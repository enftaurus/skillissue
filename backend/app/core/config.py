from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "Skill Issue"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "dev-insecure-secret-key-at-least-32-chars-long!"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for convenience in dev
    ENCRYPTION_KEY: str = "gH7_mK9_sP2_wL4_xR8_yT1_bV3_nQ6_zC5_dF0_jA="

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/skillissue"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5433/skillissue"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("SECRET_KEY")
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development").lower()
        if env == "production":
            if not v or len(v) < 32 or "insecure" in v.lower() or "dev-" in v.lower():
                raise ValueError("Insecure or default SECRET_KEY rejected in production. Must be at least 32 cryptographically secure characters.")
        return v

    @field_validator("ENCRYPTION_KEY")
    def validate_encryption_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development").lower()
        if env == "production":
            if not v or "gH7_mK9" in v:
                raise ValueError("Insecure default ENCRYPTION_KEY rejected in production. Must provide a secure production key.")
        return v

    # Model defaults
    DEFAULT_PROVIDER: str = "mock"
    SANDBOX_EXECUTION_MODE: str = "isolated_process"

settings = Settings()
