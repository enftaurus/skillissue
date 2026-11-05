"""Phase 4 regression tests (QA audit 2026-11-05): DSA round integrity."""
import uuid

import pytest

from backend.app.coding.problems import get_problem, has_runnable_tests, pick_curated_interview_problem

BRUTE = """import sys
def main():
    d = sys.stdin.read().split()
    n = int(d[0]); a = list(map(int, d[1:1+n])); t = int(d[1+n])
    for i in range(n):
        for j in range(i+1, n):
            if a[i] + a[j] == t:
                print(i, j); return
main()
"""


async def _login(client):
    email = f"dsa_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_curated_picker_only_returns_judgeable_problems():
    for skills, diff in [(["Arrays", "Hash Tables"], "beginner"), (["Dynamic Programming"], "intermediate"),
                         (["Trees & Graphs"], "advanced"), ([], "staff"), (["Kubernetes"], "intermediate")]:
        pid = pick_curated_interview_problem(skills, diff)
        assert not pid.startswith("cf-")
        assert has_runnable_tests(get_problem(pid))


@pytest.mark.asyncio
async def test_codeforces_stub_cannot_be_passed_with_empty_code(client):
    headers = await _login(client)
    for endpoint in ("/api/v1/coding/run", "/api/v1/coding/submit"):
        r = await client.post(endpoint, headers=headers, json={"problem_id": "cf-2110-d", "language": "python", "code": "pass"})
        assert r.status_code == 422, r.text
        assert r.json()["error"]["code"] == "PROBLEM_NOT_JUDGEABLE"


@pytest.mark.asyncio
async def test_dsa_auto_pick_is_curated_and_runs_hints_do_not_consume_budget(client):
    headers = await _login(client)
    r = await client.post("/api/v1/interviews/domain", headers=headers, json={
        "category": "dsa", "domain_skills": ["Arrays", "Hash Tables"], "difficulty": "beginner"})
    assert r.status_code == 201, r.text
    iv = r.json()
    iid = iv["id"]
    assert not (iv.get("coding_problem_id") or "").startswith("cf-")
    assert "hey man" not in iv["messages"][0]["content"].lower()

    r = await client.post(f"/api/v1/interviews/{iid}/message", headers=headers,
                          json={"content": "I'm a CS student, okay at arrays, weak at graphs.", "client_turn_id": str(uuid.uuid4())})
    assert r.status_code == 200
    assert "Here is your question" in r.json()["content"]

    for _ in range(3):
        r = await client.post(f"/api/v1/interviews/{iid}/code", headers=headers,
                              json={"language": "python", "code": BRUTE, "run_mode": "run"})
        assert r.status_code == 200, r.text
    for lvl in (1, 2, 3):
        r = await client.post(f"/api/v1/interviews/{iid}/hint", headers=headers, json={"level": lvl, "current_code": BRUTE})
        assert r.status_code == 200, r.text

    state = (await client.get(f"/api/v1/interviews/{iid}/state", headers=headers)).json()
    assert state["turn_count"] == 1, state  # only the intro answer counts
    detail = (await client.get(f"/api/v1/interviews/{iid}", headers=headers)).json()
    assert detail["status"] == "in_progress"

    # The problem statement is presented exactly once, however long the session gets.
    for i in range(4):
        r = await client.post(f"/api/v1/interviews/{iid}/message", headers=headers,
                              json={"content": f"My approach {i}: use a hash map from value to index, one pass.", "client_turn_id": str(uuid.uuid4())})
        assert r.status_code == 200
    detail = (await client.get(f"/api/v1/interviews/{iid}", headers=headers)).json()
    presented = [m for m in detail["messages"] if m["role"] == "assistant" and "Here is your question" in m["content"]]
    assert len(presented) == 1

    # Grouped transcript never pairs a question with a hint marker, and pairs are chronological.
    grouped = detail["grouped_transcript"]
    assert all("[Requested Level" not in (t["candidate_answer"] or "") for t in grouped)
    assert all(not t["interviewer_question"].startswith("[Level") for t in grouped)
    assert grouped[0]["candidate_answer"].startswith("I'm a CS student")
