"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from kiremisu.api.annotations import router as annotations_router
from kiremisu.api.auth import router as auth_router
from kiremisu.api.chapters import router as chapters_router
from kiremisu.api.dashboard import router as dashboard_router
from kiremisu.api.downloads import router as downloads_router
from kiremisu.api.file_operations import router as file_operations_router
from kiremisu.api.filesystem import router as filesystem_router
from kiremisu.api.jobs import router as jobs_router
from kiremisu.api.jobs import set_worker_runner
from kiremisu.api.library import router as library_router
from kiremisu.api.mangadx import cleanup_mangadx_services
from kiremisu.api.mangadx import router as mangadx_router
from kiremisu.api.metrics import router as metrics_router
from kiremisu.api.notifications import router as notifications_router
from kiremisu.api.push_notifications import router as push_router
from kiremisu.api.reader import router as reader_router
from kiremisu.api.series import router as series_router
from kiremisu.api.tags import router as tags_router
from kiremisu.api.watching import router as watching_router
from kiremisu.api.websocket import router as websocket_router
from kiremisu.core.config import settings
from kiremisu.core.error_handler import global_exception_handler
from kiremisu.core.rate_limiter import RateLimiter, RateLimitMiddleware
from kiremisu.database.connection import get_db_session_factory
from kiremisu.services.job_scheduler import SchedulerRunner
from kiremisu.services.job_worker import JobWorkerRunner

logger = logging.getLogger(__name__)

# Global instances for background services
_worker_runner: JobWorkerRunner = None
_scheduler_runner: SchedulerRunner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for background services and security initialization."""
    global _worker_runner, _scheduler_runner

    # Initialize database session factory
    db_session_factory = get_db_session_factory()

    # Initialize security and authentication
    try:
        logger.info("Initializing security and authentication...")

        # Initialize admin user if needed
        async with db_session_factory() as db:
            from kiremisu.core.auth import initialize_admin_user
            await initialize_admin_user(db)

        # Validate JWT configuration
        if not settings.secret_key or len(settings.secret_key) < 32:
            logger.error("JWT SECRET_KEY not properly configured")
            logger.error("Please set a secure SECRET_KEY environment variable (at least 32 characters)")
            from kiremisu.core.auth import generate_secure_secret_key
            logger.info(f"Generated secure key example: {generate_secure_secret_key()}")
            raise ValueError("JWT SECRET_KEY configuration required")

        logger.info("Security initialization completed")

    except Exception as e:
        logger.error(f"Security initialization failed: {e}")
        raise

    # Initialize and start background services
    try:
        logger.info("Starting background services...")

        # Initialize job worker
        _worker_runner = JobWorkerRunner(
            db_session_factory=db_session_factory, poll_interval_seconds=10, max_concurrent_jobs=3
        )

        # Initialize job scheduler
        _scheduler_runner = SchedulerRunner(
            db_session_factory=db_session_factory, check_interval_minutes=5
        )

        # Set worker runner for job API
        set_worker_runner(_worker_runner)

        # Start services
        await _worker_runner.start()
        await _scheduler_runner.start()

        logger.info("Background services started successfully")

        yield

    finally:
        # Cleanup background services
        logger.info("Stopping background services...")

        if _scheduler_runner:
            await _scheduler_runner.stop()

        if _worker_runner:
            await _worker_runner.stop()

        # Cleanup MangaDx services
        await cleanup_mangadx_services()

        logger.info("Background services stopped")


app = FastAPI(
    title="KireMisu API",
    description="Secure self-hosted manga reader and library management system",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    # Security headers
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
)

# Add global exception handler for security
app.add_exception_handler(Exception, global_exception_handler)

# Add slowapi rate limiter for downloads API
slowapi_limiter = Limiter(key_func=get_remote_address)
app.state.limiter = slowapi_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Rate limiting middleware (add before CORS)
rate_limiter = RateLimiter(
    requests_per_minute=settings.general_rate_limit_per_minute,
    requests_per_hour=settings.general_rate_limit_per_hour,
    burst_limit=settings.general_rate_limit_burst,
)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Don't cache sensitive endpoints
    if request.url.path.startswith("/api/auth") or "token" in request.url.path:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(library_router)
app.include_router(jobs_router)
app.include_router(chapters_router)
app.include_router(reader_router)
app.include_router(series_router)
app.include_router(dashboard_router)
app.include_router(annotations_router)
app.include_router(mangadx_router)
app.include_router(downloads_router)
app.include_router(tags_router)
app.include_router(file_operations_router)
app.include_router(filesystem_router)
app.include_router(notifications_router)
app.include_router(watching_router)
app.include_router(websocket_router)
app.include_router(metrics_router)
app.include_router(push_router)
app.include_router(auth_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "KireMisu API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "kiremisu.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )
