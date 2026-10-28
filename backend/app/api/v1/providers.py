from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.providers.models_catalog import get_recommended_lineup, ModelMetadata, DEFAULT_MODEL_ID
from backend.app.providers.schemas import (
    ProviderConfigSave, ProviderConfigResponse, TestCredentialsRequest, TestCredentialsResponse,
    IamPolicyResponse
)
from backend.app.providers.service import ProviderConfigService

router = APIRouter(prefix="/providers", tags=["Providers & BYOC"])

@router.get("/config", response_model=ProviderConfigResponse)
async def get_my_provider_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    config = await ProviderConfigService.get_config(db, current_user.id)
    return config

@router.put("/config", response_model=ProviderConfigResponse)
async def update_my_provider_config(
    data: ProviderConfigSave,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    config = await ProviderConfigService.save_config(db, current_user.id, data)
    return config

@router.post("/test", response_model=TestCredentialsResponse)
async def test_provider_credentials(
    data: TestCredentialsRequest,
    current_user: User = Depends(get_current_active_user),
):
    result = await ProviderConfigService.test_credentials(data)
    return result

@router.delete("/credentials", response_model=ProviderConfigResponse)
async def delete_saved_credentials(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    config = await ProviderConfigService.delete_credentials(db, current_user.id)
    return config

@router.get("/models", response_model=List[ModelMetadata])
async def list_available_models():
    return get_recommended_lineup()

@router.get("/iam-policy", response_model=IamPolicyResponse)
async def get_iam_policy(
    model_id: str = Query(default=DEFAULT_MODEL_ID, description="Target Bedrock model ID"),
    region: str = Query(default="us-east-1", description="AWS Region"),
    models: Optional[str] = Query(default=None, description="Alias for model_id"),
    regions: Optional[str] = Query(default=None, description="Alias for region"),
):
    effective_model = models or model_id
    effective_region = regions or region
    return ProviderConfigService.get_iam_policy_doc(model_id=effective_model, region=effective_region)
