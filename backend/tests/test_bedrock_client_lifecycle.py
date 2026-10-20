import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from botocore.exceptions import ClientError, EndpointConnectionError
from backend.app.database.models import ProviderConfig
from backend.app.core.security import encrypt_secret
from backend.app.core.errors import ProviderError, AppException
from backend.app.providers.bedrock import AmazonBedrockProvider, map_bedrock_client_error
from backend.app.providers.factory import ModelFactory
from backend.app.providers.model_client_factory import (
    ModelClientFactory, ClientCacheKey, BoundedClientCache
)
from backend.app.providers.resolver import ModelResolver, UserConfigMetadata
from backend.app.providers.service import ProviderConfigService

def make_mock_config(user_id: str, access_key: str, secret_key: str, version: int = 1):
    bundle = json.dumps({"access_key_id": access_key, "secret_access_key": secret_key})
    return ProviderConfig(
        user_id=user_id,
        provider_name="bedrock",
        aws_region="us-east-1",
        aws_access_key_masked=access_key[:4] + "..." + access_key[-4:],
        aws_secret_key_enc=encrypt_secret(bundle, user_id=user_id),
        preferred_model="amazon.nova-lite-v1:0",
        default_model="amazon.nova-lite-v1:0",
        config_version=version,
        is_valid=True,
        monthly_token_budget=1_000_000,
        monthly_tokens_used=0,
        monthly_cost_cents_budget=1000,
        monthly_cost_cents_used=0,
    )

@pytest.fixture(autouse=True)
def clean_client_cache():
    """Ensure a clean in-memory client and metadata cache for each test."""
    ModelClientFactory.clear_all_caches()
    yield
    ModelClientFactory.clear_all_caches()

@pytest.mark.asyncio
async def test_repeated_calls_reuse_same_client():
    """Requirement 1 & 2: Repeated calls reuse the cached client without re-creating instances."""
    mock_config = make_mock_config("user_reuse", "AKIAREUSE12345678", "secret_reuse_key")
    db_mock = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    db_mock.execute.return_value = mock_res

    # 1st call: cache miss
    client1 = await ModelFactory.get_for_user(db_mock, "user_reuse", task_type="general")
    assert isinstance(client1, AmazonBedrockProvider)

    # 2nd call: cache hit
    client2 = await ModelFactory.get_for_user(db_mock, "user_reuse", task_type="general")
    assert client1 is client2, "Repeated calls must return the identical cached client instance"

@pytest.mark.asyncio
async def test_identical_effective_config_shares_client_across_tasks():
    """Requirement 3: Tasks with identical effective model/region/parameters share the same client."""
    mock_config = make_mock_config("user_tasks", "AKIATASKS12345678", "secret_tasks_key")
    # Both coding and interviewer default to preferred_model (amazon.nova-lite-v1:0)
    mock_config.interviewer_model = None
    mock_config.coding_model = None

    db_mock = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    db_mock.execute.return_value = mock_res

    client_interview = await ModelFactory.get_for_user(db_mock, "user_tasks", task_type="interviewer")
    client_coding = await ModelFactory.get_for_user(db_mock, "user_tasks", task_type="coding")

    assert client_interview is client_coding, (
        "Different task names must reuse the same client when their effective configuration is identical"
    )

@pytest.mark.asyncio
async def test_distinct_users_never_share_clients():
    """Requirement 4: Strict tenant isolation — users never share clients even with identical models."""
    config_alice = make_mock_config("user_alice", "AKIAALICE12345678", "secret_alice_key")
    config_bob = make_mock_config("user_bob", "AKIABOB1234567890", "secret_bob_key")

    db_alice = AsyncMock()
    res_alice = MagicMock()
    res_alice.scalar_one_or_none.return_value = config_alice
    db_alice.execute.return_value = res_alice

    db_bob = AsyncMock()
    res_bob = MagicMock()
    res_bob.scalar_one_or_none.return_value = config_bob
    db_bob.execute.return_value = res_bob

    client_alice = await ModelFactory.get_for_user(db_alice, "user_alice", task_type="general")
    client_bob = await ModelFactory.get_for_user(db_bob, "user_bob", task_type="general")

    assert client_alice is not client_bob, "Different users must never share SDK clients"
    assert client_alice.aws_access_key_id == "AKIAALICE12345678"
    assert client_bob.aws_access_key_id == "AKIABOB1234567890"

