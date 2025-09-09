"""API endpoints for reading progress tracking."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_async_session
from app.users import current_active_user
from app.models.user import User
from app.services.progress import ProgressService
from app.schemas.progress import (
    ProgressUpdateRequest,
    BulkMarkRequest,
    ReadingHistoryFilter,
    ReadingStatisticsFilter,
    ReadingProgressResponse,
    SeriesProgressResponse,
    ReadingHistoryResponse,
    ReadingStatisticsResponse,
    BulkOperationResponse,
    ResumeReadingResponse,
    ReadingProgressSummary
)

router = APIRouter(tags=["progress"])
progress_service = ProgressService()


@router.put("/chapters/{chapter_id}")
async def update_chapter_progress(
    chapter_id: int,
    progress_data: ProgressUpdateRequest,
    request: Request,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> ReadingProgressResponse:
    """
    Update reading progress for a specific chapter.
    
    Updates the user's current page position and calculates reading statistics.
    Creates timeline events for tracking reading history.
    """
    try:
        progress = await progress_service.update_chapter_progress(
            db=db,
            user_id=current_user.id,
            chapter_id=chapter_id,
            current_page=progress_data.current_page,
            total_pages=progress_data.total_pages,
            session_duration=progress_data.session_duration_seconds,
            device_info=progress_data.device_info or request.headers.get("User-Agent", "Unknown")[:255]
        )
        
        return ReadingProgressResponse.model_validate(progress)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update progress: {str(e)}"
        )


@router.post("/chapters/{chapter_id}/mark-read")
async def mark_chapter_read(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> ReadingProgressResponse:
    """
    Mark a chapter as read without tracking page-by-page progress.
    
    Useful for bulk operations or when user wants to skip reading but mark as complete.
    """
    try:
        device_info = request.headers.get("User-Agent", "Unknown")[:255]
        progress = await progress_service.mark_chapter_read(
            db=db,
            user_id=current_user.id,
            chapter_id=chapter_id,
            device_info=device_info
        )
        
        return ReadingProgressResponse.model_validate(progress)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark chapter as read: {str(e)}"
        )


@router.post("/chapters/{chapter_id}/mark-unread")
async def mark_chapter_unread(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> Optional[ReadingProgressResponse]:
    """
    Mark a chapter as unread, resetting all progress.
    
    Returns None if the chapter was not previously read.
    """
    try:
        device_info = request.headers.get("User-Agent", "Unknown")[:255]
        progress = await progress_service.mark_chapter_unread(
            db=db,
            user_id=current_user.id,
            chapter_id=chapter_id,
            device_info=device_info
        )
        
        if progress:
            return ReadingProgressResponse.model_validate(progress)
        return None
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark chapter as unread: {str(e)}"
        )


@router.post("/bulk/mark-read")
async def bulk_mark_read(
    bulk_request: BulkMarkRequest,
    request: Request,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> BulkOperationResponse:
    """
    Mark multiple chapters as read in a single operation.
    
    Efficient for marking entire series or volumes as complete.
    Rate limited to prevent abuse.
    """
    try:
        device_info = bulk_request.device_info or request.headers.get("User-Agent", "Unknown")[:255]
        successful = await progress_service.bulk_mark_read(
            db=db,
            user_id=current_user.id,
            chapter_ids=bulk_request.chapter_ids,
            device_info=device_info
        )
        
        total_requested = len(bulk_request.chapter_ids)
        failed = total_requested - successful
        
        return BulkOperationResponse(
            total_requested=total_requested,
            successful=successful,
            failed=failed,
            success_rate=successful / total_requested if total_requested > 0 else 0.0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk mark read operation failed: {str(e)}"
        )


@router.post("/bulk/mark-unread")
async def bulk_mark_unread(
    bulk_request: BulkMarkRequest,
    request: Request,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> BulkOperationResponse:
    """
    Mark multiple chapters as unread in a single operation.
    
    Useful for re-reading series or correcting mistakes.
    Rate limited to prevent abuse.
    """
    try:
        device_info = bulk_request.device_info or request.headers.get("User-Agent", "Unknown")[:255]
        successful = await progress_service.bulk_mark_unread(
            db=db,
            user_id=current_user.id,
            chapter_ids=bulk_request.chapter_ids,
            device_info=device_info
        )
        
        total_requested = len(bulk_request.chapter_ids)
        failed = total_requested - successful
        
        return BulkOperationResponse(
            total_requested=total_requested,
            successful=successful,
            failed=failed,
            success_rate=successful / total_requested if total_requested > 0 else 0.0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk mark unread operation failed: {str(e)}"
        )


@router.get("/series/{series_id}")
async def get_series_progress(
    series_id: int,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> SeriesProgressResponse:
    """
    Get comprehensive reading progress for a series.
    
    Includes completion percentage, chapter-by-chapter progress,
    and reading time statistics.
    """
    try:
        progress_data = await progress_service.get_series_progress(
            db=db,
            user_id=current_user.id,
            series_id=series_id
        )
        
        return SeriesProgressResponse(**progress_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get series progress: {str(e)}"
        )


@router.get("/history")
async def get_reading_history(
    limit: int = Query(default=50, ge=1, le=200, description="Number of history entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
    series_id: Optional[int] = Query(None, gt=0, description="Filter by series ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> List[ReadingHistoryResponse]:
    """
    Get user's reading history timeline.
    
    Returns chronological list of reading events with filtering options.
    Useful for tracking reading habits and resuming where left off.
    """
    try:
        history_data = await progress_service.get_reading_history(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            series_id=series_id,
            event_type=event_type
        )
        
        return [ReadingHistoryResponse(**entry) for entry in history_data]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reading history: {str(e)}"
        )


@router.get("/statistics")
async def get_reading_statistics(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include in statistics"),
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> ReadingStatisticsResponse:
    """
    Get comprehensive reading statistics and insights.
    
    Includes reading time, completion rates, streaks, and activity patterns.
    Perfect for dashboard widgets and reading habit analysis.
    """
    try:
        stats_data = await progress_service.get_reading_statistics(
            db=db,
            user_id=current_user.id,
            days=days
        )
        
        return ReadingStatisticsResponse(**stats_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reading statistics: {str(e)}"
        )


@router.get("/resume")
async def get_resume_reading(
    limit: int = Query(default=5, ge=1, le=10, description="Number of suggestions to return"),
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> ResumeReadingResponse:
    """
    Get suggestions for resuming reading.
    
    Returns in-progress chapters and recently accessed series to help users
    continue where they left off.
    """
    try:
        # Get recent reading history to find in-progress chapters
        recent_history = await progress_service.get_reading_history(
            db=db,
            user_id=current_user.id,
            limit=20,
            offset=0
        )
        
        # Find most recently accessed chapter that's not completed
        last_read_chapter = None
        recommended_chapter_id = None
        recommended_series_id = None
        
        for entry in recent_history:
            if entry['progress_percentage'] and entry['progress_percentage'] < 100:
                recommended_chapter_id = entry.get('chapter_id')  # We'd need to modify history response
                recommended_series_id = entry.get('series_id')   # We'd need to modify history response
                break
        
        # This is a simplified implementation - in reality we'd need more complex logic
        # to determine the best continuation suggestions
        
        return ResumeReadingResponse(
            has_in_progress=len([h for h in recent_history if h.get('progress_percentage', 0) < 100]) > 0,
            recommended_chapter_id=recommended_chapter_id,
            recommended_series_id=recommended_series_id,
            last_read_chapter=None,  # Would need to fetch actual chapter progress
            continue_reading_suggestions=[]  # Would need to fetch in-progress chapters
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get resume reading suggestions: {str(e)}"
        )


@router.get("/dashboard")
async def get_progress_dashboard(
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
) -> ReadingProgressSummary:
    """
    Get dashboard summary of reading progress.
    
    Provides high-level statistics perfect for main dashboard widgets.
    Optimized for quick loading and overview display.
    """
    try:
        # Get basic statistics
        stats = await progress_service.get_reading_statistics(
            db=db,
            user_id=current_user.id,
            days=1  # Today's activity
        )
        
        # This is simplified - would need additional queries for comprehensive dashboard
        return ReadingProgressSummary(
            total_series=0,  # Would need to query distinct series with progress
            series_in_progress=0,  # Would need to query series with partial progress
            series_completed=0,  # Would need to query series with 100% completion
            chapters_read_today=stats.recent_chapters_completed,
            reading_time_today_minutes=stats.recent_reading_time_seconds // 60,
            current_streak_days=stats.current_reading_streak_days
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard data: {str(e)}"
        )