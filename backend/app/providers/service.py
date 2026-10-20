import json
import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models import ProviderConfig
from backend.app.providers.schemas import ProviderConfigSave, TestCredentialsRequest, TestCredentialsResponse
from backend.app.providers.factory import ModelFactory
from backend.app.core.security import encrypt_secret, mask_access_key
from backend.app.core.errors import AppException, EntityNotFoundError, ProviderError
from backend.app.core.logging import logger

class ProviderConfigService:
    @staticmethod
    async def get_config(db: AsyncSession, user_id: str) -> ProviderConfig:
        result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
        config = result.scalar_one_or_none()
        if not config:
            # Create default mock config if none exists
            config = ProviderConfig(
                user_id=user_id,
                provider_name="mock",
                preferred_model="mock-qwen3-32b",
                is_valid=True
            )
            db.add(config)
            await db.commit()
            await db.refresh(config)
        return config

    @staticmethod
    def check_spend_budget(config: ProviderConfig):
        """Verify user has not exceeded their configured monthly token or cost ceiling."""
        if config.provider_name == "mock":
            return  # Mock provider is zero-cost and unlimited

        if config.monthly_token_budget and config.monthly_tokens_used >= config.monthly_token_budget:
            raise AppException(
                f"Monthly token budget ({config.monthly_token_budget:,} tokens) reached. "
                "Increase your budget under Settings → Model Provider or use Mock mode.",
                code="TOKEN_BUDGET_EXCEEDED",
                status_code=429
            )

        if config.monthly_cost_cents_budget and config.monthly_cost_cents_used >= config.monthly_cost_cents_budget:
            spent_usd = config.monthly_cost_cents_used / 100.0
            budget_usd = config.monthly_cost_cents_budget / 100.0
            raise AppException(
                f"Monthly cost limit (${budget_usd:.2f}) reached (spent: ${spent_usd:.2f}). "
                "Increase your budget under Settings → Model Provider or use Mock mode.",
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
    async def save_config(db: AsyncSession, user_id: str, data: ProviderConfigSave) -> ProviderConfig:
        config = await ProviderConfigService.get_config(db, user_id)

        config.provider_name = data.provider_name
        config.aws_region = data.aws_region
        config.preferred_model = data.preferred_model
        config.default_model = data.default_model or data.preferred_model
        config.interviewer_model = data.interviewer_model
        config.evaluation_model = data.evaluation_model
        config.coding_model = data.coding_model
        config.planning_model = data.planning_model
        config.fallback_enabled = data.fallback_enabled
        config.fallback_provider = data.fallback_provider
        config.fallback_model = data.fallback_model
        if data.temperature is not None:
            config.temperature = data.temperature
        if data.max_tokens is not None:
            config.max_tokens = data.max_tokens
        if data.monthly_token_budget is not None:
            config.monthly_token_budget = data.monthly_token_budget
        if data.monthly_cost_cents_budget is not None:
            config.monthly_cost_cents_budget = data.monthly_cost_cents_budget

        if data.provider_name == "mock":
            config.is_valid = True
            config.last_tested_at = datetime.now(timezone.utc)
            config.aws_access_key_masked = "LOCAL_MOCK"
            config.aws_secret_key_enc = ""
        else:
            # Bedrock configuration
            if not data.aws_access_key_id or not data.aws_secret_access_key:
                # Check if we already have valid credentials stored
                if not config.aws_secret_key_enc:
                    raise AppException("AWS Access Key ID and Secret Access Key are required.", code="MISSING_CREDENTIALS")
            else:
                # Validate live credentials before persisting
                test_res = await ProviderConfigService.test_credentials(
                    TestCredentialsRequest(
                        provider_name="bedrock",
                        aws_region=data.aws_region,
                        aws_access_key_id=data.aws_access_key_id,
                        aws_secret_access_key=data.aws_secret_access_key,
                        preferred_model=data.preferred_model,
                    )
                )
                if not test_res.success:
                    raise AppException(test_res.message, code="INVALID_CREDENTIALS")

                # Store encrypted credentials bundle using tenant-isolated key and masked display
                creds_bundle = json.dumps({
                    "access_key_id": data.aws_access_key_id,
                    "secret_access_key": data.aws_secret_access_key,
                })
                config.aws_access_key_masked = mask_access_key(data.aws_access_key_id)
                config.aws_secret_key_enc = encrypt_secret(creds_bundle, user_id=user_id)
                config.is_valid = True
                config.last_tested_at = datetime.now(timezone.utc)

        from backend.app.providers.model_client_factory import ModelClientFactory
        ModelClientFactory.clear_cache_for_user(user_id)

        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def delete_credentials(db: AsyncSession, user_id: str) -> ProviderConfig:
        config = await ProviderConfigService.get_config(db, user_id)
        config.provider_name = "mock"
        config.aws_access_key_masked = ""
        config.aws_secret_key_enc = ""
        config.preferred_model = "mock-qwen3-32b"
        config.default_model = "mock-qwen3-32b"
        config.interviewer_model = None
        config.evaluation_model = None
        config.coding_model = None
        config.planning_model = None
        config.is_valid = True
        config.last_tested_at = None

        from backend.app.providers.model_client_factory import ModelClientFactory
        ModelClientFactory.clear_cache_for_user(user_id)

        await db.commit()
        await db.refresh(config)
        logger.info(f"Permanently purged stored BYOC credentials for user {user_id}")
        return config

    @staticmethod
    async def record_usage(db: AsyncSession, user_id: str, tokens_used: int, cost_usd: float):
        result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
        config = result.scalar_one_or_none()
        if config:
            config.total_tokens_used += tokens_used
            config.estimated_cost_usd += cost_usd
            config.monthly_tokens_used += tokens_used
            cost_cents = int(round(cost_usd * 100))
            config.monthly_cost_cents_used += cost_cents
            await db.commit()
