"""Job management API endpoints."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    JobResponse,
    JobListResponse,
    JobScheduleRequest,
    JobScheduleResponse,
    JobStatsResponse,
    WorkerStatusResponse,
)
from kiremisu.services.job_scheduler import JobScheduler
from kiremisu.services.job_worker import JobWorkerRunner

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobWorkerDependency:
    """Dependency provider for job worker runner."""

    def __init__(self):
        self._worker_runner: Optional[JobWorkerRunner] = None

    def set_worker_runner(self, worker_runner: JobWorkerRunner):
        """Set the worker runner instance."""
        self._worker_runner = worker_runner

    def get_worker_runner(self) -> Optional[JobWorkerRunner]:
        """Get the worker runner instance."""
        return self._worker_runner


# Global dependency instance
job_worker_dependency = JobWorkerDependency()


def get_worker_runner() -> Optional[JobWorkerRunner]:
    """Dependency function to get worker runner."""
    return job_worker_dependency.get_worker_runner()


def set_worker_runner(worker_runner: JobWorkerRunner):
    """Set the global worker runner instance."""
    job_worker_dependency.set_worker_runner(worker_runner)


@router.get("/status", response_model=JobStatsResponse)
async def get_job_status(
    db: AsyncSession = Depends(get_db),
    worker_runner: Optional[JobWorkerRunner] = Depends(get_worker_runner),
) -> JobStatsResponse:
    """Get job queue status and statistics."""
    # Get queue statistics
    queue_stats = await JobScheduler.get_queue_stats(db)

    # Get worker status
    worker_status = None
    if worker_runner:
        worker_status = await worker_runner.get_worker_status()

    return JobStatsResponse(
        queue_stats=queue_stats, worker_status=worker_status, timestamp=datetime.utcnow()
    )


@router.get("/recent", response_model=JobListResponse)
async def get_recent_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of jobs to return"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """Get recent jobs with optional filtering."""
    jobs = await JobScheduler.get_recent_jobs(db, job_type=job_type, limit=limit)

    return JobListResponse(
        jobs=[JobResponse.from_model(job) for job in jobs],
        total=len(jobs),
        job_type_filter=job_type,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)) -> JobResponse:
    """Get details of a specific job."""
    job = await JobScheduler.get_job_status(db, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}"
        )

    return JobResponse.from_model(job)


@router.post("/schedule", response_model=JobScheduleResponse)
async def schedule_jobs(
    schedule_request: JobScheduleRequest, db: AsyncSession = Depends(get_db)
) -> JobScheduleResponse:
    """Schedule jobs based on the request type."""
    try:
        if schedule_request.job_type == "library_scan":
            if schedule_request.library_path_id:
                # Schedule manual scan for specific path
                job_id = await JobScheduler.schedule_manual_scan(
                    db,
                    library_path_id=schedule_request.library_path_id,
                    priority=schedule_request.priority,
                )

                return JobScheduleResponse(
                    status="scheduled",
                    message=f"Manual library scan scheduled for path {schedule_request.library_path_id}",
                    job_id=job_id,
                    scheduled_count=1,
                )
            else:
                # Schedule manual scan for all paths
                job_id = await JobScheduler.schedule_manual_scan(
                    db, priority=schedule_request.priority
                )

                return JobScheduleResponse(
                    status="scheduled",
                    message="Manual library scan scheduled for all paths",
                    job_id=job_id,
                    scheduled_count=1,
                )

        elif schedule_request.job_type == "auto_schedule":
            # Schedule automatic scans based on library path intervals
            result = await JobScheduler.schedule_library_scans(db)

            return JobScheduleResponse(
                status="completed",
                message=f"Scheduled {result['scheduled']} automatic scans, skipped {result['skipped']} paths",
                scheduled_count=result["scheduled"],
                skipped_count=result["skipped"],
                total_paths=result["total_paths"],
            )

        elif schedule_request.job_type == "download":
            # Schedule download job
            if not schedule_request.manga_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Download jobs require 'manga_id' field",
                )

            job_id = await JobScheduler.schedule_download(
                db,
                manga_id=schedule_request.manga_id,
                download_type=schedule_request.download_type,
                series_id=schedule_request.series_id,
                priority=schedule_request.priority,
            )

            return JobScheduleResponse(
                status="scheduled",
                message=f"Download job scheduled for {schedule_request.download_type} manga: {schedule_request.manga_id}",
                job_id=job_id,
                scheduled_count=1,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown job type: {schedule_request.job_type}",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        # Log the full exception for debugging but don't expose internals
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Job scheduling failed: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while scheduling job",
        )


@router.post("/cleanup", response_model=Dict[str, int])
async def cleanup_old_jobs(
    older_than_days: int = Query(
        30, ge=1, le=365, description="Remove jobs completed more than this many days ago"
    ),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, int]:
    """Clean up old completed jobs."""
    try:
        deleted_count = await JobScheduler.cleanup_old_jobs(db, older_than_days)

        return {"deleted": deleted_count, "older_than_days": older_than_days}

    except Exception as e:
        # Log the full exception for debugging but don't expose internals
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Job cleanup failed: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred during job cleanup",
        )


@router.get("/worker/status", response_model=WorkerStatusResponse)
async def get_worker_status(
    worker_runner: Optional[JobWorkerRunner] = Depends(get_worker_runner),
) -> WorkerStatusResponse:
    """Get current worker status."""
    if not worker_runner:
        return WorkerStatusResponse(
            running=False,
            active_jobs=0,
            max_concurrent_jobs=0,
            poll_interval_seconds=0,
            message="Worker not initialized",
        )

    status = await worker_runner.get_worker_status()
    return WorkerStatusResponse(**status)
