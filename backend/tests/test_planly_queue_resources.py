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


# --- E18-E20 (5a, round 3d) ---------------------------------------------------------------------------------

def test_fit_tasks_and_plan_meta_survive_junk_model_output():
    from backend.app.plans.service import clean_plan_meta
    junk = [{"title": "T" * 900, "subtopic": "S" * 400, "description": {"x": 1}, "task_type": "revision" * 10},
            {"title": 42, "subtopic": ["a"], "task_type": None}, {"title": {"nested": True}}, {"title": "  "},
            {"title": "ok\x00nul"}]
    t = fit_tasks(junk, 4, 30, "DBMS")
    assert len(t) == 4
    assert len(t[0]["title"]) == 255 and len(t[0]["subtopic"]) == 150 and t[0]["task_type"] == "practice"
    assert isinstance(t[0]["description"], str) and t[0]["description"]
    assert t[1]["title"] == "42" and t[1]["subtopic"] is None
    assert t[2]["title"] == "oknul"
    title, skills = clean_plan_meta({"bad": 1}, "not a list", "DBMS Study Roadmap", "DBMS")
    assert title == "DBMS Study Roadmap" and skills == ["DBMS"]
    title, skills = clean_plan_meta("x" * 1000, [{"a": 1}, "SQL", 7, "y" * 500], "f", "f")
    assert len(title) == 255 and skills == ["SQL", "7", "y" * 150]


@pytest.mark.asyncio
async def test_schedule_days_validated(client):
    h = await _login(client)
    for bad in (["funday"], ["monday"] * 50, ["x" * 10000]):
        r = await client.post("/api/v1/plans/custom", headers=h, json={"topic": "DSA", "total_days": 3, "schedule_days": bad})
        assert r.status_code == 422, bad
    r = await client.post("/api/v1/plans/custom", headers=h, json={"topic": "DSA", "total_days": 3,
                                                                  "schedule_days": [" Monday", "monday", "FRIDAY"]})
    assert r.status_code in (200, 201) and r.json()["schedule_days"] == ["monday", "friday"]


@pytest.mark.asyncio
async def test_long_queue_topic_and_double_start_dont_break_the_plan(db_session):
    import asyncio
    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from backend.app.core.config import settings
    from backend.app.database.session import get_db
    from backend.app.main import create_application

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _own_session():  # one session per request, like production
        async with maker() as s:
            yield s
            await s.commit()

    app = create_application()
    app.dependency_overrides[get_db] = _own_session
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            h = await _login(client)
            r = await client.post("/api/v1/learning-backlog", headers=h, json={"topic": "T" * 150, "subtopic": "S" * 150,
                                                                               "priority": "high", "reason": "practice"})
            assert r.status_code in (200, 201), r.text
            item_id = r.json()["id"]
            plan = (await client.post("/api/v1/plans/custom", headers=h,
                                      json={"topic": "DSA", "daily_study_minutes": 30, "total_days": 3})).json()
            base = len(plan["tasks"])

            # Title "Deep Dive: {topic} ({subtopic})" is 316 chars against a 255 column: used to be a 500.
            rs = await asyncio.gather(*[client.post(f"/api/v1/plans/{plan['id']}/queue/next", headers=h) for _ in range(3)])
            assert all(x.status_code in (200, 409) for x in rs), [x.text for x in rs]
            plan = (await client.get(f"/api/v1/plans/{plan['id']}", headers=h)).json()
            assert len(plan["tasks"]) == base + 1  # three concurrent "Start next topic" clicks schedule it once
            assert len(plan["tasks"][-1]["title"]) <= 255

            # Re-attaching an item that's already in this plan doesn't duplicate it either.
            r = await client.post(f"/api/v1/plans/{plan['id']}/backlog-items", headers=h, json={"backlog_item_ids": [item_id]})
            assert r.status_code == 200 and len(r.json()["tasks"]) == base + 1
    finally:
        await engine.dispose()
