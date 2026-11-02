import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_enterprise_pipeline_and_candidate_exam(client: AsyncClient):
    # Register and login recruiter
    email = f"recruiter_{uuid.uuid4().hex[:8]}@acme.corp"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Assessment Pipeline
    pipeline_payload = {
        "title": "Uber SDE-1 Campus Hiring Assessment 2026",
        "target_role": "Backend Engineer",
        "job_description": "We are seeking talented SDE-1 engineers proficient in distributed systems, concurrency, and clean API design.",
        "rounds": [
            {
                "round_type": "oa_dsa",
                "name": "Round 1: Company DSA OA",
                "time_limit_minutes": 35,
                "is_enabled": True,
                "config": {"topics": ["Array", "Graph"]}
            },
            {
                "round_type": "ai_project",
                "name": "Round 2: Machine Coding Take-Home",
                "time_limit_minutes": 30,
                "is_enabled": True,
                "config": {"project_id": "distributed-rate-limiter"}
            },
            {
                "round_type": "tough_interview",
                "name": "Round 3: Anti-Sycophancy AI Interview",
                "time_limit_minutes": 20,
                "is_enabled": True,
                "config": {"questions": 4}
            }
        ]
    }
    create_res = await client.post("/api/v1/enterprise/pipelines", headers=headers, json=pipeline_payload)
    assert create_res.status_code == 201
    pipe_data = create_res.json()
    assert pipe_data["title"] == "Uber SDE-1 Campus Hiring Assessment 2026"
    assert len(pipe_data["rounds"]) == 3
    pipe_id = pipe_data["id"]
    invite_token = pipe_data["invite_token"]

    # 2. Invite Candidate
    cand_invite_res = await client.post(
        f"/api/v1/enterprise/pipelines/{pipe_id}/invite",
        headers=headers,
        json={"candidate_name": "Alice Candidate", "candidate_email": "alice@university.edu"}
    )
    assert cand_invite_res.status_code == 201
    cand_data = cand_invite_res.json()
    access_token = cand_data["access_token"]
    assert cand_data["status"] == "invited"

    # 3. Candidate enters exam room via token
    exam_res = await client.get(f"/api/v1/enterprise/assessments/{access_token}")
    assert exam_res.status_code == 200
    exam_data = exam_res.json()
    assert exam_data["candidate_name"] == "Alice Candidate"
    assert exam_data["current_round_index"] == 0
    assert len(exam_data["rounds"]) == 3

    # 4. Candidate completes Round 0 (DSA OA)
    sub1_res = await client.post(
        f"/api/v1/enterprise/assessments/{access_token}/submit-round",
        json={
            "round_index": 0,
            "round_type": "oa_dsa",
            "submission_data": {"score": 90.0, "tests_passed": 2, "tests_total": 2},
            "integrity_events": {"window_blurs": 1, "copy_paste_count": 2}
        }
    )
    assert sub1_res.status_code == 200
    sub1_data = sub1_res.json()
    assert sub1_data["current_round_index"] == 1
    assert sub1_data["status"] == "in_progress"

    # 5. Candidate completes Round 1 (AI Project)
    sub2_res = await client.post(
        f"/api/v1/enterprise/assessments/{access_token}/submit-round",
        json={
            "round_index": 1,
            "round_type": "ai_project",
            "submission_data": {"score": 85.0, "prompt_quality_score": 88.0},
            "integrity_events": {"window_blurs": 0, "copy_paste_count": 0}
        }
    )
    assert sub2_res.status_code == 200
    sub2_data = sub2_res.json()
    assert sub2_data["current_round_index"] == 2

    # 6. Candidate completes Round 2 (Tough Interview) -> Finished!
    sub3_res = await client.post(
        f"/api/v1/enterprise/assessments/{access_token}/submit-round",
        json={
            "round_index": 2,
            "round_type": "tough_interview",
            "submission_data": {"score": 80.0, "anti_sycophancy_grade": 82.0},
            "integrity_events": {"window_blurs": 0, "copy_paste_count": 0}
        }
    )
    assert sub3_res.status_code == 200
    sub3_data = sub3_res.json()
    assert sub3_data["status"] == "completed"
    assert sub3_data["composite_score"] == 85.0
    assert sub3_data["completed_at"] is not None

    # 7. Recruiter views leaderboard
    lb_res = await client.get(f"/api/v1/enterprise/pipelines/{pipe_id}/leaderboard", headers=headers)
    assert lb_res.status_code == 200
    lb_data = lb_res.json()
    assert lb_data["total_candidates"] == 1
    assert lb_data["completed_candidates"] == 1
    assert lb_data["average_score"] == 85.0
    assert lb_data["candidates"][0]["candidate_name"] == "Alice Candidate"
