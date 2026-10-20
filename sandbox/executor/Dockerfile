FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --no-cache-dir fastapi uvicorn[standard] docker pydantic

COPY sandbox/ /app/sandbox/

ENV PYTHONPATH=/app \
    PORT=8001

EXPOSE 8001

CMD ["uvicorn", "sandbox.executor.main:app", "--host", "0.0.0.0", "--port", "8001"]
