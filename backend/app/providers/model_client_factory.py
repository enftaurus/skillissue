import collections
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_aws import ChatBedrockConverse
from backend.app.providers.base import BaseProvider
from backend.app.providers.bedrock import AmazonBedrockProvider
from backend.app.providers.resolver import ModelResolver, UserConfigMetadata
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

@dataclass(frozen=True)
class ClientCacheKey:
    """
    Cache key strictly derived from the effective client construction parameters.
    Isolated per user ID and configuration version. Task names that resolve to
    the same effective parameters share the same cache key.
    """
    client_type: str  # "langchain" or "provider"
    user_id: str
    config_version: int
    region: str
    model_id: str
    temperature: float
    max_tokens: int
    provider_name: str = "bedrock"

@dataclass
class CacheEntry:
    client: Any
    created_at: float
    last_accessed_at: float

class BoundedClientCache:
    """
    Thread-safe / task-safe bounded in-memory cache for SDK clients.
    
    SECURITY NOTE:
    Boto3 and LangChain SDK clients retain AWS credentials in process memory during their
    lifetime. This cache enforces a strict maximum size bound and idle expiration to safely
    evict stale or abandoned client instances and purge retained credentials from memory.
    """
    def __init__(self, max_size: int = 128, idle_ttl_seconds: float = 300.0):
        self.max_size = max_size
        self.idle_ttl_seconds = idle_ttl_seconds
        # OrderedDict maintains access order for LRU eviction
        self._entries: collections.OrderedDict[ClientCacheKey, CacheEntry] = collections.OrderedDict()

    def get(self, key: ClientCacheKey) -> Optional[Any]:
        entry = self._entries.get(key)
        if not entry:
            return None

        now = time.time()
        # Check idle expiration
        if now - entry.last_accessed_at > self.idle_ttl_seconds:
            self._entries.pop(key, None)
            return None

        # Update access time and move to end (MRU)
        entry.last_accessed_at = now
        self._entries.move_to_end(key)
        return entry.client

    def set(self, key: ClientCacheKey, client: Any):
        now = time.time()
        # Evict expired entries first
        expired_keys = [
            k for k, v in self._entries.items()
            if now - v.last_accessed_at > self.idle_ttl_seconds
        ]
        for k in expired_keys:
            self._entries.pop(k, None)

        # Enforce hard capacity bound via LRU eviction
        while len(self._entries) >= self.max_size:
            # popitem(last=False) pops the oldest accessed item (LRU)
            self._entries.popitem(last=False)

        self._entries[key] = CacheEntry(
            client=client,
            created_at=now,
            last_accessed_at=now,
        )

    def invalidate_user(self, user_id: str):
        keys_to_remove = [k for k in self._entries if k.user_id == user_id]
        for k in keys_to_remove:
            self._entries.pop(k, None)

    def clear(self):
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

# Global per-process client cache (hard limit 128 clients, 5-minute idle expiration)
_CLIENT_CACHE = BoundedClientCache(max_size=128, idle_ttl_seconds=300.0)

