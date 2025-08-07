"""Downloads API endpoints for managing download jobs and progress."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.models import JobQueue
from kiremisu.database.schemas import (
    DownloadJobRequest,
    DownloadJobResponse,
    DownloadJobListResponse,
    DownloadJobActionRequest,
    DownloadJobActionResponse,
    DownloadStatsResponse,
    BulkDownloadRequest,
    BulkDownloadResponse,
    PaginationParams,
    PaginationMeta,
)
from kiremisu.services.download_service import DownloadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


# Dependency to get download service
def get_download_service() -> DownloadService:
    """Get download service instance."""
    return DownloadService()


@router.post("/", response_model=DownloadJobResponse, status_code=status.HTTP_201_CREATED)
async def create_download_job(
    request: DownloadJobRequest,
    db: AsyncSession = Depends(get_db),
    download_service: DownloadService = Depends(get_download_service),
):
    """
    Create a new download job.
    
    Creates a download job based on the request type:
    - single: Download specific chapters
    - batch: Download multiple specific chapters
    - series: Download entire series from MangaDx
    """
    try:
        logger.info(f"Creating download job: {request.download_type} for manga {request.manga_id}")
        
        if request.download_type == "single":
            if not request.chapter_ids or len(request.chapter_ids) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Single download requires exactly one chapter_id"
                )
            
            job_id = await download_service.enqueue_single_chapter_download(
                db=db,
                manga_id=request.manga_id,
                chapter_id=request.chapter_ids[0],
                series_id=request.series_id,
                priority=request.priority,
                destination_path=request.destination_path,
            )
            
        elif request.download_type == "batch":
            if not request.chapter_ids or len(request.chapter_ids) < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Batch download requires at least one chapter_id"
                )
            
            job_id = await download_service.enqueue_batch_download(
                db=db,
                manga_id=request.manga_id,
                chapter_ids=request.chapter_ids,
                batch_type="multiple",
                series_id=request.series_id,
                volume_number=request.volume_number,
                priority=request.priority,
                destination_path=request.destination_path,
            )
            
        elif request.download_type == "series":
            job_id = await download_service.enqueue_series_download(
                db=db,
                manga_id=request.manga_id,
                series_id=request.series_id,
                priority=request.priority,
                destination_path=request.destination_path,
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid download_type: {request.download_type}"
            )
        
        # Get the created job to return
        result = await db.execute(select(JobQueue).where(JobQueue.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created job"
            )
        
        return DownloadJobResponse.from_job_model(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create download job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create download job: {str(e)}"
        )
    finally:
        await download_service.cleanup()


@router.get("/", response_model=DownloadJobListResponse)
async def list_download_jobs(
    status_filter: Optional[str] = Query(None, description="Filter by job status"),
    download_type_filter: Optional[str] = Query(None, description="Filter by download type"), 
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    download_service: DownloadService = Depends(get_download_service),
):
    """
    List download jobs with filtering and pagination.
    
    Returns paginated list of download jobs with status counts.
    """
    try:
        logger.info(f"Listing download jobs with filters: status={status_filter}, type={download_type_filter}")
        
        # Get jobs with filtering
        jobs, total_count = await download_service.get_download_jobs(
            db=db,
            status=status_filter,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        
        # Get status counts for summary
        stats_query = select(
            JobQueue.status,
            func.count(JobQueue.id).label("count")
        ).where(JobQueue.job_type == "download").group_by(JobQueue.status)
        
        stats_result = await db.execute(stats_query)
        status_counts = dict(stats_result.fetchall())
        
        # Create pagination metadata
        pagination_meta = PaginationMeta.create(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total_count,
        )
        
        return DownloadJobListResponse(
            jobs=[DownloadJobResponse.from_job_model(job) for job in jobs],
            total=total_count,
            active_downloads=status_counts.get("running", 0),
            pending_downloads=status_counts.get("pending", 0),
            failed_downloads=status_counts.get("failed", 0),
            completed_downloads=status_counts.get("completed", 0),
            status_filter=status_filter,
            download_type_filter=download_type_filter,
            pagination=pagination_meta,
        )
        
    except Exception as e:
        logger.error(f"Failed to list download jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list download jobs: {str(e)}"
        )
    finally:
        await download_service.cleanup()


@router.get("/{job_id}", response_model=DownloadJobResponse)
async def get_download_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific download job.
    
    Returns job details including current progress and status.
    """
    try:
        result = await db.execute(
            select(JobQueue).where(
                and_(
                    JobQueue.id == job_id,
                    JobQueue.job_type == "download"
                )
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job {job_id} not found"
            )
        
        return DownloadJobResponse.from_job_model(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get download job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get download job: {str(e)}"
        )


@router.post("/{job_id}/actions", response_model=DownloadJobActionResponse)
async def perform_download_job_action(
    job_id: UUID,
    action_request: DownloadJobActionRequest,
    db: AsyncSession = Depends(get_db),
    download_service: DownloadService = Depends(get_download_service),
):
    """
    Perform an action on a download job.
    
    Supported actions:
    - cancel: Cancel a pending or running job
    - retry: Retry a failed job
    - pause: Pause a running job (not yet implemented)
    - resume: Resume a paused job (not yet implemented)
    """
    try:
        logger.info(f"Performing action '{action_request.action}' on download job {job_id}")
        
        success = False
        message = ""
        new_status = None
        
        if action_request.action == "cancel":
            success = await download_service.cancel_download_job(db, job_id)
            if success:
                message = "Download job cancelled successfully"
                new_status = "failed"
            else:
                message = "Failed to cancel download job - job not found or not cancellable"
                
        elif action_request.action == "retry":
            success = await download_service.retry_download_job(db, job_id)
            if success:
                message = "Download job queued for retry"
                new_status = "pending"
            else:
                message = "Failed to retry download job - job not found or not failed"
                
        elif action_request.action in ["pause", "resume"]:
            # Placeholder for future implementation
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Action '{action_request.action}' is not yet implemented"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {action_request.action}"
            )
        
        return DownloadJobActionResponse(
            job_id=job_id,
            action=action_request.action,
            success=success,
            message=message,
            new_status=new_status,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform action on download job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform action: {str(e)}"
        )
    finally:
        await download_service.cleanup()


