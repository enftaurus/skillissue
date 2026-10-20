FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

COPY backend/pyproject.toml /app/backend/
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    pydantic-settings \
    "sqlalchemy[asyncio]>=2.0" \
    asyncpg \
    psycopg2-binary \
    alembic \
    boto3 \
    botocore \
    cryptography \
    bcrypt \
    python-jose \
    pypdf \
    httpx \
    python-multipart

COPY backend /app/backend
COPY sandbox /app/sandbox
COPY scripts /app/scripts

RUN chown -R appuser:appgroup /app

USER 1000:1000
ENV PYTHONPATH=/app \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
