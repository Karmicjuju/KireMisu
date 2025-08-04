"""API endpoints for manga series."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from kiremisu.database.connection import get_db
from kiremisu.database.models import Series, Chapter
from kiremisu.database.schemas import SeriesResponse, ChapterResponse

router = APIRouter(prefix="/api/series", tags=["series"])


@router.get("/", response_model=List[SeriesResponse])
async def get_series_list(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of series to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of series to return"),
    search: Optional[str] = Query(None, description="Search term for series title"),
) -> List[SeriesResponse]:
    """Get list of all series."""
    query = select(Series)

    # Add search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.where(Series.title_primary.ilike(search_term))

    # Add ordering and pagination
    query = query.order_by(Series.title_primary.asc()).offset(skip).limit(limit)

    result = await db.execute(query)
    series_list = result.scalars().all()

    return [SeriesResponse.from_model(series) for series in series_list]


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(series_id: UUID, db: AsyncSession = Depends(get_db)) -> SeriesResponse:
    """Get series details by ID."""
    result = await db.execute(select(Series).where(Series.id == series_id))
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    return SeriesResponse.from_model(series)


@router.get("/{series_id}/chapters", response_model=List[ChapterResponse])
async def get_series_chapters(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
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
