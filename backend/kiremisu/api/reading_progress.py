"""
Reading progress API endpoints for R-2: Mark-read & progress bars.

This module provides comprehensive reading progress functionality including:
- Toggle read state for chapters and series
- Reading progress tracking per chapter
- User reading statistics and analytics
- Integration with existing manga reader architecture
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.unified_auth import get_current_user
from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    ChapterMarkReadResponse,
    ReadingProgressResponse,
    ReadingProgressUpdateRequest,
    SeriesProgressResponse,
    UserReadingStatsResponse,
)
from kiremisu.services.reading_progress import ReadingProgressService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reading-progress", tags=["reading-progress"])


@router.put("/chapters/{chapter_id}/progress", response_model=ReadingProgressResponse)
async def update_chapter_progress(
    chapter_id: UUID,
    progress: ReadingProgressUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> ReadingProgressResponse:
    """
    Update reading progress for a chapter.

    This endpoint allows updating the current reading position for a chapter,
    automatically handling completion detection and series progress updates.

    Args:
        chapter_id: Chapter UUID
        progress: Reading progress update data
        db: Database session

    Returns:
        Updated reading progress information

    Raises:
        HTTPException: If chapter not found or invalid progress data
    """
    try:
        return await ReadingProgressService.update_chapter_progress(db, str(chapter_id), progress)
    except ValueError as e:
        logger.warning(
            "Failed to update chapter progress: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating chapter progress: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reading progress",
        )


@router.post("/chapters/{chapter_id}/mark-read", response_model=ChapterMarkReadResponse)
async def toggle_chapter_read_status(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> ChapterMarkReadResponse:
    """
    Toggle the read status of a chapter.

    This endpoint toggles between read and unread status for a chapter,
    automatically updating series read counts and timestamps.

    Args:
        chapter_id: Chapter UUID
        db: Database session

    Returns:
        Updated chapter read status information

    Raises:
        HTTPException: If chapter not found
    """
    try:
        new_status, read_at = await ReadingProgressService.toggle_chapter_read_status(
            db, str(chapter_id)
        )

        # Get the chapter to find the series_id
        from sqlalchemy import select

        from kiremisu.database.models import Chapter

        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise ValueError(f"Chapter with ID {chapter_id} not found")

        # Get updated series read count
        series_progress = await ReadingProgressService.get_series_progress(
            db, str(chapter.series_id)
        )

        return ChapterMarkReadResponse(
            id=chapter_id,
            is_read=new_status,
            read_at=read_at,
            series_read_chapters=series_progress.read_chapters,
        )
    except ValueError as e:
        logger.warning(
            "Failed to toggle chapter read status: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error toggling chapter read status: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chapter read status",
        )


@router.post("/chapters/{chapter_id}/mark-unread", response_model=ChapterMarkReadResponse)
async def mark_chapter_unread(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> ChapterMarkReadResponse:
    """
    Mark a chapter as unread.

    This endpoint specifically marks a chapter as unread, useful for
    dedicated unread actions in the UI.

    Args:
        chapter_id: Chapter UUID
        db: Database session

    Returns:
        Updated chapter read status information
    """
    try:
        # Check current status and toggle only if currently read
        from sqlalchemy import select

        from kiremisu.database.models import Chapter

        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise ValueError(f"Chapter with ID {chapter_id} not found")

        if not chapter.is_read:
            # Already unread, return current status
            series_progress = await ReadingProgressService.get_series_progress(
                db, str(chapter.series_id)
            )
            return ChapterMarkReadResponse(
                id=chapter_id,
                is_read=False,
                read_at=None,
                series_read_chapters=series_progress.read_chapters,
            )

        # Toggle to unread
        new_status, read_at = await ReadingProgressService.toggle_chapter_read_status(
            db, str(chapter_id)
        )

        series_progress = await ReadingProgressService.get_series_progress(
            db, str(chapter.series_id)
        )

        return ChapterMarkReadResponse(
            id=chapter_id,
            is_read=new_status,
            read_at=read_at,
            series_read_chapters=series_progress.read_chapters,
        )

    except ValueError as e:
        logger.warning(
            "Failed to mark chapter as unread: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error marking chapter as unread: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark chapter as unread",
        )


@router.get("/series/{series_id}/stats", response_model=SeriesProgressResponse)
async def get_series_progress(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> SeriesProgressResponse:
    """
    Get reading progress statistics for a series.

    This endpoint provides comprehensive progress information for a series
    including completion percentage, recent chapters, and reading timeline.

    Args:
        series_id: Series UUID
        db: Database session

    Returns:
        Series reading progress information

    Raises:
        HTTPException: If series not found
    """
    try:
        return await ReadingProgressService.get_series_progress(db, str(series_id))
    except ValueError as e:
        logger.warning(
            "Failed to get series progress: %s",
            str(e),
            extra={"series_id": str(series_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error getting series progress: %s",
            str(e),
            extra={"series_id": str(series_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get series progress",
        )


@router.post("/series/{series_id}/mark-read")
async def mark_series_read(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Mark all chapters in a series as read.

    This endpoint marks all chapters in a series as read, useful for
    bulk operations when catching up on a series.

    Args:
        series_id: Series UUID
        db: Database session

    Returns:
        Operation result with number of chapters updated

    Raises:
        HTTPException: If series not found
    """
    try:
        chapters_updated = await ReadingProgressService.mark_series_read(db, str(series_id))

        return {
            "status": "success",
            "message": f"Marked {chapters_updated} chapters as read",
            "series_id": str(series_id),
            "chapters_updated": chapters_updated,
        }

    except ValueError as e:
        logger.warning(
            "Failed to mark series as read: %s",
            str(e),
            extra={"series_id": str(series_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error marking series as read: %s",
            str(e),
            extra={"series_id": str(series_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark series as read",
        )


@router.post("/series/{series_id}/mark-unread")
async def mark_series_unread(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Mark all chapters in a series as unread.

    This endpoint marks all chapters in a series as unread, useful for
    re-reading scenarios or correcting bulk read operations.

    Args:
        series_id: Series UUID
        db: Database session

    Returns:
        Operation result with number of chapters updated

    Raises:
        HTTPException: If series not found
    """
    try:
        chapters_updated = await ReadingProgressService.mark_series_unread(db, str(series_id))

        return {
            "status": "success",
            "message": f"Marked {chapters_updated} chapters as unread",
            "series_id": str(series_id),
            "chapters_updated": chapters_updated,
        }

    except ValueError as e:
        logger.warning(
            "Failed to mark series as unread: %s",
            str(e),
            extra={"series_id": str(series_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error marking series as unread: %s",
            str(e),
            extra={"series_id": str(series_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark series as unread",
        )


@router.get("/user/stats", response_model=UserReadingStatsResponse)
async def get_user_reading_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> UserReadingStatsResponse:
    """
    Get comprehensive user reading statistics.

    This endpoint provides detailed reading statistics including:
    - Overall progress and completion rates
    - Reading streaks and activity patterns
    - Favorite genres and recent activity
    - Weekly and monthly reading summaries

    Args:
        db: Database session

    Returns:
        Comprehensive user reading statistics
    """
    try:
        return await ReadingProgressService.get_user_reading_stats(db)
    except Exception as e:
        logger.error(
            "Unexpected error getting user reading stats: %s",
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user reading statistics",
        )


# Additional endpoint for getting chapter reading progress
@router.get("/chapters/{chapter_id}/progress", response_model=ReadingProgressResponse)
async def get_chapter_progress(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> ReadingProgressResponse:
    """
    Get current reading progress for a specific chapter.

    This endpoint returns the current reading progress state for a chapter,
    useful for resuming reading or displaying progress indicators.

    Args:
        chapter_id: Chapter UUID
        db: Database session

    Returns:
        Current reading progress information

    Raises:
        HTTPException: If chapter not found
    """
    try:
        from sqlalchemy import select

        from kiremisu.database.models import Chapter

        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chapter with ID {chapter_id} not found",
            )

        # Calculate progress percentage
        progress_percentage = (
            (chapter.last_read_page + 1) / chapter.page_count * 100 if chapter.page_count > 0 else 0
        )

        return ReadingProgressResponse(
            chapter_id=chapter.id,
            series_id=chapter.series_id,
            current_page=chapter.last_read_page,
            total_pages=chapter.page_count,
            progress_percentage=progress_percentage,
            is_read=chapter.is_read,
            started_at=getattr(chapter, "started_reading_at", None),
            read_at=chapter.read_at,
            updated_at=chapter.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error getting chapter progress: %s",
            str(e),
            extra={"chapter_id": str(chapter_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chapter progress",
        )
