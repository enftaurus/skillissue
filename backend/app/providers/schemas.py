from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.providers.models_catalog import ModelMetadata

class ProviderConfigSave(BaseModel):
    provider_name: str = Field(default="bedrock", pattern="^(bedrock|mock)$")
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    preferred_model: str = "qwen.qwen3-32b-instruct-v1:0"

class ProviderConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    provider_name: str
    aws_region: str
    aws_access_key_masked: str
    preferred_model: str
    is_valid: bool
    last_tested_at: Optional[datetime] = None
    total_tokens_used: int
    estimated_cost_usd: float

class TestCredentialsRequest(BaseModel):
    provider_name: str
    aws_region: str
    aws_access_key_id: str
    aws_secret_access_key: str
    preferred_model: str

class TestCredentialsResponse(BaseModel):
    success: bool
    message: str
    model_id: str
    latency_ms: Optional[int] = None
