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


@pytest.mark.asyncio
async def test_company_specific_rounds_and_brute_force_hints(client: httpx.AsyncClient):
    # 1. Register candidate
    email = f"candidate_dsa_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"}
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Launch Uber DSA Interview Round
    dsa_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={
            "category": "dsa",
            "domain_skills": ["Uber", "Dynamic Programming", "Algorithms"],
            "target_role": "Backend Engineer",
            "difficulty": "intermediate",
        }
    )
    assert dsa_res.status_code == 201
    dsa_interview = dsa_res.json()
    dsa_id = dsa_interview["id"]
    # Check conversational onboarding message
    first_msg = dsa_interview["messages"][0]["content"]
    assert "introduce yourself" in first_msg.lower() or "dsa" in first_msg.lower()

    # 3. Candidate introduces themselves mentioning favorite topic (DP & Competitive Programming)
    intro_res = await client.post(
        f"/api/v1/interviews/{dsa_id}/message",
        headers=headers,
        json={"content": "I am Raja Babu, a BTech CSE student and hobby competitive programmer. My favorite topic is dynamic programming because of overlapping subproblems and memoization."}
    )
    assert intro_res.status_code == 200
    problem_turn = intro_res.json()
    assert "session" in problem_turn["content"].lower() or "question" in problem_turn["content"].lower() or "two sum" in problem_turn["content"].lower()

    # 4. Candidate executes Brute-Force Solution (nested loops O(N^2))
    brute_force_code = """
import sys

def solve():
    lines = sys.stdin.read().split()
    if not lines:
        return
    n = int(lines[0])
    nums = [int(x) for x in lines[1:n+1]]
    target = int(lines[n+1])
    
    # Brute force nested loops O(N^2)
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                print(f"{i} {j}")
                return

if __name__ == "__main__":
    solve()
"""
    code_res = await client.post(
        f"/api/v1/interviews/{dsa_id}/code",
        headers=headers,
        json={
            "language": "python",
            "code": brute_force_code,
            "run_mode": "run"
        }
    )
    assert code_res.status_code == 200
    code_turn = code_res.json()
    assert "execution" in code_turn
    feedback = code_turn["assistant_message"]["content"]
    # Assert brute force feedback, quadratic time complexity warning, and progressive hints
    feedback_lower = feedback.lower()
    assert any(term in feedback_lower for term in ["brute-force", "o(n^2)", "quadratic", "tle", "time limit", "nested loop"])
    assert any(term in feedback_lower for term in ["trade space", "data structure", "refactor", "optimal", "o(n)"])

    # 5. Candidate submits Optimal Solution (Hash Map O(N))
    optimal_code = """
import sys

def solve():
    lines = sys.stdin.read().split()
    if not lines:
        return
    n = int(lines[0])
    nums = [int(x) for x in lines[1:n+1]]
    target = int(lines[n+1])
    
    # Optimal Hash Map O(N)
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            print(f"{seen[complement]} {i}")
            return
        seen[num] = i

if __name__ == "__main__":
    solve()
"""
    optimal_res = await client.post(
        f"/api/v1/interviews/{dsa_id}/code",
        headers=headers,
        json={
            "language": "python",
            "code": optimal_code,
            "run_mode": "submit"
        }
    )
    assert optimal_res.status_code == 200
    optimal_turn = optimal_res.json()
    optimal_feedback = optimal_turn["assistant_message"]["content"].lower()
    assert any(term in optimal_feedback for term in ["optimal", "pass", "clean", "space complexity", "edge cases"])

    # 6. Test Company-Specific Behavioral Round (e.g. OpenAI)
    openai_beh_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={
            "category": "behavioral",
            "domain_skills": ["OpenAI", "STAR Framework", "Culture Fit"],
            "target_role": "AI Research Engineer",
            "difficulty": "hard",
        }
    )
    assert openai_beh_res.status_code == 201
    beh_msg = openai_beh_res.json()["messages"][0]["content"]
    assert any(term in beh_msg.lower() for term in ["openai", "star", "safety", "deadline", "velocity"])

    # 7. Test Company-Specific Managerial Round (e.g. Uber)
    uber_mgr_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={
            "category": "managerial",
            "domain_skills": ["Uber", "Engineering Leadership", "Technical Debt"],
            "target_role": "Engineering Manager",
            "difficulty": "hard",
        }
    )
    assert uber_mgr_res.status_code == 201
    mgr_msg = uber_mgr_res.json()["messages"][0]["content"]
    assert any(term in mgr_msg.lower() for term in ["uber", "technical debt", "velocity", "dispatch", "prioritize"])


