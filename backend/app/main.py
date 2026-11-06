from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.core.logging import logger
from fastapi.exceptions import RequestValidationError
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.providers import router as providers_router
from backend.app.api.v1.resumes import router as resumes_router
from backend.app.api.v1.job_descriptions import router as job_descriptions_router
from backend.app.api.v1.interviews import router as interviews_router
from backend.app.api.v1.evaluations import router as evaluations_router
from backend.app.api.v1.plans import router as plans_router
from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.coding import router as coding_router
from backend.app.api.v1.learning_backlog import router as learning_backlog_router
from backend.app.api.v1.projects import router as projects_router
from backend.app.api.v1.audio import router as audio_router
from backend.app.api.v1.voice import router as voice_router
from backend.app.api.v1.comprehension import router as comprehension_router
from backend.app.api.v1.tracks import router as tracks_router
from backend.app.api.v1.enterprise import router as enterprise_router
from backend.app.api.v1.explanation_checks import router as explanation_checks_router
from backend.app.api.v1.telemetry import router as telemetry_router

def create_application() -> FastAPI:
    is_dev = settings.ENVIRONMENT.lower() in ("development", "test") or settings.DEBUG
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url="/api/v1/openapi.json" if is_dev else None,
        docs_url="/docs" if is_dev else None,
        redoc_url=None,
    )

    # Security Headers Middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        # A NUL in a path segment or query value reaches Postgres on read paths (writes are stripped
        # in session.before_flush) and 500s. No legitimate request carries one: reject up front.
        if "\x00" in request.url.path or b"%00" in request.scope.get("query_string", b"").lower():
            response = JSONResponse(status_code=400, content={"error": {
                "code": "INVALID_CHARACTERS", "message": "Request contains a NUL byte."}})
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        return response

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global custom exception handler
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        error: dict = {"code": exc.code, "message": exc.message}
        if getattr(exc, "details", None):
            error["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content={"error": error})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Don't echo the rejected input back (a 200k-char answer used to come back in the 422 body).
        errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()][:10]
        first = errors[0] if errors else {"loc": [], "msg": "Invalid request"}
        field = ".".join(str(p) for p in first["loc"] if p not in ("body", "query", "path"))
        message = f"{field}: {first['msg']}" if field else first["msg"]
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": message, "details": errors}})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Never leak internals; keep the response JSON so clients can show a sane message.
        logger.error(f"Unhandled error on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)[:300]}")
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR",
                                                               "message": "Something went wrong on our side. Try again."}})

    # Root health endpoint
    @app.get("/health", tags=["Health"])
    async def root_health():
        return {"status": "healthy", "project": settings.PROJECT_NAME}

    # Mount API routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(voice_router, prefix="/api/v1")
    app.include_router(comprehension_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")
    app.include_router(resumes_router, prefix="/api/v1")
    app.include_router(job_descriptions_router, prefix="/api/v1")
    app.include_router(interviews_router, prefix="/api/v1")
    app.include_router(evaluations_router, prefix="/api/v1")
    app.include_router(plans_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(coding_router, prefix="/api/v1")
    app.include_router(learning_backlog_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(audio_router, prefix="/api/v1")
    app.include_router(tracks_router, prefix="/api/v1")
    app.include_router(enterprise_router, prefix="/api/v1")
    app.include_router(explanation_checks_router, prefix="/api/v1")
    app.include_router(telemetry_router, prefix="/api/v1")
    # Also support direct path without /api/v1 prefix
    app.include_router(explanation_checks_router)
    app.include_router(telemetry_router)

    return app

app = create_application()
