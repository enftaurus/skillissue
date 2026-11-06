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
    /app/venv/bin/pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic httpx "pytest==8.4.2"

COPY sandbox/ /app/sandbox/
RUN mkdir -p /app/backend/app/core && \
    touch /app/backend/__init__.py /app/backend/app/__init__.py /app/backend/app/core/__init__.py
COPY backend/app/core/logging.py /app/backend/app/core/logging.py
# Hardened multi-file project runner (single source of truth with the API; ADR 0023)
RUN mkdir -p /app/backend/app/projects && touch /app/backend/app/projects/__init__.py
COPY backend/app/core/errors.py /app/backend/app/core/
COPY backend/app/projects/sandbox.py /app/backend/app/projects/sandbox.py

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PORT=8001

# Run as an unprivileged user. Under root, bubblewrap's user namespace maps the job back to kernel uid 0, which the
# kernel exempts from RLIMIT_NPROC, so `ulimit -u` would not stop a fork bomb. As uid 10001 the limit holds (ADR 0026).
RUN useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin executor
USER 10001:10001

EXPOSE 8001

CMD ["uvicorn", "sandbox.executor.main:app", "--host", "0.0.0.0", "--port", "8001"]
