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


@pytest.mark.asyncio
async def test_numeric_answers_do_not_match_inside_other_numbers():
    item = ITEMS_BY_ID["async-fanout"]
    q = next(x for x in item.questions if x.type == "numeric")
    assert (await grade_answer(item, q, "0.2 seconds")).verdict == "incorrect"  # found by the calibration eval
    assert (await grade_answer(item, q, "12 seconds")).verdict == "incorrect"
    assert (await grade_answer(item, q, "about 2 seconds")).verdict == "correct"
    assert (await grade_answer(item, q, "2.0s total")).verdict == "correct"
    r = ITEMS_BY_ID["retry-helper"]
    rq = next(x for x in r.questions if x.type == "numeric")
    assert (await grade_answer(r, rq, "11.5 seconds")).verdict == "incorrect"
    assert (await grade_answer(r, rq, "1.5 seconds")).verdict == "correct"


# --- Round 3f regressions (E25-E28) ---------------------------------------------------------

@pytest.mark.asyncio
async def test_trace_accepts_inline_outputs_and_matches_whole_tokens():
    build = ITEMS_BY_ID["build-order"]
    q = next(x for x in build.questions if x.type == "trace")  # "[]\n['c']"
    assert (await grade_answer(build, q, "It prints [] and then ['c']")).verdict == "correct"
    assert (await grade_answer(build, q, "['c'] then []")).verdict != "correct"  # order still matters
    retry = ITEMS_BY_ID["retry-helper"]
    rq = next(x for x in retry.questions if x.type == "trace")  # "None 3 3"
    assert (await grade_answer(retry, rq, "NoneType 3 3")).verdict == "incorrect"
    assert (await grade_answer(retry, rq, "None 3 33")).verdict == "incorrect"


class _Judge:
    def __init__(self, text):
        self.text = text

    async def generate_text(self, **kw):
        class R:
            pass
        r = R()
        r.text = self.text
        return r


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [
    '[1, 2]', '{"covered": 3, "score": 0.5}', '{"covered": [0], "score": "high"}',
    '{"covered": [0], "score": null, "follow_up": {"q": 1}}', '{"covered": [true, "0", 9, -1], "score": NaN}',
    '{"covered": [0], "score": 0.4, "feedback": 12, "follow_up": 7}', 'no json at all',
])
async def test_malformed_judge_output_never_500s(raw):
    item = ITEMS_BY_ID["ttl-lru-cache"]
    q = next(x for x in item.questions if x.type == "explain")
    g = await grade_answer(item, q, "It is an LRU cache with a TTL per key; get moves keys to the end.", _Judge(raw))
    assert 0.0 <= g.score <= 1.0 and isinstance(g.feedback, str)
    assert g.follow_up is None or isinstance(g.follow_up, str)


@pytest.mark.asyncio
async def test_nan_judge_score_is_not_full_marks():
    item = ITEMS_BY_ID["ttl-lru-cache"]
    q = next(x for x in item.questions if x.type == "explain")
    g = await grade_answer(item, q, "it caches stuff", _Judge('{"covered": [], "score": NaN}'))
    assert g.score == 0.0


@pytest.mark.asyncio
async def test_offline_follow_up_does_not_leak_the_answer_key():
    for item in ITEMS:
        for q in item.questions:
            if q.type in ("trace", "numeric"):
                continue
            g = await grade_answer(item, q, "not sure, something about the code")
            assert g.follow_up, f"{item.id}/{q.id}"
            for point in q.key_points:
                assert point.split(",")[0].lower() not in g.follow_up.lower(), f"{item.id}/{q.id} leaked {point!r}"


@pytest.mark.asyncio
async def test_answer_after_concurrent_finish_is_rejected(client, monkeypatch):
    """Grading is slow; a finish landing mid-grade must not be overwritten by the stale answer."""
    from backend.app.comprehension import service as svc
    from backend.app.providers.factory import ModelFactory

    async def _no_provider(*a, **k):
        raise RuntimeError("offline")
    monkeypatch.setattr(ModelFactory, "get_for_user", _no_provider)
    h = await _login(client)
    sid = (await client.post("/api/v1/comprehension/sessions", headers=h, json={"item_id": "retry-helper"})).json()["id"]

    real_grade = svc.grade_answer

    async def slow_grade(*a, **k):
        fin = await client.post(f"/api/v1/comprehension/sessions/{sid}/finish", headers=h)
        assert fin.json()["status"] == "completed"
        return await real_grade(*a, **k)
    monkeypatch.setattr(svc, "grade_answer", slow_grade)
    r = await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h, json={"question_id": "q1", "answer": "None 3 3"})
    assert r.json()["error"]["code"] == "SESSION_FINISHED"
    monkeypatch.setattr(svc, "grade_answer", real_grade)
    s = (await client.get(f"/api/v1/comprehension/sessions/{sid}", headers=h)).json()
    assert s["answers"] == {} and s["score"] == 0.0


@pytest.mark.asyncio
async def test_retired_item_is_410_not_500(client, db_session):
    from backend.app.database.models import ComprehensionSession
    h = await _login(client)
    sid = (await client.post("/api/v1/comprehension/sessions", headers=h, json={"item_id": "retry-helper"})).json()["id"]
    row = await db_session.get(ComprehensionSession, sid)
    row.item_id = "retired-item"
    await db_session.commit()
    for r in (await client.get(f"/api/v1/comprehension/sessions/{sid}", headers=h),
              await client.post(f"/api/v1/comprehension/sessions/{sid}/finish", headers=h),
              await client.post(f"/api/v1/comprehension/sessions/{sid}/answer", headers=h, json={"question_id": "q1", "answer": "x"})):
        assert r.status_code == 410 and r.json()["error"]["code"] == "ITEM_RETIRED"
    assert (await client.get("/api/v1/comprehension/history", headers=h)).status_code == 200
