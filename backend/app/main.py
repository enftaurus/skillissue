from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.errors import AppException
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
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    # Root health endpoint
    @app.get("/health", tags=["Health"])
    async def root_health():
        return {"status": "healthy", "project": settings.PROJECT_NAME}

    # Mount API routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")
    app.include_router(resumes_router, prefix="/api/v1")
    app.include_router(job_descriptions_router, prefix="/api/v1")
    app.include_router(interviews_router, prefix="/api/v1")
    app.include_router(evaluations_router, prefix="/api/v1")
    app.include_router(plans_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(coding_router, prefix="/api/v1")

    return app

app = create_application()