@pytest.mark.asyncio
async def test_no_credential_decryption_on_cache_hit():
    """Requirement 2 & 7: Credentials are decrypted strictly on cache miss, never on cache hit."""
    mock_config = make_mock_config("user_crypto", "AKIACRYPTO1234567", "secret_crypto_key")
    db_mock = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    db_mock.execute.return_value = mock_res

    decrypt_count = 0
    real_decrypt = ModelResolver.resolve_credentials

    async def spy_resolve_credentials(db, uid):
        nonlocal decrypt_count
        decrypt_count += 1
        return await real_decrypt(db, uid)

    with patch.object(ModelResolver, "resolve_credentials", side_effect=spy_resolve_credentials):
        # 1st call: cache miss -> decrypter invoked
        c1 = await ModelFactory.get_for_user(db_mock, "user_crypto", task_type="general")
        assert decrypt_count == 1

        # 2nd to 6th calls: cache hit -> decrypter NEVER invoked
        for _ in range(5):
            c_hit = await ModelFactory.get_for_user(db_mock, "user_crypto", task_type="general")
            assert c_hit is c1
            assert decrypt_count == 1, "Credentials must not be decrypted on cache hit"

@pytest.mark.asyncio
async def test_configuration_change_invalidates_cache_and_increments_version():
    """Requirement 5: Config change increments version and invalidates local cache immediately."""
    mock_config = make_mock_config("user_inval", "AKIAINVAL11111111", "secret_inval_1", version=1)
    db_mock = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    db_mock.execute.return_value = mock_res

    # 1. First client under version 1
    c1 = await ModelFactory.get_for_user(db_mock, "user_inval", task_type="general")
    assert c1.aws_access_key_id == "AKIAINVAL11111111"

    # 2. Simulate credential rotation: increment version & invalidate cache
    mock_config.config_version = 2
    mock_config.aws_access_key_masked = "AKIA...2222"
    mock_config.aws_secret_key_enc = encrypt_secret(
        json.dumps({"access_key_id": "AKIAINVAL22222222", "secret_access_key": "secret_inval_2"}),
        user_id="user_inval"
    )
    ModelClientFactory.clear_cache_for_user("user_inval")

    # 3. Next call must create a new client under version 2
    c2 = await ModelFactory.get_for_user(db_mock, "user_inval", task_type="general")
    assert c2 is not c1, "Rotated credentials must invalidate the old client"
    assert c2.aws_access_key_id == "AKIAINVAL22222222"

@pytest.mark.asyncio
async def test_cache_idle_ttl_expiration():
    """Requirement 6: Idle entries expire after idle_ttl_seconds."""
    cache = BoundedClientCache(max_size=10, idle_ttl_seconds=50.0)
    key = ClientCacheKey("provider", "user_idle", 1, "us-east-1", "amazon.nova-lite-v1:0", 0.7, 2048)
    dummy_client = {"mock": "client"}

    cache.set(key, dummy_client)
    assert cache.get(key) is dummy_client

    # Simulate 51 seconds passing
    with patch("time.time", return_value=time.time() + 51.0):
        expired = cache.get(key)
        assert expired is None, "Client must expire after idle TTL"
        assert len(cache) == 0, "Expired entry must be purged from cache"

