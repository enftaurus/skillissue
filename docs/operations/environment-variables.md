# Environment Variables Reference — Skill Issue

All environment configuration options are documented below. For local development, copy `.env.example` to `.env`.

| Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `test`, `production`). |
| `DEBUG` | `true` | Enables FastAPI debug logging and OpenAPI interactive docs. |
| `SECRET_KEY` | `dev-secret-key-change-in-production-1234567890` | JWT signing key. |
| `ENCRYPTION_KEY` | `gH7_mK9_sP2_wL4_xR8_yT1_bV3_nQ6_zC5_dF0_jA=` | Fernet 32-byte urlsafe base64 key for encrypting provider credentials. |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/skillissue` | Async connection string for FastAPI application. |
| `DATABASE_URL_SYNC` | `postgresql://postgres:postgres@localhost:5433/skillissue` | Synchronous connection string for Alembic migrations. |
| `POSTGRES_PORT` | `5433` | Host port mapped to PostgreSQL container port 5432. Set to 5433 to avoid collision. |
| `POSTGRES_USER` | `postgres` | Database username. |
| `POSTGRES_PASSWORD` | `postgres` | Database password. |
| `POSTGRES_DB` | `skillissue` | Database name. |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | Allowed CORS origins for the frontend. |
| `SANDBOX_EXECUTION_MODE` | `isolated_process` | Sandbox isolation mode: `docker` or `isolated_process` (for dev systems without Docker socket sharing). |
| `DEFAULT_PROVIDER` | `mock` | Default LLM provider for accounts without saved BYOC credentials (`mock` or `bedrock`). |
