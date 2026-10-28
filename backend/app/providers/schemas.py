from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from backend.app.providers.models_catalog import ModelMetadata, DEFAULT_MODEL_ID

ALLOWED_AWS_REGIONS = {"us-east-1", "us-west-2", "ap-south-1", "ap-southeast-2", "eu-central-1"}

class ProviderConfigSave(BaseModel):
    provider_name: str = Field(default="bedrock", pattern="^bedrock$")
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    preferred_model: str = DEFAULT_MODEL_ID
    default_model: Optional[str] = DEFAULT_MODEL_ID
    interviewer_model: Optional[str] = None
    evaluation_model: Optional[str] = None
    coding_model: Optional[str] = None
    planning_model: Optional[str] = None
    fallback_enabled: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    monthly_token_budget: Optional[int] = Field(default=1_000_000, ge=10_000, le=50_000_000)
    monthly_cost_cents_budget: Optional[int] = Field(default=1000, ge=100, le=50000)  # $1 to $500

    @field_validator("aws_region")
    def validate_region(cls, v: str) -> str:
        if v not in ALLOWED_AWS_REGIONS:
            raise ValueError(f"Invalid AWS region '{v}'. Allowed regions: {sorted(list(ALLOWED_AWS_REGIONS))}")
        return v

class ProviderConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    provider_name: str
    aws_region: str
    aws_access_key_masked: str
    preferred_model: str
    default_model: Optional[str] = None
    interviewer_model: Optional[str] = None
    evaluation_model: Optional[str] = None
    coding_model: Optional[str] = None
    planning_model: Optional[str] = None
    fallback_enabled: bool = False
    temperature: float = 0.7
    max_tokens: int = 2048
    is_valid: bool
    last_tested_at: Optional[datetime] = None
    total_tokens_used: int
    estimated_cost_usd: float
    monthly_token_budget: int = 1_000_000
    monthly_tokens_used: int = 0
    monthly_cost_cents_budget: int = 1000
    monthly_cost_cents_used: int = 0
    config_version: int = 1

class TestCredentialsRequest(BaseModel):
    provider_name: str = "bedrock"
    aws_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: Optional[str] = None
    preferred_model: str = DEFAULT_MODEL_ID

    @field_validator("aws_region")
    def validate_region(cls, v: str) -> str:
        if v not in ALLOWED_AWS_REGIONS:
            raise ValueError(f"Invalid AWS region '{v}'. Allowed regions: {sorted(list(ALLOWED_AWS_REGIONS))}")
        return v

class TestCredentialsResponse(BaseModel):
    success: bool
    message: str
    model_id: str
    latency_ms: Optional[int] = None

class IamPolicyResponse(BaseModel):
    policy_json: str
    policy_document: Optional[str] = None
    model_id: str
    region: str
    actions_explained: Dict[str, str] = {}
    resources_explained: List[str] = []
    setup_notes: List[str] = []

    def __init__(self, **data):
        if "policy_json" in data and not data.get("policy_document"):
            data["policy_document"] = data["policy_json"]
        elif "policy_document" in data and not data.get("policy_json"):
            data["policy_json"] = data["policy_document"]
        super().__init__(**data)
