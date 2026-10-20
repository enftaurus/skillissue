import uuid
import pytest
import httpx

@pytest.mark.asyncio
async def test_langgraph_interview_agent_workflow(client: httpx.AsyncClient):
    # 1. Register user
    email = f"agent_user_{uuid.uuid4().hex[:8]}@example.com"
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

    # 2. Configure provider preferences with task-specific models
    config_res = await client.put(
        "/api/v1/providers/config",
        headers=headers,
        json={
            "provider_name": "bedrock",
            "aws_region": "us-east-1",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "preferred_model": "amazon.nova-lite-v1:0",
            "default_model": "amazon.nova-lite-v1:0",
            "interviewer_model": "amazon.nova-lite-v1:0",
            "evaluation_model": "amazon.nova-pro-v1:0",
            "coding_model": "amazon.nova-lite-v1:0",
            "temperature": 0.5,
            "max_tokens": 1024,
        }
    )
    assert config_res.status_code == 200
    cfg = config_res.json()
    assert cfg["interviewer_model"] == "amazon.nova-lite-v1:0"
    assert cfg["evaluation_model"] == "amazon.nova-pro-v1:0"
    assert cfg["coding_model"] == "amazon.nova-lite-v1:0"

    # 3. Create domain interview powered by LangGraph agent
    start_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={
            "category": "technical",
            "domain_skills": ["PostgreSQL", "Distributed Systems"],
            "target_role": "Senior Backend Engineer",
            "difficulty": "hard",
        }
    )
    assert start_res.status_code == 201
    interview = start_res.json()
    interview_id = interview["id"]
    assert len(interview["messages"]) == 1
    assert interview["messages"][0]["role"] == "assistant"
    assert len(interview["grouped_transcript"]) == 1
    assert interview["grouped_transcript"][0]["question_index"] == 1

    # 4. Candidate sends response (triggers LangGraph assess_candidate_turn_node & generate_question_node)
    msg1_res = await client.post(
        f"/api/v1/interviews/{interview_id}/message",
        headers=headers,
        json={"content": "We partitioned our PostgreSQL database using declarative range partitioning by created_at timestamp and deployed pg_partman."}
    )
    assert msg1_res.status_code == 200
    msg1 = msg1_res.json()
    assert msg1["role"] == "assistant"
    assert msg1["question_index"] == 2
    assert len(msg1["content"]) > 10

    # 5. Check grouped transcript endpoint
    transcript_res = await client.get(
        f"/api/v1/interviews/{interview_id}/transcript/grouped",
        headers=headers
    )
    assert transcript_res.status_code == 200
    turns = transcript_res.json()
    assert len(turns) >= 2
    assert turns[0]["question_index"] == 1
    assert "partitioned" in turns[0]["candidate_answer"]

    # 6. Candidate answers second question
    msg2_res = await client.post(
        f"/api/v1/interviews/{interview_id}/message",
        headers=headers,
        json={"content": "To prevent lock contention, we attached partitions during maintenance windows with SHARE UPDATE EXCLUSIVE locks."}
    )
    assert msg2_res.status_code == 200

    # 7. End interview
    end_res = await client.post(f"/api/v1/interviews/{interview_id}/end", headers=headers)
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "completed"

    # 8. Submit question-by-question self-evaluation
    self_eval_res = await client.post(
        "/api/v1/evaluations/self",
        headers=headers,
        json={
            "interview_id": interview_id,
            "dimension_scores": {
                "technical_depth": 4,
                "system_design_tradeoffs": 4,
                "communication_clarity": 5,
                "problem_solving_rigor": 4,
            },
            "reflection": "I demonstrated solid mechanical understanding of Postgres table partitioning.",
            "question_evaluations": [
                {
                    "question_index": 1,
                    "score": 4,
                    "strengths": "Mentioned range partitioning and pg_partman automation.",
                    "missed_points": "Could have discussed index inheritance caveats.",
                    "confidence": "high",
                },
                {
                    "question_index": 2,
                    "score": 4,
                    "strengths": "Addressed DDL lock mitigation strategies.",
                    "missed_points": "Did not explain query pruning performance benchmarks.",
                    "confidence": "medium",
                }
            ]
        }
    )
    assert self_eval_res.status_code == 201
    self_eval = self_eval_res.json()
    assert len(self_eval["question_evaluations"]) == 2
    assert self_eval["question_evaluations"][0]["score"] == 4

    # 9. Generate AI evaluation (resolves evaluation model and calculates scores deterministically)
    ai_eval_res = await client.post(
        f"/api/v1/evaluations/{interview_id}/generate",
        headers=headers
    )
    assert ai_eval_res.status_code == 200
    ai_eval = ai_eval_res.json()
    assert ai_eval["overall_score"] > 0
    assert "technical_depth" in ai_eval["rubric_dimension_scores"]

    # 10. Fetch self-vs-AI comparison with question comparisons
    comparison_res = await client.get(
        f"/api/v1/evaluations/{interview_id}/comparison",
        headers=headers
    )
    assert comparison_res.status_code == 200
    comp = comparison_res.json()
    assert len(comp["dimensions"]) == 4
    assert len(comp["question_comparisons"]) >= 2
    assert comp["question_comparisons"][0]["self_score"] == 4
    assert comp["question_comparisons"][0]["self_strengths"] == "Mentioned range partitioning and pg_partman automation."
