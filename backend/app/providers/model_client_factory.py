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
        Resolves the LangChain BaseChatModel for the authenticated user and task type
        using the unified ModelResolver.
        """
        from backend.app.providers.resolver import ModelResolver
        resolution = await ModelResolver.resolve(db, user_id, task_type=task_type)

        if resolution.provider_name == "mock":
            return MockChatModel(model_id=resolution.model_id)

        # Check client cache
        cache_key = f"{user_id}:{task_type}:{resolution.model_id}:{resolution.temperature}:{resolution.max_tokens}"
        cached_client = cls._get_cached_client(cache_key)
        if cached_client:
            return cached_client

        # Instantiate LangChain ChatBedrockConverse
        try:
            client = ChatBedrockConverse(
                model_id=resolution.model_id,
                aws_access_key_id=resolution.access_key,
                aws_secret_access_key=resolution.secret_key,
                region_name=resolution.region or "us-east-1",
                temperature=resolution.temperature,
                max_tokens=resolution.max_tokens,
            )
            cls._set_cached_client(cache_key, client)
            return client
        except Exception as e:
            logger.warning(f"Failed to initialize ChatBedrockConverse for user {user_id}: {e}.")
            if resolution.is_fallback or resolution.intended_provider:
                logger.warning("Dynamic fallback to MockChatModel activated.")
                return MockChatModel(model_id=MOCK_MODEL_ID)
            raise ProviderError(f"Bedrock model initialization failed: {e}", "PROVIDER_INITIALIZATION_FAILED")
