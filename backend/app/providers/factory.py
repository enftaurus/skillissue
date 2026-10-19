from typing import Dict, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.providers.base import BaseProvider
from backend.app.providers.bedrock import AmazonBedrockProvider
from backend.app.providers.mock_provider import MockProvider
from backend.app.providers.models_catalog import (
    DEFAULT_MODEL_ID, DEFAULT_CODING_MODEL_ID, MOCK_MODEL_ID, get_model_metadata
)
from backend.app.core.security import decrypt_secret
from backend.app.core.errors import ProviderError
from backend.app.database.models import ProviderConfig

# Explicit trusted provider class mapping (No dynamic imports from arbitrary strings)
PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "bedrock": AmazonBedrockProvider,
    "mock": MockProvider,
}

class ModelFactory:
    @staticmethod
    def get_provider_by_type(
        provider_name: str,
        model_id: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        aws_region: Optional[str] = None,
    ) -> BaseProvider:
        provider_cls = PROVIDER_REGISTRY.get(provider_name.lower())
        if not provider_cls:
            raise ProviderError(f"Unsupported provider: '{provider_name}'. Must be one of: {list(PROVIDER_REGISTRY.keys())}", "INVALID_PROVIDER")

        if provider_cls == AmazonBedrockProvider:
            if not aws_access_key or not aws_secret_key:
                raise ProviderError("AWS credentials are required for Amazon Bedrock.", "MISSING_CREDENTIALS")
            return AmazonBedrockProvider(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                aws_region=aws_region or "us-east-1",
                model_id=model_id or DEFAULT_MODEL_ID,
            )
        else:
            return MockProvider(model_id=model_id or MOCK_MODEL_ID)

    @classmethod
    async def get_for_user(
        cls,
        db: AsyncSession,
        user_id: str,
        task_type: str = "general"  # 'general', 'coding', 'evaluation'
    ) -> BaseProvider:
        result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
        config = result.scalar_one_or_none()

        # If user has no config or is in mock mode, use MockProvider
        if not config or config.provider_name == "mock" or not config.is_valid:
            mock_model = MOCK_MODEL_ID
            return MockProvider(model_id=mock_model)

        # Select model based on task routing or preferred setting
        model_id = config.preferred_model or DEFAULT_MODEL_ID
        if task_type == "coding":
            # If user configured a Bedrock provider, check if coding specialist can be used
            model_id = DEFAULT_CODING_MODEL_ID

        # Decrypt secret key in ephemeral memory only
        secret_key = decrypt_secret(config.aws_secret_key_enc)
        # Re-derive access key prefix if needed, or pass the stored masked / full
        # Wait: we need the full access key to invoke AWS! Let's ensure access key is stored securely or encrypted.
        # To be completely safe and avoid storing access key in plaintext, we store encrypted or pass through.
        return cls.get_provider_by_type(
            provider_name=config.provider_name,
            model_id=model_id,
            aws_access_key=decrypt_secret(config.aws_access_key_masked) if config.aws_access_key_masked.startswith("gAAAA") else config.aws_access_key_masked,
            aws_secret_key=secret_key,
            aws_region=config.aws_region,
        )
