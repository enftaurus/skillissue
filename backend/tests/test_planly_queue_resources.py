"""Planly: user-chosen days/minutes, verified resources only, and a real learning queue."""
import uuid
from unittest.mock import patch

import pytest

from backend.app.plans.resources import allowed, curated_for, resolve_for_tasks
from backend.app.plans.service import fit_tasks
from backend.app.providers.base import ProviderResponse


async def _login(client):
    email = f"planly_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_fit_tasks_exact_days_and_minutes():
    t = fit_tasks([{"title": "A", "estimated_minutes": 300}, {"title": "B"}], 5, 30, "DBMS")
    assert [x["day_number"] for x in t] == [1, 2, 3, 4, 5]
    assert all(x["estimated_minutes"] <= 30 for x in t)
    assert t[-1]["task_type"] == "reassessment"
    assert len(fit_tasks([{"title": str(i)} for i in range(20)], 4, 45, "x")) == 4


def test_allowlist_blocks_unknown_and_internal_hosts():
    assert allowed("https://docs.python.org/3/tutorial/")
    for bad in ("http://docs.python.org/3/", "https://evil.example.com/x", "https://169.254.169.254/latest",
                "https://localhost/admin", "https://user@docs.python.org/", "javascript:alert(1)"):
        assert not allowed(bad), bad
    assert curated_for("Graph BFS traversal")[0]["url"].startswith("https://cp-algorithms.com/graph/")


@pytest.mark.asyncio
async def test_invented_links_are_replaced_with_curated_ones():
    tasks = [{"title": "Postgres indexing", "external_resources": [
        {"title": "Made up", "url": "https://www.postgresql.org/docs/current/indexes-btree-magic.html"},
        {"title": "Random blog", "url": "https://some-random-blog.dev/postgres"}]}]
    out = await resolve_for_tasks(tasks, "DBMS")
    urls = [r["url"] for r in out[0]]
    assert urls and all("magic" not in u and "random-blog" not in u for u in urls)
    assert any("postgresql.org/docs" in u for u in urls)


@pytest.mark.asyncio
async def test_custom_plan_uses_requested_days_minutes_and_verified_links(client):
    h = await _login(client)
    fake = ProviderResponse(text="", parsed_json={"title": "OS plan", "tasks": [
        {"title": "Processes and threads", "estimated_minutes": 999,
         "external_resources": [{"title": "Fake", "url": "https://docs.python.org/3/library/not-a-real-page-123.html"}]}]})
    with patch("backend.app.providers.mock_provider.MockProvider.generate_json", return_value=fake):
        r = await client.post("/api/v1/plans/custom", headers=h, json={
            "topic": "Operating Systems", "daily_study_minutes": 30, "total_days": 6,
            "schedule_days": ["monday", "wednesday", "friday"]})
    assert r.status_code == 201, r.text
    plan = r.json()
    assert len(plan["tasks"]) == 6 and plan["total_days"] == 6
    assert all(t["estimated_minutes"] <= 30 for t in plan["tasks"])
    links = [res["url"] for t in plan["tasks"] for res in t["external_resources"]]
    assert links and all("not-a-real-page" not in u for u in links)
    assert {d for d in (t["scheduled_date"][:10] for t in plan["tasks"])}  # scheduled on chosen weekdays


@pytest.mark.asyncio
async def test_queue_is_priority_then_fifo_and_refills(client):
    h = await _login(client)
    for topic, pr in (("Tries", "low"), ("Dynamic Programming", "medium"), ("Graphs", "high"), ("Heaps", "medium")):
        await client.post("/api/v1/learning-backlog", headers=h, json={"topic": topic, "priority": pr, "reason": "practice"})
    q = (await client.get("/api/v1/learning-backlog?status=queued", headers=h)).json()
    assert [i["topic"] for i in q] == ["Graphs", "Dynamic Programming", "Heaps", "Tries"]

    plan = (await client.post("/api/v1/plans/custom", headers=h, json={"topic": "DSA", "daily_study_minutes": 30, "total_days": 3})).json()
    plan = (await client.post(f"/api/v1/plans/{plan['id']}/queue/next", headers=h)).json()
    assert plan["tasks"][-1]["title"].startswith("Deep Dive: Graphs") and plan["tasks"][-1]["external_resources"]
    q = [i["topic"] for i in (await client.get("/api/v1/learning-backlog?status=queued", headers=h)).json()]
    assert q == ["Dynamic Programming", "Heaps", "Tries"]

    # Skipping a queue task puts the topic back in the queue.
    graphs_task = plan["tasks"][-1]
    await client.put(f"/api/v1/plans/tasks/{graphs_task['id']}/status", headers=h, json={"status": "skipped"})
    assert "Graphs" in [i["topic"] for i in (await client.get("/api/v1/learning-backlog?status=queued", headers=h)).json()]

    # Finishing everything pulls the next topic in automatically.
    for t in plan["tasks"][:-1]:
        await client.put(f"/api/v1/plans/tasks/{t['id']}/status", headers=h, json={"status": "completed"})
    plan = (await client.get(f"/api/v1/plans/{plan['id']}", headers=h)).json()
    assert plan["tasks"][-1]["title"].startswith("Deep Dive: Graphs")  # re-queued high priority comes first again


@pytest.mark.asyncio
async def test_empty_queue_is_a_clear_error(client):
    h = await _login(client)
    plan = (await client.post("/api/v1/plans/custom", headers=h, json={"topic": "DSA", "daily_study_minutes": 30, "total_days": 3})).json()
    r = await client.post(f"/api/v1/plans/{plan['id']}/queue/next", headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "QUEUE_EMPTY"
