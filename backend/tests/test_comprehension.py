"""Code comprehension round: answer keys are verified by execution; grading and API flow."""
import subprocess
import sys
import uuid
from datetime import timedelta

import pytest

from backend.app.comprehension.bank import ITEMS, ITEMS_BY_ID
from backend.app.comprehension.grading import grade_answer, location_correct, referenced_lines


@pytest.mark.parametrize("item", ITEMS, ids=[i.id for i in ITEMS])
def test_answer_keys_are_true(item):
    """Every trace expectation must be what the served code actually prints."""
    main = list(item.clean_files().values())[0]
    for q in item.questions:
        if q.type == "trace":
            out = subprocess.run([sys.executable, "-I", "-c", main + "\n" + q.harness], capture_output=True, text=True, timeout=15)
            assert out.stdout.strip() == q.expected_output, f"{item.id}/{q.id}: {out.stdout!r} {out.stderr[-300:]}"
        if q.type == "bug":
            assert item.bug_lines(), f"{item.id} has a bug question but no # @bug marker"
    assert all("@bug" not in src for src in item.clean_files().values())


def test_location_parsing():
    item = ITEMS_BY_ID["ttl-lru-cache"]  # bug at cache.py:16
    assert location_correct("The bug is on L16, move_to_end runs before the expiry check", item)
    assert location_correct("line 17: the expiry check comes too late", item)
    assert location_correct("This line: self._data.move_to_end(key) inside get", item)
    assert not location_correct("Somewhere in put, line 25", item)
    assert 16 in referenced_lines("L16 and line 9", item)


@pytest.mark.asyncio
async def test_grading_paths_without_llm():
    item = ITEMS_BY_ID["retry-helper"]
    trace = next(q for q in item.questions if q.type == "trace")
    g = await grade_answer(item, trace, "It prints:\nNone 3 3")
    assert g.verdict == "correct"
    g = await grade_answer(item, trace, "ValueError is raised")
    assert g.verdict == "incorrect" and g.follow_up

    numeric = next(q for q in item.questions if q.type == "numeric")
    assert (await grade_answer(item, numeric, "0.1+0.2+0.4+0.8 = 1.5 seconds")).verdict == "correct"
    assert (await grade_answer(item, numeric, "3.1s")).verdict == "incorrect"

    bug = next(q for q in item.questions if q.type == "bug")
    g = await grade_answer(item, bug, "attempt == attempts is never true since range stops at attempts - 1, so it returns None")
    assert g.location_correct is False and g.follow_up and g.score < 0.8
    g = await grade_answer(item, bug, "L11: attempt == attempts is never true because range stops at attempts - 1; "
                                      "after the last failure the function returns None instead of raising")
    assert g.location_correct is True and g.score >= 0.6


async def _login(client):
    email = f"comp_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.mark.asyncio
async def test_session_flow_follow_up_reveal_and_isolation(client, monkeypatch):
    from backend.app.providers.factory import ModelFactory

    async def _no_provider(*a, **k):
        raise RuntimeError("offline")
    monkeypatch.setattr(ModelFactory, "get_for_user", _no_provider)

    h = await _login(client)
    items = (await client.get("/api/v1/comprehension/items", headers=h)).json()
    assert len(items) >= 8 and "files" not in items[0]

    s = (await client.post("/api/v1/comprehension/sessions", headers=h, json={"item_id": "keyset-pagination"})).json()
    sid = s["id"]
    assert "reveal" not in s and "expected_output" not in str(s) and "@bug" not in str(s)

    r = (await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h,
                           json={"question_id": "q1", "answer": "[0, 1, 4]"})).json()
    assert r["verdict"] == "correct" and r["done"]
    again = await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h, json={"question_id": "q1", "answer": "x"})
    assert again.status_code == 400 and again.json()["error"]["code"] == "ALREADY_ANSWERED"

    r = (await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h,
                           json={"question_id": "q2", "answer": "rows with the same created_at get skipped"})).json()
    assert r["follow_up"] and not r["done"]
    r2 = (await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h,
                            json={"question_id": "q2", "answer": "L5, the filter uses > cursor on a non-unique created_at"})).json()
    assert r2["done"] and r2["score"] >= r["score"] and r2["location_correct"]

    other = await _login(client)
    assert (await client.get(f"/api/v1/comprehension/sessions/{sid}", headers=other)).status_code == 404

    fin = (await client.post(f"/api/v1/comprehension/sessions/{sid}/finish", headers=h)).json()
    assert fin["status"] == "completed" and 0 < fin["score"] <= 100
    assert fin["reveal"]["bug_lines"] == [{"file": "paging.py", "line": 5}]
    late = await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h, json={"question_id": "q3", "answer": "x"})
    assert late.json()["error"]["code"] == "SESSION_FINISHED"


@pytest.mark.asyncio
async def test_expired_session_rejects_answers(client, db_session):
    from backend.app.database.models import ComprehensionSession
    h = await _login(client)
    s = (await client.post("/api/v1/comprehension/sessions", headers=h, json={"item_id": "retry-helper"})).json()
    row = await db_session.get(ComprehensionSession, s["id"])
    row.started_at = row.started_at - timedelta(hours=1)
    await db_session.commit()
    r = await client.post(f"/api/v1/comprehension/sessions/{s['id']}/answer", headers=h, json={"question_id": "q1", "answer": "None 3 3"})
    assert r.json()["error"]["code"] == "SESSION_EXPIRED"
