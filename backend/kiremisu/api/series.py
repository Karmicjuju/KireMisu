"""API endpoints for manga series."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from kiremisu.database.connection import get_db
from kiremisu.core.unified_auth import get_current_user
from kiremisu.database.models import Series, Chapter, Tag, series_tags
from kiremisu.database.schemas import (
    SeriesResponse,
    ChapterResponse,
    SeriesProgressResponse,
    WatchToggleRequest,
    WatchToggleResponse,
)
from kiremisu.database.utils import (
    with_db_retry,
    log_slow_query,
    safe_like_pattern,
    validate_query_params,
)
from kiremisu.services.watching_service import WatchingService

router = APIRouter(prefix="/api/series", tags=["series"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[SeriesResponse])
@with_db_retry(max_attempts=2)
@log_slow_query("get_series_list", 2.0)
async def get_series_list(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of series to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of series to return"),
    search: Optional[str] = Query(None, description="Search term for series title"),
    tag_ids: Optional[List[UUID]] = Query(None, description="Filter by tag IDs (AND logic)"),
    tag_names: Optional[List[str]] = Query(None, description="Filter by tag names (AND logic)"),
) -> List[SeriesResponse]:
    """Get list of all series with optional tag filtering."""
    # Validate input parameters
    try:
        clean_params = validate_query_params(search=search, tag_names=tag_names or [])
        search = clean_params.get("search")
        tag_names = clean_params.get("tag_names")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = select(Series).options(selectinload(Series.user_tags))

    # Add search filter if provided
    if search:
        search_term = safe_like_pattern(search)
        query = query.where(Series.title_primary.ilike(search_term))

    # Add tag filtering if provided
    if tag_ids or tag_names:
        # Build a subquery for series that have ALL specified tags
        filters = []

        if tag_ids:
            for tag_id in tag_ids:
                subquery = select(series_tags.c.series_id).where(series_tags.c.tag_id == tag_id)
                filters.append(Series.id.in_(subquery))

        if tag_names:
            for tag_name in tag_names:
                # Find tag by name and use its ID
                tag_subquery = select(Tag.id).where(func.lower(Tag.name) == func.lower(tag_name))
                series_subquery = select(series_tags.c.series_id).where(
                    series_tags.c.tag_id.in_(tag_subquery)
                )
                filters.append(Series.id.in_(series_subquery))

        # Apply all filters (AND logic)
        for filter_condition in filters:
            query = query.where(filter_condition)

    # Add ordering and pagination
    query = query.order_by(Series.title_primary.asc()).offset(skip).limit(limit)

    result = await db.execute(query)
    series_list = result.scalars().all()

    return [SeriesResponse.from_model(series) for series in series_list]


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> SeriesResponse:
    """Get series details by ID."""
    result = await db.execute(
        select(Series).options(selectinload(Series.user_tags)).where(Series.id == series_id)
    )
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    return SeriesResponse.from_model(series)


@router.get("/{series_id}/chapters", response_model=List[ChapterResponse])
async def get_series_chapters(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of chapters to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of chapters to return"),
) -> List[ChapterResponse]:
    """Get all chapters for a series."""
    # First verify series exists
    series_result = await db.execute(select(Series).where(Series.id == series_id))
    series = series_result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Get chapters ordered by volume and chapter number
    result = await db.execute(
        select(Chapter)
        .where(Chapter.series_id == series_id)
        .order_by(Chapter.volume_number.asc().nulls_last(), Chapter.chapter_number.asc())
        .offset(skip)
        .limit(limit)
    )
    chapters = result.scalars().all()

    return [ChapterResponse.from_model(chapter) for chapter in chapters]


@router.get("/{series_id}/progress", response_model=SeriesProgressResponse)
async def get_series_progress(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> SeriesProgressResponse:
    """Get detailed progress information for a series."""
    # Get series
    series_result = await db.execute(select(Series).where(Series.id == series_id))
    series = series_result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Get recent read chapters (up to 5, ordered by read_at desc)
    recent_chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.series_id == series_id, Chapter.is_read == True)
        .order_by(Chapter.read_at.desc().nulls_last())
        .limit(5)
    )
    recent_chapters = recent_chapters_result.scalars().all()

    # Get most recent read timestamp
    last_read_result = await db.execute(
        select(func.max(Chapter.read_at)).where(
            Chapter.series_id == series_id, Chapter.is_read == True
        )
    )
    last_read_at = last_read_result.scalar()

    # Calculate progress percentage
    progress_percentage = 0.0
    if series.total_chapters > 0:
        progress_percentage = (series.read_chapters / series.total_chapters) * 100

    return SeriesProgressResponse(
        series_id=series_id,
        total_chapters=series.total_chapters,
        read_chapters=series.read_chapters,
        progress_percentage=round(progress_percentage, 2),
        recent_chapters=[ChapterResponse.from_model(chapter) for chapter in recent_chapters],
        last_read_at=last_read_at,
    )


@router.post("/{series_id}/watch", response_model=WatchToggleResponse)
async def toggle_series_watch(
    series_id: UUID,
    request: WatchToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> WatchToggleResponse:
    """Toggle watching status for a series."""
    try:
        series = await WatchingService.toggle_watch(
            db=db, series_id=series_id, enabled=request.enabled
        )

        return WatchToggleResponse.from_series(series)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error toggling watch status for series {series_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update watch status")
