import uuid
import pytest
import httpx
from backend.app.providers.models_catalog import SUPPORTED_MODELS, calculate_token_cost, generate_iam_policy
from backend.app.providers.mock_provider import MockProvider
from backend.app.core.errors import ProviderError

@pytest.mark.asyncio
async def test_models_catalog_lineup(client: httpx.AsyncClient):
    # Verify recommended models catalog endpoint
    res = await client.get("/api/v1/providers/models")
    assert res.status_code == 200
    models = res.json()
    model_ids = [m["model_id"] for m in models]

    # Verify Chinese models lineup is primary
    assert "qwen.qwen3-32b-v1:0" in model_ids
    assert "qwen.qwen3-coder-30b-a3b-v1:0" in model_ids
    assert "deepseek.v3.2" in model_ids
    assert "us.deepseek.r1-v1:0" in model_ids
    assert "mock-qwen3-32b" not in model_ids

    # Verify Qwen3 32B is default model ($0.1545 in / $0.618 out per 1M)
    qwen_default = next(m for m in models if m["model_id"] == "qwen.qwen3-32b-v1:0")
    assert qwen_default["input_price_per_1m"] == 0.1545
    assert qwen_default["output_price_per_1m"] == 0.618
    assert qwen_default["is_default"] is True

    # Verify pricing calculation
    # 10,000 in, 2,000 out with Qwen3 32B:
    # in: 10000 / 1000000 * 0.1545 = 0.001545
    # out: 2000 / 1000000 * 0.618 = 0.001236
    # total = 0.002781
    cost = calculate_token_cost("qwen.qwen3-32b-v1:0", 10_000, 2_000)
    assert cost == pytest.approx(0.002781, rel=1e-3)

@pytest.mark.asyncio
async def test_iam_policy_generation(client: httpx.AsyncClient):
    # Test IAM policy generator endpoint with Qwen and DeepSeek
    res = await client.get("/api/v1/providers/iam-policy?model_id=qwen.qwen3-32b-v1:0&region=us-east-1")
    assert res.status_code == 200
    data = res.json()
    assert "policy_json" in data
    assert "bedrock:InvokeModel" in data["policy_json"]
    assert "bedrock:InvokeModelWithResponseStream" in data["policy_json"]
    assert "qwen.qwen3-32b-v1:0" in data["policy_json"]
    assert "actions_explained" in data

    # Test IAM policy generator for DeepSeek-R1 inference profile
    res_ds = await client.get("/api/v1/providers/iam-policy?model_id=us.deepseek.r1-v1:0&region=us-east-1")
    assert res_ds.status_code == 200
    ds_data = res_ds.json()
    assert "us.deepseek.r1-v1:0" in ds_data["policy_json"]
    assert "deepseek.r1-v1:0" in ds_data["policy_json"]

@pytest.mark.asyncio
async def test_mock_provider_test_double():
    """Verify test double provider operates deterministically for offline testing."""
    provider = MockProvider()
    assert await provider.validate_credentials() is True

    r1 = await provider.generate_text("Hello, start my interview", conversation_history=[])
    assert len(r1.text) > 20
    assert r1.input_tokens > 0

    eval_res = await provider.generate_json(
        prompt="Evaluate candidate performance against rubric",
        system_prompt="You are an expert technical evaluator."
    )
    assert eval_res.parsed_json is not None
    assert "overall_score" in eval_res.parsed_json

@pytest.mark.asyncio
async def test_user_provider_settings_workflow(client: httpx.AsyncClient):
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

    # Default provider should be unconfigured Bedrock (is_valid=False)
    cfg = await client.get("/api/v1/providers/config", headers=headers)
    assert cfg.status_code == 200
    assert cfg.json()["provider_name"] == "bedrock"
    assert cfg.json()["is_valid"] is False

    # Delete credentials resets to unconfigured state
    del_cred = await client.delete("/api/v1/providers/credentials", headers=headers)
    assert del_cred.status_code == 200
    assert del_cred.json()["is_valid"] is False

@pytest.mark.asyncio
async def test_provider_credential_encryption_and_routing():
    """Verify ProviderConfig stores and decrypts unmasked Access Key ID and fails closed without silent mock fallback."""
    import json
    from unittest.mock import AsyncMock, MagicMock
    from backend.app.database.models import ProviderConfig
    from backend.app.core.security import encrypt_secret
    from backend.app.providers.factory import ModelFactory
    from backend.app.providers.bedrock import AmazonBedrockProvider

    full_access_key = "AKIAIOSFODNN7EXAMPLE"
    full_secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    bundle = json.dumps({"access_key_id": full_access_key, "secret_access_key": full_secret_key})
    mock_config = ProviderConfig(
        user_id="test-user-123",
        provider_name="bedrock",
        aws_region="us-east-1",
        aws_access_key_masked="AKIA...MPLE",
        aws_secret_key_enc=encrypt_secret(bundle),
        preferred_model="amazon.nova-pro-v1:0",
        is_valid=True,
    )

    db_mock = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    db_mock.execute.return_value = mock_res

    # 1. Verify get_for_user decrypts full unmasked credentials
    provider = await ModelFactory.get_for_user(db_mock, "test-user-123", task_type="general")
    assert isinstance(provider, AmazonBedrockProvider)
    assert provider.aws_access_key_id == full_access_key
    assert provider.aws_secret_access_key == full_secret_key
    assert provider.model_id == "amazon.nova-pro-v1:0"

    # 2. Corrupted ciphertext must fail closed with ProviderError (no silent fallback!)
    from backend.app.providers.model_client_factory import ModelClientFactory
    ModelClientFactory.clear_cache_for_user("test-user-123")
    mock_config.aws_secret_key_enc = "corrupted-ciphertext-invalid-token"
    with pytest.raises(ProviderError, match="could not be decrypted or are incomplete"):
        await ModelFactory.get_for_user(db_mock, "test-user-123", task_type="general")