@pytest.mark.asyncio
async def test_bounded_cache_hard_size_limit_and_lru():
    """Requirement 6: Hard cache size limit evicts least-recently-used entry safely."""
    cache = BoundedClientCache(max_size=3, idle_ttl_seconds=300.0)

    key1 = ClientCacheKey("provider", "u1", 1, "us-east-1", "m", 0.7, 100)
    key2 = ClientCacheKey("provider", "u2", 1, "us-east-1", "m", 0.7, 100)
    key3 = ClientCacheKey("provider", "u3", 1, "us-east-1", "m", 0.7, 100)
    key4 = ClientCacheKey("provider", "u4", 1, "us-east-1", "m", 0.7, 100)

    cache.set(key1, "client1")
    cache.set(key2, "client2")
    cache.set(key3, "client3")

    # Access key1 to make key2 the least-recently used
    assert cache.get(key1) == "client1"

    # Add 4th item -> must evict key2 (the LRU entry)
    cache.set(key4, "client4")

    assert len(cache) == 3, "Cache must not exceed max_size"
    assert cache.get(key2) is None, "Key2 should have been evicted as LRU"
    assert cache.get(key1) == "client1", "Key1 was recently accessed and must remain"
    assert cache.get(key3) == "client3"
    assert cache.get(key4) == "client4"

@pytest.mark.asyncio
async def test_multi_worker_stale_config_recovery():
    """Requirement 5 & 10: Multi-worker replica does not retain stale config indefinitely."""
    # Worker A cached metadata for version 1
    mock_config = make_mock_config("user_worker", "AKIAWORKER111111", "sec1", version=1)
    db_mock = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    db_mock.execute.return_value = mock_res

    c1 = await ModelFactory.get_for_user(db_mock, "user_worker", task_type="general")
    assert c1.aws_access_key_id == "AKIAWORKER111111"

    # Simulate Worker B updating DB to version 2 (without Worker A getting in-process notify)
    mock_config.config_version = 2
    mock_config.aws_access_key_masked = "AKIA...2222"
    mock_config.aws_secret_key_enc = encrypt_secret(
        json.dumps({"access_key_id": "AKIAWORKER222222", "secret_access_key": "sec2"}),
        user_id="user_worker"
    )

    # When metadata TTL expires (simulated by force_refresh or TTL expiry)
    with patch("time.time", return_value=time.time() + 65.0):
        c2 = await ModelFactory.get_for_user(db_mock, "user_worker", task_type="general")
        assert c2 is not c1, "Worker A must pick up new version after metadata TTL"
        assert c2.aws_access_key_id == "AKIAWORKER222222"

@pytest.mark.asyncio
async def test_explicit_error_mapping_without_silent_mock():
    """Requirement 9: AWS Bedrock ClientError responses map to typed ProviderError without mock fallback."""
    def make_client_error(code: str, message: str = ""):
        return ClientError(
            {"Error": {"Code": code, "Message": message}},
            "Converse"
        )

    # 1. Expired session token
    err1 = map_bedrock_client_error(make_client_error("ExpiredTokenException"), "m", "us-east-1")
    assert err1.code == "EXPIRED_SESSION_TOKEN"

    # 2. Access Denied (IAM)
    err2 = map_bedrock_client_error(make_client_error("AccessDeniedException"), "m", "us-east-1")
    assert err2.code == "PERMISSION_DENIED"

    # 3. Throttling
    err3 = map_bedrock_client_error(make_client_error("ThrottlingException"), "m", "us-east-1")
    assert err3.code == "THROTTLED"

    # 4. Invalid credentials
    err4 = map_bedrock_client_error(make_client_error("UnrecognizedClientException"), "m", "us-east-1")
    assert err4.code == "INVALID_CREDENTIALS"

    # 5. Model unavailable
    err5 = map_bedrock_client_error(make_client_error("ResourceNotFoundException"), "m", "us-east-1")
    assert err5.code == "MODEL_UNAVAILABLE"

    # 6. Validation error
    err6 = map_bedrock_client_error(make_client_error("ValidationException", "bad params"), "m", "us-east-1")
    assert err6.code == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_budget_enforcement_blocks_inference():
    """Requirement 8: Spend budget ceiling blocks inference with HTTP 429 AppException."""
    # 1. Token budget exceeded
    config_token_limit = make_mock_config("user_token_limit", "AKIATOKEN12345678", "secret_token_key")
    config_token_limit.monthly_token_budget = 50_000
    config_token_limit.monthly_tokens_used = 50_001

    db_mock = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = config_token_limit
    db_mock.execute.return_value = res_mock

    with pytest.raises(AppException) as exc_info:
        await ModelFactory.get_for_user(db_mock, "user_token_limit", task_type="general")
    assert exc_info.value.code == "TOKEN_BUDGET_EXCEEDED"
    assert exc_info.value.status_code == 429

    # 2. Cost budget exceeded
    ModelClientFactory.clear_all_caches()
    config_cost_limit = make_mock_config("user_cost_limit", "AKIACOST123456789", "secret_cost_key")
    config_cost_limit.monthly_cost_cents_budget = 1000  # $10.00
    config_cost_limit.monthly_cost_cents_used = 1000   # $10.00 reached

    res_mock.scalar_one_or_none.return_value = config_cost_limit
    with pytest.raises(AppException) as exc_info:
        await ModelFactory.get_for_user(db_mock, "user_cost_limit", task_type="general")
    assert exc_info.value.code == "COST_BUDGET_EXCEEDED"
    assert exc_info.value.status_code == 429

