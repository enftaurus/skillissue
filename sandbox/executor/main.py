import asyncio
import os
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, status, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from sandbox.executor.schemas import ExecuteRequest, ExecuteResponse
from sandbox.executor.persistent_manager import PersistentSandboxManager

EXECUTOR_SECRET = os.environ.get("EXECUTOR_SECRET", "dev-executor-secret-token-32chars-min!")
MAX_CONCURRENT_WORKERS = int(os.environ.get("SANDBOX_MAX_WORKERS", "4"))

class AdmissionController:
    """Threadsafe, race-free admission controller and backpressure gate."""
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self._active = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self._active >= self.max_concurrent:
                return False
            self._active += 1
            return True

    async def release(self):
        async with self._lock:
            self._active = max(0, self._active - 1)

manager = PersistentSandboxManager()
admission = AdmissionController(MAX_CONCURRENT_WORKERS)

ALLOWED_PROD_PROFILES = {"hardened_microvm", "firecracker", "kata", "gvisor", "dedicated_vm"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Security Boundary Validation: Fail closed in production if insecure profile is configured
    env = os.environ.get("ENVIRONMENT", "development").lower()
    profile = os.environ.get("SANDBOX_SECURITY_PROFILE", "local_docker_dev").lower()

    if env == "production" and profile not in ALLOWED_PROD_PROFILES:
        raise RuntimeError(
            f"FATAL: Insecure sandbox configuration in production! "
            f"SANDBOX_SECURITY_PROFILE is '{profile}'. "
            f"Running the code execution sandbox inside a standard Docker container with "
            f"CAP_SYS_ADMIN, unconfined seccomp, or unconfined AppArmor is strictly prohibited in production. "
            f"Production deployments must use an isolated microVM boundary "
            f"(allowed profiles: {', '.join(sorted(ALLOWED_PROD_PROFILES))})."
        )

    # Startup health check
    healthy, detail = manager.is_healthy()
    if not healthy and env == "production":
        raise RuntimeError(f"Sandbox executor unhealthy on startup: {detail}")
    yield

app = FastAPI(
    title="Skill Issue Persistent Sandbox Executor",
    version="2.0.0",
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
    env = os.environ.get("ENVIRONMENT", "development")
    profile = os.environ.get("SANDBOX_SECURITY_PROFILE", "local_docker_dev")
    return {
        "status": "healthy" if healthy else "degraded",
        "detail": detail,
        "runtime": manager.runtime,
        "environment": env,
        "security_profile": profile,
        "supported_languages": ["python", "java", "cpp"],
        "max_workers": MAX_CONCURRENT_WORKERS,
    }

@app.post(
    "/execute",
    response_model=ExecuteResponse,
    dependencies=[Depends(verify_executor_secret)],
)
async def execute(request: ExecuteRequest):
    admitted = await admission.try_acquire()
    if not admitted:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Sandbox executor queue is full. Try again shortly."},
            headers={"Retry-After": "2"},
        )

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, manager.execute_job, request)
        return result
    finally:
        await admission.release()

@app.post(
    "/execute/stream",
    dependencies=[Depends(verify_executor_secret)],
)
async def execute_stream(request: ExecuteRequest):
    admitted = await admission.try_acquire()
    if not admitted:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Sandbox executor queue is full."},
            headers={"Retry-After": "2"},
        )

    async def sse_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _worker():
            try:
                for event in manager.execute_job_streaming(request):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "message": str(e)})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _worker)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            await admission.release()

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
