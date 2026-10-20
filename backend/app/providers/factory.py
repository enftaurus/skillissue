from typing import Dict, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.providers.base import BaseProvider
from backend.app.providers.bedrock import AmazonBedrockProvider
from backend.app.providers.models_catalog import DEFAULT_MODEL_ID
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

# Explicit trusted provider class mapping (Production BYOC via Amazon Bedrock)
PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "bedrock": AmazonBedrockProvider,
}

class ModelFactory:
    """
    Facade maintaining backward compatibility with existing services.
    Delegates all per-user resolution, bounded caching, and client lifecycle
    directly to ModelClientFactory.
    """

    @staticmethod
    def get_provider_by_type(
        provider_name: str,
        model_id: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        aws_region: Optional[str] = None,
        aws_session_token: Optional[str] = None,
    ) -> BaseProvider:
        if provider_name == "test_double":
            from backend.app.providers.mock_provider import MockProvider
            return MockProvider(model_id=model_id or DEFAULT_MODEL_ID)

        provider_cls = PROVIDER_REGISTRY.get(provider_name.lower())
        if not provider_cls:
            raise ProviderError(
                f"Unsupported provider: '{provider_name}'. Skill Issue uses real Amazon Bedrock BYOC inference.",
                "INVALID_PROVIDER"
            )

        if not aws_access_key or not aws_secret_key:
            raise ProviderError(
                "AWS credentials (Access Key ID and Secret Access Key) are required for Amazon Bedrock.",
                "MISSING_CREDENTIALS"
            )

        return AmazonBedrockProvider(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_region=aws_region or "us-east-1",
            aws_session_token=aws_session_token,
            model_id=model_id or DEFAULT_MODEL_ID,
        )

    @classmethod
    async def get_for_user(
        cls,
        db: AsyncSession,
        user_id: str,
        task_type: str = "general"
    ) -> BaseProvider:
        """
        Consolidated provider-resolution path.
        Delegates directly to ModelClientFactory to leverage the bounded client cache,
        configuration versioning, and zero-decryption cache hits.
        """
        from backend.app.providers.model_client_factory import ModelClientFactory
        return await ModelClientFactory.get_provider(db, user_id, task_type=task_type)