@pytest.mark.asyncio
async def test_concurrent_usage_accounting_atomic(db_session: AsyncSession):
    """Requirement 8: Concurrent requests record usage atomically without race condition lost updates."""
    import uuid
    from backend.app.database.models import User
    from sqlalchemy import select

    unique_email = f"concurrent_usage_{uuid.uuid4().hex[:8]}@example.com"
    test_user = User(email=unique_email, hashed_password="hashed_pw_test", onboarding_completed=True)
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    config = ProviderConfig(
        user_id=test_user.id,
        provider_name="bedrock",
        aws_region="us-east-1",
        preferred_model="amazon.nova-lite-v1:0",
        monthly_tokens_used=0,
        monthly_cost_cents_used=0,
        total_tokens_used=0,
        estimated_cost_usd=0.0,
        is_valid=True
    )
    db_session.add(config)
    await db_session.commit()

    # Launch 10 concurrent usage updates of 100 tokens and $0.05 (5 cents) each
    from backend.app.database.session import AsyncSessionLocal

    async def record_one():
        async with AsyncSessionLocal() as sess:
            await ProviderConfigService.record_usage(sess, test_user.id, tokens_used=100, cost_usd=0.05)

    await asyncio.gather(*(record_one() for _ in range(10)))

    # Fetch final recorded state from database via a fresh session
    async with AsyncSessionLocal() as verify_sess:
        refreshed_res = await verify_sess.execute(select(ProviderConfig).where(ProviderConfig.user_id == test_user.id))
        final_config = refreshed_res.scalar_one()

    # 10 x 100 tokens = 1000 tokens exact
    assert final_config.monthly_tokens_used == 1000
    assert final_config.total_tokens_used == 1000
    # 10 x 5 cents = 50 cents ($0.50)
    assert final_config.monthly_cost_cents_used == 50
    assert final_config.estimated_cost_usd == pytest.approx(0.50, rel=1e-3)

@pytest.mark.asyncio
async def test_missing_bedrock_config_fails_closed_without_mock():
    """Requirement 8: Outside test mock double, unconfigured user causes explicit ProviderError with setup URL."""
    db_mock = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = None  # No config
    db_mock.execute.return_value = res_mock

    # Temporarily unset PYTEST_CURRENT_TEST to simulate production execution
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        if "PYTEST_CURRENT_TEST" in os.environ:
            del os.environ["PYTEST_CURRENT_TEST"]
        try:
            with pytest.raises(ProviderError) as exc_info:
                await ModelFactory.get_for_user(db_mock, "unconfigured_user", task_type="general")
            assert exc_info.value.code == "BEDROCK_CONFIG_REQUIRED"
            assert "/onboarding/bedrock" in exc_info.value.message
        finally:
            os.environ["PYTEST_CURRENT_TEST"] = "1"


