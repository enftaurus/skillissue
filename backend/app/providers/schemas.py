from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from backend.app.providers.models_catalog import ModelMetadata

ALLOWED_AWS_REGIONS = {"us-east-1", "us-west-2", "ap-south-1", "ap-southeast-2"}

class ProviderConfigSave(BaseModel):
    provider_name: str = Field(default="bedrock", pattern="^(bedrock|mock)$")
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    preferred_model: str = "qwen.qwen3-32b-instruct-v1:0"
    monthly_token_budget: Optional[int] = Field(default=1_000_000, ge=10_000, le=50_000_000)
    monthly_cost_cents_budget: Optional[int] = Field(default=1000, ge=100, le=50000)  # $1 to $500

    @field_validator("aws_region")
    def validate_region(cls, v: str, info) -> str:
        provider = info.data.get("provider_name", "bedrock")
        if provider == "bedrock" and v not in ALLOWED_AWS_REGIONS:
            raise ValueError(f"Invalid AWS region '{v}'. Allowed regions: {sorted(list(ALLOWED_AWS_REGIONS))}")
        return v

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
    monthly_token_budget: int = 1_000_000
    monthly_tokens_used: int = 0
    monthly_cost_cents_budget: int = 1000
    monthly_cost_cents_used: int = 0

class TestCredentialsRequest(BaseModel):
    provider_name: str
    aws_region: str
    aws_access_key_id: str
    aws_secret_access_key: str
    preferred_model: str

    @field_validator("aws_region")
    def validate_region(cls, v: str, info) -> str:
        provider = info.data.get("provider_name", "bedrock")
        if provider == "bedrock" and v not in ALLOWED_AWS_REGIONS:
            raise ValueError(f"Invalid AWS region '{v}'. Allowed regions: {sorted(list(ALLOWED_AWS_REGIONS))}")
        return v

class TestCredentialsResponse(BaseModel):
    success: bool
    message: str
    model_id: str
    latency_ms: Optional[int] = None
