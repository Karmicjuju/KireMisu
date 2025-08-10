"""API endpoints for watching series functionality."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import WatchingResponse
from kiremisu.services.watching_service import WatchingService

router = APIRouter(prefix="/api/watching", tags=["watching"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[WatchingResponse])
async def get_watching_list(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of series to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of series to return"),
) -> List[WatchingResponse]:
    """Get list of all watched series."""
    try:
        watched_series = await WatchingService.get_watched_series(db, skip=skip, limit=limit)
        return [WatchingResponse.from_series(series) for series in watched_series]
    except Exception as e:
        logger.error(f"Error getting watching list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get watching list")


@router.get("/{series_id}", response_model=WatchingResponse)
async def get_watching_status(
    series_id: UUID, db: AsyncSession = Depends(get_db)
) -> WatchingResponse:
    """Get watching status for a specific series."""
    try:
        # Get the series to check its watching status
        from kiremisu.database.models import Series
        from sqlalchemy import select

        result = await db.execute(select(Series).where(Series.id == series_id))
        series = result.scalar_one_or_none()

        if not series:
            raise HTTPException(status_code=404, detail="Series not found")

        return WatchingResponse.from_series(series)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting watching status for series {series_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get watching status")


@router.post("/{series_id}", response_model=WatchingResponse)
async def watch_series(
    series_id: UUID, db: AsyncSession = Depends(get_db)
) -> WatchingResponse:
    """Start watching a series."""
    try:
        series = await WatchingService.toggle_watch(db=db, series_id=series_id, enabled=True)
        return WatchingResponse.from_series(series)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error watching series {series_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to watch series")


@router.delete("/{series_id}")
async def unwatch_series(series_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """Stop watching a series."""
    try:
        await WatchingService.toggle_watch(db=db, series_id=series_id, enabled=False)
        return {"message": "Series unwatched successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error unwatching series {series_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unwatch series")