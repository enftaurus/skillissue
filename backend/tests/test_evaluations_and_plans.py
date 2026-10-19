import uuid
import pytest
import httpx

@pytest.mark.asyncio
async def test_evaluation_and_planly_lifecycle(client: httpx.AsyncClient):
    # 1. Register candidate
    email = f"eval_learner_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "daily_study_minutes": 45}
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Interview
    interview_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={
            "category": "technical",
            "domain_skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            "target_role": "Backend Engineer",
            "difficulty": "intermediate"
        }
    )
    assert interview_res.status_code == 201
    interview_id = interview_res.json()["id"]

    # 3. Simulate candidate response
    await client.post(
        f"/api/v1/interviews/{interview_id}/message",
        headers=headers,
        json={"content": "We implemented Redis for caching user session lookups to reduce PostgreSQL load."}
    )

    # 4. End interview
    await client.post(f"/api/v1/interviews/{interview_id}/end", headers=headers)

    # 5. Submit candidate Self-Evaluation (MUST occur before AI evaluation)
    self_eval_res = await client.post(
        "/api/v1/evaluations/self",
        headers=headers,
        json={
            "interview_id": interview_id,
            "dimension_scores": {
                "technical_depth": 3,
                "system_design_tradeoffs": 2,
                "communication_clarity": 4,
                "problem_solving_rigor": 3
            },
            "reflection": "I gave a solid explanation of Redis caching but forgot to talk about eviction policies."
        }
    )
    assert self_eval_res.status_code == 201
    assert self_eval_res.json()["dimension_scores"]["technical_depth"] == 3

    # 6. Generate AI Evaluation
    ai_eval_res = await client.post(
        f"/api/v1/evaluations/{interview_id}/generate",
        headers=headers
    )
    assert ai_eval_res.status_code == 200
    eval_data = ai_eval_res.json()
    assert eval_data["overall_score"] > 0
    assert len(eval_data["rubric_dimension_scores"]) > 0
    assert len(eval_data["strengths"]) > 0
    assert len(eval_data["weaknesses"]) > 0
    eval_id = eval_data["id"]

    # 7. Get Self vs AI Comparison
    comp_res = await client.get(
        f"/api/v1/evaluations/{interview_id}/comparison",
        headers=headers
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert len(comp_data["dimensions"]) > 0
    # Technical depth comparison
    tech_dim = next(d for d in comp_data["dimensions"] if d["dimension_id"] == "technical_depth")
    assert tech_dim["self_score"] == 3
    assert tech_dim["ai_score"] is not None
    assert tech_dim["delta"] is not None

    # 8. Generate Planly Improvement Plan
    plan_res = await client.post(
        f"/api/v1/plans/generate/{eval_id}",
        headers=headers
    )
    assert plan_res.status_code == 201
    plan = plan_res.json()
    assert plan["total_days"] >= 5
    assert len(plan["tasks"]) >= 5
    plan_id = plan["id"]
    first_task_id = plan["tasks"][0]["id"]

    # 9. Toggle task completion
    toggle_res = await client.post(
        f"/api/v1/plans/tasks/{first_task_id}/toggle",
        headers=headers,
        json={"is_completed": True}
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_completed"] is True

    # 10. Adapt Plan (student missed 2 days)
    adapt_res = await client.post(
        f"/api/v1/plans/{plan_id}/adapt",
        headers=headers,
        json={"days_behind": 2}
    )
    assert adapt_res.status_code == 200
    adapted_plan = adapt_res.json()
    assert adapted_plan["total_days"] >= plan["total_days"]

    # 11. Verify Analytics Dashboard
    dash_res = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total_interviews"] >= 1
    assert dash["completed_interviews"] >= 1
    assert dash["plan_tasks_completed"] >= 1
    assert len(dash["score_history"]) >= 1
    assert len(dash["dimension_trends"]) > 0

@pytest.mark.asyncio
async def test_evaluation_parsing_failure_rejects_fabricated_score(client: httpx.AsyncClient):
    """Verify that when the LLM outputs malformed JSON or empty dimensions, no fabricated 70.0 score is saved."""
    from unittest.mock import patch
    from backend.app.providers.base import ProviderResponse
    from backend.app.core.errors import ProviderError

    # 1. Register candidate and start interview
    email = f"eval_fail_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    int_res = await client.post(
        "/api/v1/interviews/domain",
        headers=headers,
        json={"category": "technical", "domain_skills": ["Python"]}
    )
    interview_id = int_res.json()["id"]

    # Send an answer so interview has at least 2 messages
    await client.post(
        f"/api/v1/interviews/{interview_id}/message",
        headers=headers,
        json={"content": "I designed asynchronous workers using Celery and Redis."}
    )

    # Mock provider returning malformed JSON
    mock_bad_resp = ProviderResponse(
        text="I cannot evaluate this transcript.",
        input_tokens=10,
        output_tokens=10,
        estimated_cost_usd=0.0,
        model_id="mock-qwen3-32b",
        parsed_json={"error": "JSON_PARSE_FAILURE"}
    )

    with patch("backend.app.providers.mock_provider.MockProvider.generate_json", return_value=mock_bad_resp):
        eval_call = await client.post(f"/api/v1/evaluations/{interview_id}/generate", headers=headers)
        # Must fail with an error (502 Bad Gateway from provider parsing error), NOT return 200 with 70.0 fabricated score
        assert eval_call.status_code == 502
        assert "EVALUATION_PARSING_FAILED" in eval_call.text or "failed" in eval_call.text.lower()

    # Verify no bogus evaluation was recorded in database
    get_eval = await client.get(f"/api/v1/evaluations/{interview_id}", headers=headers)
    assert get_eval.status_code == 404

