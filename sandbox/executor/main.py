import asyncio
import os
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, status, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from sandbox.executor.schemas import ExecuteRequest, ExecuteResponse
from sandbox.executor.docker_manager import DockerSandboxManager
from sandbox.executor.reaper import SandboxReaper

EXECUTOR_SECRET = os.environ.get("EXECUTOR_SECRET", "dev-executor-secret-token-32chars-min!")
MAX_CONCURRENT_WORKERS = int(os.environ.get("SANDBOX_MAX_WORKERS", "4"))

manager = DockerSandboxManager()
reaper = SandboxReaper()
semaphore = asyncio.Semaphore(MAX_CONCURRENT_WORKERS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start background reaper
    reaper.start()
    yield
    # Shutdown: stop reaper
    reaper.stop()

app = FastAPI(
    title="Skill Issue Sandbox Executor",
    version="1.0.0",
    docs_url=None if os.environ.get("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)

async def verify_executor_secret(x_executor_secret: str = Header(None)):
    if not x_executor_secret or x_executor_secret != EXECUTOR_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing executor authentication secret",
        )

@app.get("/health")
async def health():
    healthy, detail = manager.is_healthy()
    return {
        "status": "healthy" if healthy else "degraded",
        "detail": detail,
        "runtime": manager.runtime,
        "supported_languages": ["python", "java", "cpp"],
        "max_workers": MAX_CONCURRENT_WORKERS,
    }

@app.post(
    "/execute",
    response_model=ExecuteResponse,
    dependencies=[Depends(verify_executor_secret)],
)
async def execute(request: ExecuteRequest):
    # Concurrency control: if saturated, return 429
    if semaphore.locked() and semaphore._value == 0:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Sandbox executor queue is full. Try again shortly."},
            headers={"Retry-After": "2"},
        )

    async with semaphore:
        # Run blocking Docker operations in threadpool so event loop remains free
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, manager.execute_job, request)
        return result

@app.post(
    "/execute/stream",
    dependencies=[Depends(verify_executor_secret)],
)
async def execute_stream(request: ExecuteRequest):
    if semaphore.locked() and semaphore._value == 0:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Sandbox executor queue is full."},
            headers={"Retry-After": "2"},
        )

    async def sse_generator() -> AsyncGenerator[str, None]:
        async with semaphore:
            loop = asyncio.get_running_loop()
            yield f"data: {json.dumps({'event': 'queued', 'job_id': request.job_id})}\n\n"
            
            # Execute
            result = await loop.run_in_executor(None, manager.execute_job, request)
            
            # Stream per-test result
            for tr in result.test_results:
                yield f"data: {json.dumps({'event': 'test_result', 'result': tr.model_dump()})}\n\n"

            yield f"data: {json.dumps({'event': 'done', 'response': result.model_dump()})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
