import json
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    PROJECT_NAME: str = "Skill Issue"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "dev-insecure-secret-key-at-least-32-chars-long!"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Session refresh lifetime
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

    # Sandbox & Execution
    DEFAULT_PROVIDER: str = "mock"
    SANDBOX_EXECUTION_MODE: str = "docker"  # 'docker', 'mock', 'disabled'
    SANDBOX_RUNTIME: str = "runc"           # 'runc', 'runsc', 'kata'
    SANDBOX_EXECUTOR_URL: str = "http://127.0.0.1:8001"
    SANDBOX_EXECUTOR_SECRET: str = "skillissue-executor-internal-secret-2026"

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

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "Settings":
        env = self.ENVIRONMENT.lower()
        if env in ("development", "test") and not self.DEBUG:
            # Enable debug automatically only in development if not explicitly configured
            pass

        if env == "production":
            # 1. Enforce strong secrets
            if not self.SECRET_KEY or len(self.SECRET_KEY) < 32 or "insecure" in self.SECRET_KEY.lower() or "dev-" in self.SECRET_KEY.lower():
                raise ValueError("Insecure or default SECRET_KEY rejected in production. Must be at least 32 cryptographically secure characters.")
            
            if not self.ENCRYPTION_KEY or "gH7_mK9" in self.ENCRYPTION_KEY:
                raise ValueError("Insecure default ENCRYPTION_KEY rejected in production. Must provide a secure production key.")

            # 2. Reject SQLite or in-memory DB
            if "sqlite" in self.DATABASE_URL.lower():
                raise ValueError("SQLite is forbidden in production. PostgreSQL 16+ is required.")

            # 3. Reject non-docker sandbox execution
            if self.SANDBOX_EXECUTION_MODE != "docker":
                raise ValueError(
                    f"SANDBOX_EXECUTION_MODE must be 'docker' in production. Got '{self.SANDBOX_EXECUTION_MODE}'. "
                    "Insecure host subprocesses are forbidden in production."
                )

        return self

settings = Settings()
