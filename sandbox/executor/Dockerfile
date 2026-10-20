FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-21-jdk-headless \
    g++ \
    gcc \
    make \
    bubblewrap \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Setup isolated virtual environment for persistent executor API
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic httpx

COPY sandbox/ /app/sandbox/
COPY backend/app/core/logging.py /app/backend/app/core/logging.py
COPY backend/app/core/__init__.py /app/backend/app/core/__init__.py
COPY backend/app/__init__.py /app/backend/app/__init__.py
COPY backend/__init__.py /app/backend/__init__.py

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PORT=8001

EXPOSE 8001

CMD ["uvicorn", "sandbox.executor.main:app", "--host", "0.0.0.0", "--port", "8001"]
