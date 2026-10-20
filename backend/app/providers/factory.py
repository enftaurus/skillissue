import json
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
from backend.app.core.logging import logger
from backend.app.database.models import ProviderConfig
from backend.app.providers.model_client_factory import ModelClientFactory

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
        task_type: str = "general"  # 'general', 'coding', 'evaluation', 'interviewer', 'planning'
    ) -> BaseProvider:
        from backend.app.providers.resolver import ModelResolver
        resolution = await ModelResolver.resolve(db, user_id, task_type=task_type)
        return cls.get_provider_by_type(
            provider_name=resolution.provider_name,
            model_id=resolution.model_id,
            aws_access_key=resolution.access_key,
            aws_secret_key=resolution.secret_key,
            aws_region=resolution.region,
        )
