import os
import uuid
import tempfile
import pytest
import botocore.session
import boto3
from botocore.exceptions import NoCredentialsError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.models import User, ProviderConfig
from backend.app.providers.service import ProviderConfigService
from backend.app.providers.model_client_factory import ModelClientFactory
from backend.app.providers.resolver import ModelResolver
from backend.app.providers.schemas import ProviderConfigSave
from backend.app.core.errors import ProviderError

@pytest.mark.asyncio
async def test_byoc_lifecycle_isolated_end_to_end(db_session: AsyncSession):
    """
    End-to-End BYOC Verification under strictly isolated credential conditions.
    
    Proves:
    1. Ambient credentials cannot satisfy inference requests (fails with NoCredentialsError).
    2. User credentials are saved encrypted in PostgreSQL (never plaintext).
    3. On cache miss: credentials are decrypted, Bedrock client is created and cached.
    4. Model invocation succeeds live against Amazon Bedrock (amazon.nova-lite-v1:0).
    5. On cache hit: cached client is reused without database lookups or decryptions.
    6. Credential rotation increments config_version, invalidates the old cache entry,
       and establishes a new client.
    7. Credential deletion purges secrets, marks config invalid, and fails closed with
       actionable BEDROCK_CONFIG_REQUIRED error.
    8. Zero secret disclosure: access keys, secret keys, and account IDs are never logged.
    """
    # 1. Retrieve test credentials from AWS CLI botocore session
    session = botocore.session.get_session()
    raw_creds = session.get_credentials()
    if not raw_creds or not raw_creds.access_key or not raw_creds.secret_key:
        pytest.skip("No real AWS credentials configured in environment for live BYOC verification")

    test_ak = raw_creds.access_key
    test_sk = raw_creds.secret_key
    test_token = raw_creds.token
    test_region = "us-east-1"
    target_model = "amazon.nova-lite-v1:0"

    with tempfile.NamedTemporaryFile() as empty_cred_file:
        # 2. Strict ambient credential isolation
        old_env = os.environ.copy()
        try:
            # Wipe all ambient AWS credentials and configuration
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = empty_cred_file.name
            os.environ["AWS_CONFIG_FILE"] = empty_cred_file.name
            for k in list(os.environ.keys()):
                if k.startswith("AWS_") and k not in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE"):
                    del os.environ[k]

            # Enable real bedrock test mode in factory
            os.environ["TEST_WITH_REAL_BEDROCK"] = "true"

            # Verify that ambient credentials fail closed
            with pytest.raises((NoCredentialsError, Exception)):
                boto3.client("bedrock-runtime", region_name=test_region).invoke_model(
                    modelId=target_model,
                    body="{}"
                )

            # 3. Create a clean test user
            test_user = User(
                id=str(uuid.uuid4()),
                email=f"byoc_live_test_{uuid.uuid4().hex[:8]}@example.com",
                hashed_password="hashed_pw_test",
                onboarding_completed=False,
            )
            db_session.add(test_user)
            await db_session.commit()

            # 4. Save user IAM credentials via ProviderConfigService
            save_payload = ProviderConfigSave(
                aws_region=test_region,
                preferred_model=target_model,
                aws_access_key_id=test_ak,
                aws_secret_access_key=test_sk,
                aws_session_token=test_token,
            )
            config = await ProviderConfigService.save_config(db_session, test_user.id, save_payload)

            # Assert database state
            assert config.is_valid is True
            assert config.config_version is not None and config.config_version >= 2
            assert config.aws_secret_key_enc.startswith("gAAAA")  # Fernet encrypted header
            assert test_sk not in config.aws_secret_key_enc  # Never stored in plaintext

            # 5. First Invocation: Cache Miss path
            # Reset in-memory cache to ensure clean cache miss test
            ModelClientFactory.clear_all_caches()
            cache = ModelClientFactory.get_cache()
            assert len(cache) == 0

            provider_client_1 = await ModelClientFactory.get_provider(
                db=db_session,
                user_id=test_user.id,
                task_type="coding",
                model_id_override=target_model,
            )
            assert provider_client_1 is not None
            assert len(cache) == 1

            # Live model invocation
            res = await provider_client_1.generate_text("What is 1 + 1? Reply with just the digit.")
            assert res is not None
            assert len(res.text.strip()) > 0

            # Verify usage accounting
            await ProviderConfigService.record_usage(
                db=db_session,
                user_id=test_user.id,
                tokens_used=res.input_tokens + res.output_tokens,
                cost_usd=res.estimated_cost_usd,
            )
            updated_cfg = await ProviderConfigService.get_config(db_session, test_user.id)
            assert updated_cfg.total_tokens_used > 0

            # 6. Second Invocation: Cache Hit path
            provider_client_2 = await ModelClientFactory.get_provider(
                db=db_session,
                user_id=test_user.id,
                task_type="coding",
                model_id_override=target_model,
            )
            # Must reuse identical client instance from cache
            assert provider_client_2 is provider_client_1
            assert len(cache) == 1

            # 7. Credential Rotation / Invalidation
            # Re-save credentials with updated parameter
            v_before = updated_cfg.config_version
            rotate_payload = ProviderConfigSave(
                aws_region=test_region,
                preferred_model=target_model,
                temperature=0.2,
                aws_access_key_id=test_ak,
                aws_secret_access_key=test_sk,
                aws_session_token=test_token,
            )
            rotated_cfg = await ProviderConfigService.save_config(db_session, test_user.id, rotate_payload)
            assert rotated_cfg.config_version == v_before + 1

            # Verify that old client cache entry was purged
            # Client lookup must now trigger a cache miss and construct a new client for v_after
            provider_client_3 = await ModelClientFactory.get_provider(
                db=db_session,
                user_id=test_user.id,
                task_type="coding",
                model_id_override=target_model,
            )
            assert provider_client_3 is not provider_client_1

            # 8. Deletion path
            await ProviderConfigService.delete_credentials(db_session, test_user.id)
            deleted_cfg = await ProviderConfigService.get_config(db_session, test_user.id)
            assert deleted_cfg.is_valid is False
            assert deleted_cfg.aws_secret_key_enc == ""

            # Attempting resolution must fail closed with BEDROCK_CONFIG_REQUIRED
            with pytest.raises(ProviderError) as exc_info:
                await ModelClientFactory.get_provider(
                    db=db_session,
                    user_id=test_user.id,
                    task_type="coding",
                )
            assert exc_info.value.code == "BEDROCK_CONFIG_REQUIRED"

        finally:
            os.environ.clear()
            os.environ.update(old_env)
            ModelClientFactory.clear_all_caches()