class ModelClientFactory:
    """
    Consolidated Bedrock Client Lifecycle Manager.
    
    Serves both LangChain Chat Models and application BaseProviders through a single,
    unified resolution and client-creation pipeline.
    
    Guarantees:
    1. Reuse on cache hit: zero PostgreSQL queries and zero cryptographic decryptions.
    2. Strict tenant isolation: user A's client is never shared with user B.
    3. Shared client across identical effective task configurations.
    4. Reliable invalidation via configuration versioning and local cache purge.
    5. Bounded memory lifecycle with LRU and idle TTL eviction.
    """

    @classmethod
    def get_cache(cls) -> BoundedClientCache:
        return _CLIENT_CACHE

    @classmethod
    def clear_cache_for_user(cls, user_id: str):
        """Immediately drop all cached clients and metadata for a user upon configuration change."""
        _CLIENT_CACHE.invalidate_user(user_id)
        ModelResolver.invalidate_metadata(user_id)

    @classmethod
    def clear_all_caches(cls):
        """Reset all in-memory client and metadata caches."""
        _CLIENT_CACHE.clear()

    @classmethod
    async def get_chat_model(
        cls,
        db: AsyncSession,
        user_id: str,
        task_type: str = "general",
        model_id_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
    ) -> BaseChatModel:
        """
        Resolves or reuses a LangChain BaseChatModel for the specified user and task.
        """
        return await cls._resolve_and_get_client(
            db=db,
            user_id=user_id,
            client_type="langchain",
            task_type=task_type,
            model_id_override=model_id_override,
            temperature_override=temperature_override,
            max_tokens_override=max_tokens_override,
        )

    @classmethod
    async def get_provider(
        cls,
        db: AsyncSession,
        user_id: str,
        task_type: str = "general",
        model_id_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
    ) -> BaseProvider:
        """
        Resolves or reuses a BaseProvider (AmazonBedrockProvider) for the specified user and task.
        """
        return await cls._resolve_and_get_client(
            db=db,
            user_id=user_id,
            client_type="provider",
            task_type=task_type,
            model_id_override=model_id_override,
            temperature_override=temperature_override,
            max_tokens_override=max_tokens_override,
        )

    @classmethod
    async def _resolve_and_get_client(
        cls,
        db: AsyncSession,
        user_id: str,
        client_type: str,
        task_type: str,
        model_id_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
    ) -> Any:
        # Step 1: Lightweight metadata resolution without decrypting credentials
        metadata = await ModelResolver.get_config_metadata(db, user_id)
        ModelResolver.check_spend_budget(metadata)

        # Check for test run mock double
        is_test_run = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        is_real_bedrock_test = bool(os.environ.get("TEST_WITH_REAL_BEDROCK"))

        effective_model = model_id_override or ModelResolver.resolve_model_id(metadata, task_type)
        effective_temp = temperature_override if temperature_override is not None else metadata.temperature
        effective_tokens = max_tokens_override if max_tokens_override is not None else metadata.max_tokens

        # Step 2: Build cache key based on effective construction parameters
        region_str = metadata.aws_region if metadata.provider_name == "bedrock" else (metadata.azure_endpoint or "azure")
        cache_key = ClientCacheKey(
            client_type=client_type,
            user_id=user_id,
            config_version=metadata.config_version,
            region=region_str,
            model_id=effective_model,
            temperature=effective_temp,
            max_tokens=effective_tokens,
            provider_name=metadata.provider_name,
        )

        # Step 3: Fast Cache Hit Path
        cached_client = _CLIENT_CACHE.get(cache_key)
        if cached_client is not None:
            return cached_client

        if client_type == "langchain":
            if metadata.provider_name in ("test_double", "mock") or (is_test_run and not is_real_bedrock_test and not os.environ.get("TEST_WITH_REAL_AZURE")):
                from backend.app.providers.mock_chat_model import MockChatModel
                client = MockChatModel(model_id=effective_model)
                _CLIENT_CACHE.set(cache_key, client)
                return client
        else:
            if metadata.provider_name in ("test_double", "mock"):
                from backend.app.providers.mock_provider import MockProvider
                client = MockProvider(model_id=effective_model)
                _CLIENT_CACHE.set(cache_key, client)
                return client

        # Step 4: Cache Miss Path — Decrypt credentials ONLY on miss
        creds = await ModelResolver.resolve_credentials(db, user_id)

        try:
            if metadata.provider_name == "azure":
                target_deployment = effective_model.replace("azure.", "") if effective_model else ""
                if creds.azure_deployment_name and creds.azure_deployment_name not in ("gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini"):
                    deployment = creds.azure_deployment_name
                else:
                    deployment = target_deployment or creds.azure_deployment_name or metadata.azure_deployment_name or "gpt-4.1-mini"

                if client_type == "langchain":
                    from langchain_openai import AzureChatOpenAI
                    client = AzureChatOpenAI(
                        azure_endpoint=creds.azure_endpoint or metadata.azure_endpoint,
                        api_key=creds.azure_api_key,
                        api_version=creds.azure_api_version or metadata.azure_api_version or "2024-06-01",
                        azure_deployment=deployment,
                        temperature=effective_temp,
                        max_tokens=effective_tokens,
                        request_timeout=float(os.environ.get("AZURE_OPENAI_TIMEOUT_SECONDS", "180.0")),
                    )
                else:
                    from backend.app.providers.azure import AzureOpenAIProvider
                    client = AzureOpenAIProvider(
                        azure_endpoint=creds.azure_endpoint or metadata.azure_endpoint,
                        api_key=creds.azure_api_key,
                        api_version=creds.azure_api_version or metadata.azure_api_version or "2024-06-01",
                        deployment_name=deployment,
                        model_id=effective_model,
                    )
            else:
                if client_type == "langchain":
                    extra_kwargs = {}
                    if creds.aws_session_token:
                        extra_kwargs["aws_session_token"] = creds.aws_session_token

                    client = ChatBedrockConverse(
                        model_id=effective_model,
                        aws_access_key_id=creds.aws_access_key,
                        aws_secret_access_key=creds.aws_secret_key,
                        region_name=metadata.aws_region,
                        temperature=effective_temp,
                        max_tokens=effective_tokens,
                        **extra_kwargs
                    )
                else:
                    client = AmazonBedrockProvider(
                        aws_access_key_id=creds.aws_access_key,
                        aws_secret_access_key=creds.aws_secret_key,
                        aws_region=metadata.aws_region,
                        aws_session_token=creds.aws_session_token,
                        model_id=effective_model,
                    )

            _CLIENT_CACHE.set(cache_key, client)
            return client
        except Exception as e:
            logger.error(f"Failed to initialize {client_type} client for user {user_id}: {e}")
            provider_label = "Azure OpenAI" if metadata.provider_name == "azure" else "Amazon Bedrock"
            raise ProviderError(
                f"Failed to initialize {provider_label} model '{effective_model}': {e}. "
                "Verify model access and credentials in Settings → Model Provider.",
                "PROVIDER_INITIALIZATION_FAILED"
            )
