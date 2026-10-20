import uuid
import pytest
import httpx

@pytest.mark.asyncio
async def test_domain_and_jd_interview_workflows(client: httpx.AsyncClient):
    # 1. Register candidate
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"}
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload text resume
    resume_content = b"""
    John Doe - Backend Software Engineer
    Skills: Python, FastAPI, PostgreSQL, Redis, Docker, Distributed Systems
    Experience: Built high-throughput payment webhook service handling 5,000 req/sec.
    """
    upload_res = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.txt", resume_content, "text/plain")}
    )
    assert upload_res.status_code == 201
    resume_data = upload_res.json()
    assert "Python" in resume_data["extracted_skills"]
    resume_id = resume_data["id"]

    # 3. Create Domain-based Interview
    domain_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={
            "category": "technical",
            "domain_skills": ["Python", "FastAPI", "Redis", "PostgreSQL"],
            "target_role": "Backend Engineer",
            "difficulty": "intermediate",
            "resume_id": resume_id
        }
    )
    assert domain_res.status_code == 201
    domain_interview = domain_res.json()
    assert domain_interview["mode"] == "domain"
    assert len(domain_interview["messages"]) == 1
    assert domain_interview["messages"][0]["role"] == "assistant"
    assert len(domain_interview["messages"][0]["content"]) > 10
    interview_id = domain_interview["id"]

    # 4. Candidate sends answer making a bold performance claim
    msg_res = await client.post(
        f"/api/v1/interviews/{interview_id}/message",
        headers=headers,
        json={"content": "In our payment service, we added Redis caching for idempotent keys, which made lookups 10x faster."}
    )
    assert msg_res.status_code == 200
    follow_up = msg_res.json()
    assert follow_up["role"] == "assistant"
    # Verify adaptive questioning / skepticism
    assert len(follow_up["content"]) > 10

    # 5. End interview session
    end_res = await client.post(
        f"/api/v1/interviews/{interview_id}/end",
        headers=headers
    )
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "completed"

    # 6. Create Job Description
    jd_res = await client.post(
        "/api/v1/job-descriptions",
        headers=headers,
        json={
            "title": "Senior Distributed Systems Engineer",
            "company": "Pied Piper",
            "raw_text": "We are seeking a Senior Distributed Systems Engineer with deep expertise in Python, async I/O, Kafka, and PostgreSQL query optimization."
        }
    )
    assert jd_res.status_code == 201
    jd_data = jd_res.json()
    assert len(jd_data["extracted_skills"]) > 0
    jd_id = jd_data["id"]

    # 7. Update/Correct JD requirements
    update_jd = await client.put(
        f"/api/v1/job-descriptions/{jd_id}",
        headers=headers,
        json={"company": "Pied Piper Cloud"}
    )
    assert update_jd.status_code == 200
    assert update_jd.json()["company"] == "Pied Piper Cloud"

    # 8. Create JD-based Interview (does NOT require reselecting skills manually)
    jd_interview_res = await client.post(
        "/api/v1/interviews/jd",
        headers=headers,
        json={
            "category": "technical",
            "jd_id": jd_id,
            "difficulty": "advanced"
        }
    )
    assert jd_interview_res.status_code == 201
    jd_interview = jd_interview_res.json()
    assert jd_interview["mode"] == "jd"
    assert jd_interview["jd_id"] == jd_id
    assert len(jd_interview["messages"]) == 1

    # 9. Request Socratic hints (tiers 1 and 2)
    hint_res1 = await client.post(
        f"/api/v1/interviews/{jd_interview['id']}/hint",
        headers=headers,
        json={"level": 1, "problem_id": "two-sum", "current_code": "def twoSum(nums, target): pass"}
    )
    assert hint_res1.status_code == 200
    hint1 = hint_res1.json()
    assert hint1["level"] == 1
    assert hint1["penalty_pct"] == 5
    assert hint1["total_hint_level_used"] == 1
    assert len(hint1["hint"]) > 10

    hint_res2 = await client.post(
        f"/api/v1/interviews/{jd_interview['id']}/hint",
        headers=headers,
        json={"level": 2, "problem_id": "two-sum"}
    )
    assert hint_res2.status_code == 200
    hint2 = hint_res2.json()
    assert hint2["level"] == 2
    assert hint2["penalty_pct"] == 15
    assert hint2["total_hint_level_used"] == 2

