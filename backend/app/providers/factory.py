from typing import Any, Dict, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.providers.base import BaseProvider
from backend.app.providers.bedrock import AmazonBedrockProvider
from backend.app.providers.azure import AzureOpenAIProvider
from backend.app.providers.models_catalog import DEFAULT_MODEL_ID, DEFAULT_AZURE_MODEL_ID
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

# Explicit trusted provider class mapping (Production BYOC via Bedrock & Azure)
PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "bedrock": AmazonBedrockProvider,
    "azure": AzureOpenAIProvider,
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
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_api_version: Optional[str] = None,
        azure_deployment_name: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseProvider:
        if provider_name == "test_double":
            from backend.app.providers.mock_provider import MockProvider
            return MockProvider(model_id=model_id or DEFAULT_MODEL_ID)

        provider_cls = PROVIDER_REGISTRY.get(provider_name.lower())
        if not provider_cls:
            raise ProviderError(
                f"Unsupported provider: '{provider_name}'. Supported providers: 'azure', 'bedrock'.",
                "INVALID_PROVIDER"
            )

        if provider_name.lower() == "azure":
            if not azure_endpoint or not azure_api_key:
                raise ProviderError(
                    "Azure OpenAI credentials (Endpoint URL and API Key) are required.",
                    "MISSING_CREDENTIALS"
                )
            return AzureOpenAIProvider(
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
                api_version=azure_api_version or "2024-06-01",
                deployment_name=azure_deployment_name,
                model_id=model_id or DEFAULT_AZURE_MODEL_ID,
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
