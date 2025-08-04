"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kiremisu.api.library import router as library_router
from kiremisu.api.jobs import router as jobs_router, set_worker_runner
from kiremisu.api.chapters import router as chapters_router
from kiremisu.api.reader import router as reader_router
from kiremisu.api.series import router as series_router
from kiremisu.api.dashboard import router as dashboard_router
from kiremisu.core.config import settings
from kiremisu.core.error_handler import global_exception_handler
from kiremisu.core.rate_limiter import RateLimiter, RateLimitMiddleware
from kiremisu.database.connection import get_db_session_factory
from kiremisu.services.job_worker import JobWorkerRunner
from kiremisu.services.job_scheduler import SchedulerRunner

logger = logging.getLogger(__name__)

# Global instances for background services
_worker_runner: JobWorkerRunner = None
_scheduler_runner: SchedulerRunner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for background services."""
    global _worker_runner, _scheduler_runner

    # Initialize database session factory
    db_session_factory = get_db_session_factory()

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

        logger.info("Background services stopped")


app = FastAPI(
    title="KireMisu API",
    description="Self-hosted manga reader and library management system",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Add global exception handler for security
app.add_exception_handler(Exception, global_exception_handler)

# Rate limiting middleware (add before CORS)
rate_limiter = RateLimiter(
    requests_per_minute=120,  # Allow more requests for development
    requests_per_hour=3600,  # Generous hourly limit
    burst_limit=20,  # Allow reasonable bursts
)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

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