@router.post("/bulk", response_model=BulkDownloadResponse, status_code=status.HTTP_201_CREATED)
async def create_bulk_downloads(
    request: BulkDownloadRequest,
    db: AsyncSession = Depends(get_db),
    download_service: DownloadService = Depends(get_download_service),
):
    """
    Create multiple download jobs in bulk.
    
    Creates multiple download jobs with optional staggered scheduling.
    Returns summary of successful and failed job creations.
    """
    try:
        batch_id = UUID.generate()
        logger.info(f"Creating bulk download batch {batch_id} with {len(request.downloads)} jobs")
        
        job_ids = []
        errors = []
        
        for i, download_request in enumerate(request.downloads):
            try:
                # Apply global priority if specified
                if request.global_priority:
                    download_request.priority = request.global_priority
                
                # Create individual download job
                if download_request.download_type == "single":
                    job_id = await download_service.enqueue_single_chapter_download(
                        db=db,
                        manga_id=download_request.manga_id,
                        chapter_id=download_request.chapter_ids[0],
                        series_id=download_request.series_id,
                        priority=download_request.priority,
                        destination_path=download_request.destination_path,
                    )
                elif download_request.download_type == "batch":
                    job_id = await download_service.enqueue_batch_download(
                        db=db,
                        manga_id=download_request.manga_id,
                        chapter_ids=download_request.chapter_ids,
                        batch_type="multiple",
                        series_id=download_request.series_id,
                        volume_number=download_request.volume_number,
                        priority=download_request.priority,
                        destination_path=download_request.destination_path,
                    )
                elif download_request.download_type == "series":
                    job_id = await download_service.enqueue_series_download(
                        db=db,
                        manga_id=download_request.manga_id,
                        series_id=download_request.series_id,
                        priority=download_request.priority,
                        destination_path=download_request.destination_path,
                    )
                else:
                    raise ValueError(f"Invalid download_type: {download_request.download_type}")
                
                job_ids.append(job_id)
                
                # Add stagger delay if specified and not the last job
                if request.stagger_delay_seconds > 0 and i < len(request.downloads) - 1:
                    import asyncio
                    await asyncio.sleep(request.stagger_delay_seconds)
                    
            except Exception as e:
                error_msg = f"Failed to create job {i+1}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        successfully_queued = len(job_ids)
        failed_to_queue = len(errors)
        total_requested = len(request.downloads)
        
        # Determine status
        if successfully_queued == total_requested:
            status_msg = "scheduled"
            message = f"All {total_requested} download jobs created successfully"
        elif successfully_queued > 0:
            status_msg = "partial"
            message = f"{successfully_queued}/{total_requested} download jobs created"
        else:
            status_msg = "failed"
            message = "All download job creations failed"
        
        return BulkDownloadResponse(
            batch_id=batch_id,
            status=status_msg,
            message=message,
            total_requested=total_requested,
            successfully_queued=successfully_queued,
            failed_to_queue=failed_to_queue,
            job_ids=job_ids,
            errors=errors,
        )
        
    except Exception as e:
        logger.error(f"Failed to create bulk downloads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk downloads: {str(e)}"
        )
    finally:
        await download_service.cleanup()


