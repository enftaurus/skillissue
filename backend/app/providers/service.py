import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.app.database.models import ProviderConfig, User
from backend.app.providers.schemas import ProviderConfigSave, TestCredentialsRequest, TestCredentialsResponse
from backend.app.providers.factory import ModelFactory
from backend.app.providers.models_catalog import (
    DEFAULT_MODEL_ID, DEFAULT_CODING_MODEL_ID, DEFAULT_EVALUATION_MODEL_ID,
    generate_iam_policy
)
from backend.app.core.security import encrypt_secret, mask_access_key
from backend.app.core.errors import AppException, EntityNotFoundError, ProviderError
from backend.app.core.logging import logger

class ProviderConfigService:
    @staticmethod
    async def get_config(db: AsyncSession, user_id: str) -> ProviderConfig:
        result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
        config = result.scalar_one_or_none()
        if not config:
            # Create unconfigured Bedrock config requiring setup
            config = ProviderConfig(
                user_id=user_id,
                provider_name="bedrock",
                preferred_model=DEFAULT_MODEL_ID,
                default_model=DEFAULT_MODEL_ID,
                aws_region="us-east-1",
                is_valid=False
            )
            db.add(config)
            await db.commit()
            await db.refresh(config)
        return config

    @staticmethod
    def check_spend_budget(config: ProviderConfig):
        """Verify user has not exceeded their configured monthly token or cost ceiling."""
        if config.monthly_token_budget and config.monthly_tokens_used >= config.monthly_token_budget:
            raise AppException(
                f"Monthly token budget ({config.monthly_token_budget:,} tokens) reached. "
                "Increase your budget under Settings → Model Provider.",
                code="TOKEN_BUDGET_EXCEEDED",
                status_code=429
            )

        if config.monthly_cost_cents_budget and config.monthly_cost_cents_used >= config.monthly_cost_cents_budget:
            spent_usd = config.monthly_cost_cents_used / 100.0
            budget_usd = config.monthly_cost_cents_budget / 100.0
            raise AppException(
                f"Monthly cost limit (${budget_usd:.2f}) reached (spent: ${spent_usd:.2f}). "
                "Increase your budget under Settings → Model Provider.",
                code="COST_BUDGET_EXCEEDED",
                status_code=429
            )

    @staticmethod
    async def test_credentials(data: TestCredentialsRequest) -> TestCredentialsResponse:
        start_time = time.time()
        provider = ModelFactory.get_provider_by_type(
            provider_name=data.provider_name,
            model_id=data.preferred_model,
            aws_access_key=data.aws_access_key_id,
            aws_secret_key=data.aws_secret_access_key,
            aws_region=data.aws_region,
            aws_session_token=data.aws_session_token,
        )
        try:
            await provider.validate_credentials()
            latency = int((time.time() - start_time) * 1000)
            return TestCredentialsResponse(
                success=True,
                message=f"Successfully verified access to {data.preferred_model} in {data.aws_region}.",
                model_id=data.preferred_model,
                latency_ms=latency
            )
        except ProviderError as e:
            return TestCredentialsResponse(
                success=False,
                message=f"Validation failed: {e.message}",
                model_id=data.preferred_model
            )

    @staticmethod
    def get_iam_policy_doc(model_id: str, region: str) -> Dict[str, Any]:
        return generate_iam_policy(model_id=model_id, aws_region=region)

    @staticmethod
    async def save_config(db: AsyncSession, user_id: str, data: ProviderConfigSave) -> ProviderConfig:
        config = await ProviderConfigService.get_config(db, user_id)

        config.provider_name = "bedrock"
        config.aws_region = data.aws_region
        config.preferred_model = data.preferred_model or DEFAULT_MODEL_ID
        config.default_model = data.default_model or config.preferred_model
        config.interviewer_model = data.interviewer_model
        config.evaluation_model = data.evaluation_model
        config.coding_model = data.coding_model
        config.planning_model = data.planning_model
        if data.fallback_enabled is not None:
            config.fallback_enabled = data.fallback_enabled
        if data.temperature is not None:
            config.temperature = data.temperature
        if data.max_tokens is not None:
            config.max_tokens = data.max_tokens
        if data.monthly_token_budget is not None:
            config.monthly_token_budget = data.monthly_token_budget
        if data.monthly_cost_cents_budget is not None:
            config.monthly_cost_cents_budget = data.monthly_cost_cents_budget

        # If new access keys are submitted, test before saving
        if data.aws_access_key_id and data.aws_secret_access_key:
            test_res = await ProviderConfigService.test_credentials(
                TestCredentialsRequest(
                    provider_name="bedrock",
                    aws_region=data.aws_region,
                    aws_access_key_id=data.aws_access_key_id,
                    aws_secret_access_key=data.aws_secret_access_key,
                    aws_session_token=data.aws_session_token,
                    preferred_model=config.preferred_model,
                )
            )
            if not test_res.success:
                raise AppException(test_res.message, code="INVALID_CREDENTIALS")

            creds_bundle = json.dumps({
                "access_key_id": data.aws_access_key_id,
                "secret_access_key": data.aws_secret_access_key,
                "session_token": data.aws_session_token,
            })
            config.aws_access_key_masked = mask_access_key(data.aws_access_key_id)
            config.aws_secret_key_enc = encrypt_secret(creds_bundle, user_id=user_id)
            config.is_valid = True
            config.last_tested_at = datetime.now(timezone.utc)

            # Mark user onboarding complete
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            if user:
                user.onboarding_completed = True
        elif not config.aws_secret_key_enc:
            raise AppException("AWS Access Key ID and Secret Access Key are required.", code="MISSING_CREDENTIALS")

        # Increment configuration version to reliably invalidate cached clients across processes/replicas
        config.config_version = (config.config_version or 1) + 1

        from backend.app.providers.model_client_factory import ModelClientFactory
        ModelClientFactory.clear_cache_for_user(user_id)

        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def delete_credentials(db: AsyncSession, user_id: str) -> ProviderConfig:
        config = await ProviderConfigService.get_config(db, user_id)
        config.aws_access_key_masked = ""
        config.aws_secret_key_enc = ""
        config.is_valid = False
        config.last_tested_at = None
        config.config_version = (config.config_version or 1) + 1

        # Revert onboarding status
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        if user:
            user.onboarding_completed = False

        from backend.app.providers.model_client_factory import ModelClientFactory
        ModelClientFactory.clear_cache_for_user(user_id)

        await db.commit()
        await db.refresh(config)
        logger.info(f"Purged stored BYOC credentials for user {user_id}")
        return config

    @staticmethod
    async def record_usage(db: AsyncSession, user_id: str, tokens_used: int, cost_usd: float):
        """
        Record usage using an atomic SQL UPDATE to eliminate race conditions under concurrent requests.
        Also synchronizes in-memory cached usage.
        """
        cost_cents = int(round(cost_usd * 100))
        stmt = (
            update(ProviderConfig)
            .where(ProviderConfig.user_id == user_id)
            .values(
                total_tokens_used=ProviderConfig.total_tokens_used + tokens_used,
                estimated_cost_usd=ProviderConfig.estimated_cost_usd + cost_usd,
                monthly_tokens_used=ProviderConfig.monthly_tokens_used + tokens_used,
                monthly_cost_cents_used=ProviderConfig.monthly_cost_cents_used + cost_cents,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.execute(stmt)
        await db.commit()

        from backend.app.providers.resolver import ModelResolver
        ModelResolver.update_cached_usage(user_id, tokens_used, cost_cents)
