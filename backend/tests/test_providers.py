import pytest
import httpx
from backend.app.providers.models_catalog import SUPPORTED_MODELS, calculate_token_cost
from backend.app.providers.mock_provider import MockProvider

@pytest.mark.asyncio
async def test_models_catalog_lineup(client: httpx.AsyncClient):
    # Verify recommended models catalog endpoint
    res = await client.get("/api/v1/providers/models")
    assert res.status_code == 200
    models = res.json()
    model_ids = [m["model_id"] for m in models]

    # Verify user-specified lineup
    assert "qwen.qwen3-32b-instruct-v1:0" in model_ids
    assert "qwen.qwen3-coder-30b-a3b-v1:0" in model_ids
    assert "qwen.qwen3-next-80b-a3b-v1:0" in model_ids
    assert "moonshot.kimi-k3-v1:0" in model_ids
    assert "mock-qwen3-32b" in model_ids

    # Verify exact reference pricing for Qwen3 32B ($0.1545 in / $0.618 out per 1M)
    qwen3 = next(m for m in models if m["model_id"] == "qwen.qwen3-32b-instruct-v1:0")
    assert qwen3["input_price_per_1m"] == 0.1545
    assert qwen3["output_price_per_1m"] == 0.618

    # Verify pricing calculation
    # 10,000 in, 2,000 out with Qwen3 32B:
    # in: 10000 / 1000000 * 0.1545 = 0.001545
    # out: 2000 / 1000000 * 0.618 = 0.001236
    # total = 0.002781
    cost = calculate_token_cost("qwen.qwen3-32b-instruct-v1:0", 10_000, 2_000)
    assert cost == pytest.approx(0.002781, rel=1e-3)

@pytest.mark.asyncio
async def test_mock_provider_generation():
    provider = MockProvider()
    assert await provider.validate_credentials() is True

    # Test initial question
    r1 = await provider.generate_text("Hello, start my interview", conversation_history=[])
    assert len(r1.text) > 20
    assert r1.input_tokens > 0
    assert r1.output_tokens > 0
    assert r1.estimated_cost_usd == 0.0

    # Test adaptive follow-up on Redis claim
    r2 = await provider.generate_text(
        "Can you ask follow-up?",
        conversation_history=[
            {"role": "assistant", "content": "Tell me about your architecture."},
            {"role": "user", "content": "We used Redis for caching to make things 10x faster."}
        ]
    )
    assert "redis" in r2.text.lower() or "faster" in r2.text.lower() or "latency" in r2.text.lower()

    # Test structured evaluation JSON
    eval_res = await provider.generate_json(
        prompt="Evaluate candidate performance against rubric",
        system_prompt="You are an expert technical evaluator."
    )
    assert eval_res.parsed_json is not None
    assert "overall_score" in eval_res.parsed_json
    assert "dimension_scores" in eval_res.parsed_json
    assert "strengths" in eval_res.parsed_json
    assert "weaknesses" in eval_res.parsed_json

import uuid

@pytest.mark.asyncio
async def test_user_provider_settings_workflow(client: httpx.AsyncClient):
    # Register test user with unique email
    email = f"provider_test_{uuid.uuid4().hex[:8]}@example.com"
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

    # Default provider should be mock
    cfg = await client.get("/api/v1/providers/config", headers=headers)
    assert cfg.status_code == 200
    assert cfg.json()["provider_name"] == "mock"
    assert cfg.json()["is_valid"] is True

    # Test updating mock config preferred model
    upd = await client.put(
        "/api/v1/providers/config",
        headers=headers,
        json={
            "provider_name": "mock",
            "preferred_model": "mock-qwen3-32b",
            "aws_region": "us-east-1"
        }
    )
    assert upd.status_code == 200
    assert upd.json()["preferred_model"] == "mock-qwen3-32b"

    # Delete credentials resets to default
    del_cred = await client.delete("/api/v1/providers/credentials", headers=headers)
    assert del_cred.status_code == 200
    assert del_cred.json()["provider_name"] == "mock"
