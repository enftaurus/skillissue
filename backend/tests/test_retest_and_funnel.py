import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_retest_and_funnel_telemetry(client: AsyncClient):
    # Register and login user
    email = f"retest_user_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create an interview, answer a question, and end it
    int_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={"category": "technical", "domain_skills": ["Concurrency", "Distributed Systems"], "target_role": "Backend Engineer"}
    )
    assert int_res.status_code == 201
    interview_id = int_res.json()["id"]

    await client.post(
        f"/api/v1/interviews/{interview_id}/message",
        headers=headers,
        json={"content": "We used Redis for distributed locking with TTL to avoid deadlocks."}
    )
    await client.post(f"/api/v1/interviews/{interview_id}/end", headers=headers)

    # Generate evaluation
    eval_res = await client.post(f"/api/v1/evaluations/{interview_id}/generate", headers=headers)
    assert eval_res.status_code == 200
    evaluation_id = eval_res.json()["id"]
    baseline_score = eval_res.json()["overall_score"]

    # 2. Initiate Retest on identified weakness
    retest_res = await client.post(
        f"/api/v1/evaluations/{evaluation_id}/retest",
        headers=headers,
        json={"weakness_topic": "Concurrency & Mutex Locks", "baseline_score": baseline_score}
    )
    assert retest_res.status_code == 201
    retest_data = retest_res.json()
    assert retest_data["weakness_topic"] == "Concurrency & Mutex Locks"
    assert retest_data["status"] == "in_progress"
    retest_session_id = retest_data["id"]
    retest_interview_id = retest_data["retest_interview_id"]
    assert retest_interview_id is not None

    # List retests for evaluation
    list_retest_res = await client.get(f"/api/v1/evaluations/{evaluation_id}/retests", headers=headers)
    assert list_retest_res.status_code == 200
    assert len(list_retest_res.json()) >= 1

    # 3. Candidate answers retest interview and completes it
    await client.post(
        f"/api/v1/interviews/{retest_interview_id}/message",
        headers=headers,
        json={"content": "To prevent deadlocks and race conditions, we implement optimistic locking using version numbers on database rows."}
    )
    await client.post(f"/api/v1/interviews/{retest_interview_id}/end", headers=headers)
    await client.post(f"/api/v1/evaluations/{retest_interview_id}/generate", headers=headers)

    delta_res = await client.post(f"/api/v1/evaluations/retests/{retest_session_id}/complete", headers=headers)
    assert delta_res.status_code == 200
    delta_data = delta_res.json()
    assert delta_data["status"] == "completed"
    assert "delta_score" in delta_data
    assert len(delta_data["verified_improvements"]) >= 1

    # Answer replay diff: original answer vs retest answer on the same weakness
    diff = await client.get(f"/api/v1/evaluations/retests/{retest_session_id}/diff", headers=headers)
    assert diff.status_code == 200, diff.text
    d = diff.json()
    assert d["weakness_topic"] == "Concurrency & Mutex Locks"
    assert d["after"] and d["after"]["answer"]
    assert "verdict" in d["summary"]
    other = await client.post("/api/v1/auth/register", json={"email": f"o_{uuid.uuid4().hex[:6]}@example.com", "password": "Password123!"})
    otok = (await client.post("/api/v1/auth/login", json={"email": other.json()["email"], "password": "Password123!"})).json()["access_token"]
    assert (await client.get(f"/api/v1/evaluations/retests/{retest_session_id}/diff",
                             headers={"Authorization": f"Bearer {otok}"})).status_code == 404

    # Retest opener comes from the interview engine, not a canned concurrency question
    retest_iv = (await client.get(f"/api/v1/interviews/{retest_interview_id}", headers=headers)).json()
    assert "high-throughput concurrency and prevent race conditions" not in retest_iv["messages"][0]["content"]

    # 4. Check Admin Funnel Telemetry
    funnel_res = await client.get("/api/v1/analytics/funnel", headers=headers)
    assert funnel_res.status_code == 200
    funnel_data = funnel_res.json()
    assert funnel_data["total_signups"] >= 1
    assert len(funnel_data["steps"]) == 5
    assert "provider_reliability" in funnel_data
    assert "edge_neural_tts" in funnel_data["provider_reliability"]
    assert "faster_whisper_stt" in funnel_data["provider_reliability"]
