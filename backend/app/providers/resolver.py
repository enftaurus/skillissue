import json
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models import ProviderConfig
from backend.app.providers.models_catalog import (
    DEFAULT_MODEL_ID, DEFAULT_CODING_MODEL_ID, DEFAULT_EVALUATION_MODEL_ID,
    MOCK_MODEL_ID, get_model_metadata
)
from backend.app.core.security import decrypt_secret
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

@dataclass
class ModelResolutionResult:
    provider_name: str
    model_id: str
    access_key: Optional[str]
    secret_key: Optional[str]
    region: str
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    intended_provider: Optional[str] = None
    intended_model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048

class ModelResolver:
    """
    Unified resolution engine for model providers and models.
    Enforces identical precedence order across all services:
      1. Task-specific model override from ProviderConfig (interviewer, evaluation, coding, planning)
      2. Provider default model
      3. Environment / catalog defaults
      4. Explicit fallback tracking when live provider credentials or services are unavailable
    """

    @classmethod
    def resolve_model_id(cls, config: Optional[ProviderConfig], task_type: str = "general") -> str:
        if not config:
            if task_type == "coding":
                return DEFAULT_CODING_MODEL_ID
            elif task_type == "evaluation":
                return DEFAULT_EVALUATION_MODEL_ID
            return DEFAULT_MODEL_ID

        # 1. Task-specific override
        if task_type == "interviewer" and config.interviewer_model:
            return config.interviewer_model
        if task_type == "evaluation" and config.evaluation_model:
            return config.evaluation_model
        if task_type == "coding" and config.coding_model:
            return config.coding_model
        if task_type == "planning" and config.planning_model:
            return config.planning_model

        # 2. Provider default
        if config.default_model:
            return config.default_model
        if config.preferred_model:
            return config.preferred_model

        # 3. Catalog fallback
        if task_type == "coding":
            return DEFAULT_CODING_MODEL_ID
        elif task_type == "evaluation":
            return DEFAULT_EVALUATION_MODEL_ID
        return DEFAULT_MODEL_ID

    @classmethod
    async def resolve(
        cls,
        db: AsyncSession,
        user_id: str,
        task_type: str = "general",
    ) -> ModelResolutionResult:
        result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
        config = result.scalar_one_or_none()

        temperature = getattr(config, "temperature", 0.7) or 0.7
        max_tokens = getattr(config, "max_tokens", 2048) or 2048

        # 1. No configuration -> Offline mock mode
        if not config or config.provider_name == "mock":
            return ModelResolutionResult(
                provider_name="mock",
                model_id=cls.resolve_model_id(config, task_type) if config else MOCK_MODEL_ID,
                access_key=None,
                secret_key=None,
                region="us-east-1",
                is_fallback=False,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        intended_provider = config.provider_name
        intended_model = cls.resolve_model_id(config, task_type)

        # 2. Config marked invalid
        if not config.is_valid:
            if config.fallback_enabled:
                fallback_provider = config.fallback_provider or "mock"
                fallback_model = config.fallback_model or MOCK_MODEL_ID
                logger.warning(
                    f"Explicit Fallback: Provider config is marked invalid for user {user_id}. "
                    f"Intended {intended_provider}:{intended_model} -> Fallback {fallback_provider}:{fallback_model}"
                )
                return ModelResolutionResult(
                    provider_name=fallback_provider,
                    model_id=fallback_model,
                    access_key=None,
                    secret_key=None,
                    region="us-east-1",
                    is_fallback=True,
                    fallback_reason="Stored provider configuration is marked invalid",
                    intended_provider=intended_provider,
                    intended_model=intended_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise ProviderError("Provider configuration is invalid. Update credentials in Settings.", "INVALID_PROVIDER_CONFIG")

        # 3. Check spend budget ceiling
        from backend.app.providers.service import ProviderConfigService
        ProviderConfigService.check_spend_budget(config)

        # 4. Decrypt BYOC credentials in ephemeral memory
        access_key = None
        secret_key = None
        if config.aws_secret_key_enc:
            try:
                decrypted = decrypt_secret(config.aws_secret_key_enc, user_id=user_id)
                if decrypted:
                    try:
                        bundle = json.loads(decrypted)
                        if isinstance(bundle, dict):
                            access_key = bundle.get("access_key_id")
                            secret_key = bundle.get("secret_access_key")
                    except Exception:
                        secret_key = decrypted
                        access_key = decrypt_secret(config.aws_access_key_masked, user_id=user_id) if config.aws_access_key_masked.startswith("gAAAA") else config.aws_access_key_masked
            except Exception as e:
                logger.warning(f"Failed to decrypt credentials for user {user_id}: {e}")

        # 5. Handle missing credentials with explicit fallback
        if not access_key or not secret_key:
            fallback_provider = getattr(config, "fallback_provider", None) or "mock"
            fallback_model = getattr(config, "fallback_model", None) or MOCK_MODEL_ID
            logger.warning(
                f"Explicit Fallback: Incomplete or corrupted credentials for user {user_id}. "
                f"Intended {intended_provider}:{intended_model} -> Fallback {fallback_provider}:{fallback_model}"
            )
            return ModelResolutionResult(
                provider_name=fallback_provider,
                model_id=fallback_model,
                access_key=None,
                secret_key=None,
                region=config.aws_region or "us-east-1",
                is_fallback=True,
                fallback_reason="Incomplete or corrupted credentials in secure storage; fallback activated",
                intended_provider=intended_provider,
                intended_model=intended_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # 6. Valid resolved provider configuration
        return ModelResolutionResult(
            provider_name=intended_provider,
            model_id=intended_model,
            access_key=access_key,
            secret_key=secret_key,
            region=config.aws_region or "us-east-1",
            is_fallback=False,
            temperature=temperature,
            max_tokens=max_tokens,
        )
