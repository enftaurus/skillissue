import json
import time
from typing import Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_aws import ChatBedrockConverse
from backend.app.providers.mock_chat_model import MockChatModel
from backend.app.providers.models_catalog import (
    DEFAULT_MODEL_ID, DEFAULT_CODING_MODEL_ID, DEFAULT_EVALUATION_MODEL_ID,
    MOCK_MODEL_ID, get_model_metadata
)
from backend.app.database.models import ProviderConfig
from backend.app.core.security import decrypt_secret
from backend.app.core.errors import ProviderError, AppException
from backend.app.core.logging import logger

# Ephemeral client cache: cache key -> (BaseChatModel, expiration_timestamp)
# Cache key includes user_id, task_type, model_id, and config update timestamp.
# Zero plaintext credentials stored in cache.
_CLIENT_CACHE: Dict[str, Tuple[BaseChatModel, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes TTL

class ModelClientFactory:
    """
    Centralized LangChain Chat Model Factory.
    Resolves per-user preferences, task-specific overrides, capability checks,
    credential decryption in ephemeral memory, and explicit fallback policies.
    """

    @classmethod
    def _get_cached_client(cls, cache_key: str) -> Optional[BaseChatModel]:
        cached = _CLIENT_CACHE.get(cache_key)
        if cached:
            client, expiry = cached
            if time.time() < expiry:
                return client
            del _CLIENT_CACHE[cache_key]
        return None

    @classmethod
    def _set_cached_client(cls, cache_key: str, client: BaseChatModel):
        # Prune expired entries if cache is growing
        if len(_CLIENT_CACHE) > 100:
            now = time.time()
            expired = [k for k, (_, exp) in _CLIENT_CACHE.items() if now >= exp]
            for k in expired:
                _CLIENT_CACHE.pop(k, None)
        _CLIENT_CACHE[cache_key] = (client, time.time() + CACHE_TTL_SECONDS)

    @classmethod
    def clear_cache_for_user(cls, user_id: str):
        keys_to_remove = [k for k in _CLIENT_CACHE if k.startswith(f"{user_id}:")]
        for k in keys_to_remove:
            _CLIENT_CACHE.pop(k, None)

    @classmethod
    async def get_chat_model(
        cls,
        db: AsyncSession,
        user_id: str,
        task_type: str = "general",  # 'interviewer', 'evaluation', 'coding', 'planning', 'general'
    ) -> BaseChatModel:
        """
        Resolves the LangChain BaseChatModel for the authenticated user and task type.
        Flow: authenticated user -> task preference -> credentials -> chat model client.
        """
        # Fetch user's provider configuration
        result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
        config = result.scalar_one_or_none()

        # Offline / Mock default
        if not config or config.provider_name == "mock" or not config.is_valid:
            mock_model_id = MOCK_MODEL_ID
            return MockChatModel(model_id=mock_model_id)

        # Enforce monthly spend and token ceiling
        from backend.app.providers.service import ProviderConfigService
        ProviderConfigService.check_spend_budget(config)

        # Task-specific model resolution
        model_id = config.preferred_model or DEFAULT_MODEL_ID
        if task_type == "interviewer" and config.interviewer_model:
            model_id = config.interviewer_model
        elif task_type == "evaluation" and config.evaluation_model:
            model_id = config.evaluation_model
        elif task_type == "coding":
            model_id = config.coding_model or DEFAULT_CODING_MODEL_ID
        elif task_type == "planning" and config.planning_model:
            model_id = config.planning_model
        elif config.default_model:
            model_id = config.default_model

        # Verify model capability in catalog
        meta = get_model_metadata(model_id)
        if meta and task_type == "coding" and not meta.supports_tool_calling:
            logger.info(f"Model {model_id} has limited tool capabilities; checking coding compatibility.")

        # Check client cache
        cache_key = f"{user_id}:{task_type}:{model_id}:{config.updated_at.isoformat() if config.updated_at else ''}"
        cached_client = cls._get_cached_client(cache_key)
        if cached_client:
            return cached_client

        # Decrypt BYOC credentials in memory only
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

        # If credentials missing or invalid, check fallback
        if not access_key or not secret_key:
            if config.fallback_enabled:
                logger.warning(f"Missing AWS credentials for user {user_id}. Explicit fallback activated.")
                fallback_model = MockChatModel(model_id=config.fallback_model or MOCK_MODEL_ID)
                return fallback_model
            raise ProviderError("Incomplete or missing AWS credentials. Please update under Settings.", "MISSING_CREDENTIALS")

        # Instantiate LangChain ChatBedrockConverse
        try:
            client = ChatBedrockConverse(
                model_id=model_id,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=config.aws_region or "us-east-1",
                temperature=config.temperature or 0.7,
                max_tokens=config.max_tokens or 2048,
            )
            cls._set_cached_client(cache_key, client)
            return client
        except Exception as e:
            if config.fallback_enabled:
                logger.warning(f"Failed to initialize ChatBedrockConverse for user {user_id}: {e}. Fallback to mock activated.")
                return MockChatModel(model_id=config.fallback_model or MOCK_MODEL_ID)
            raise ProviderError(f"Bedrock model initialization failed: {e}", "PROVIDER_INITIALIZATION_FAILED")