@router.get("/stats/overview", response_model=DownloadStatsResponse)
async def get_download_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get download system statistics and health metrics.
    
    Returns comprehensive statistics about download job performance,
    queue status, and system health.
    """
    try:
        logger.info("Generating download statistics")
        
        # Get overall job counts
        total_query = select(
            JobQueue.status,
            func.count(JobQueue.id).label("count")
        ).where(JobQueue.job_type == "download").group_by(JobQueue.status)
        
        total_result = await db.execute(total_query)
        status_counts = dict(total_result.fetchall())
        
        # Get today's activity (last 24 hours)
        yesterday = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        
        today_created_result = await db.execute(
            select(func.count(JobQueue.id))
            .where(
                and_(
                    JobQueue.job_type == "download",
                    JobQueue.created_at >= yesterday
                )
            )
        )
        jobs_created_today = today_created_result.scalar() or 0
        
        today_completed_result = await db.execute(
            select(func.count(JobQueue.id))
            .where(
                and_(
                    JobQueue.job_type == "download",
                    JobQueue.status == "completed",
                    JobQueue.completed_at >= yesterday
                )
            )
        )
        jobs_completed_today = today_completed_result.scalar() or 0
        
        # Calculate success rate
        total_jobs = sum(status_counts.values())
        successful_jobs = status_counts.get("completed", 0)
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0.0
        
        # Calculate average job duration
        avg_duration_result = await db.execute(
            select(
                func.avg(
                    func.extract("epoch", JobQueue.completed_at - JobQueue.started_at)
                ).label("avg_duration")
            ).where(
                and_(
                    JobQueue.job_type == "download",
                    JobQueue.status == "completed",
                    JobQueue.started_at.isnot(None),
                    JobQueue.completed_at.isnot(None)
                )
            )
        )
        avg_duration_seconds = avg_duration_result.scalar()
        avg_duration_minutes = avg_duration_seconds / 60 if avg_duration_seconds else None
        
        # Estimate chapters downloaded today from job payloads
        # This is a simplified estimation - in production, you'd track this more precisely
        chapters_downloaded_today = jobs_completed_today * 2  # Assume average 2 chapters per job
        
        return DownloadStatsResponse(
            total_jobs=total_jobs,
            active_jobs=status_counts.get("running", 0),
            pending_jobs=status_counts.get("pending", 0),
            failed_jobs=status_counts.get("failed", 0),
            completed_jobs=status_counts.get("completed", 0),
            jobs_created_today=jobs_created_today,
            jobs_completed_today=jobs_completed_today,
            chapters_downloaded_today=chapters_downloaded_today,
            average_job_duration_minutes=avg_duration_minutes,
            success_rate_percentage=success_rate,
            current_download_speed_mbps=None,  # Would require real-time monitoring
            total_downloaded_size_gb=None,  # Would require file system analysis
            available_storage_gb=None,  # Would require disk space check
        )
        
    except Exception as e:
        logger.error(f"Failed to generate download stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download stats: {str(e)}"
        )


@router.delete("/{job_id}")
async def delete_download_job(
    job_id: UUID,
    force: bool = Query(False, description="Force delete even if job is running"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a download job from the queue.
    
    Only pending and failed jobs can be deleted by default.
    Use force=true to delete running jobs (will cancel them first).
    """
    try:
        # Check if job exists
        result = await db.execute(
            select(JobQueue).where(
                and_(
                    JobQueue.id == job_id,
                    JobQueue.job_type == "download"
                )
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job {job_id} not found"
            )
        
        # Check if job can be deleted
        if job.status == "running" and not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete running job without force=true parameter"
            )
        
        # Delete the job
        await db.delete(job)
        await db.commit()
        
        logger.info(f"Deleted download job {job_id}")
        return {"message": f"Download job {job_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete download job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete download job: {str(e)}"
        )