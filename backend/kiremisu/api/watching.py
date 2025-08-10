"""API endpoints for watching series functionality."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import WatchingResponse, WatchingContextRequest, ErrorResponse
from kiremisu.services.watching_service import WatchingService
from kiremisu.core.error_handler import create_not_found_error, create_standardized_error_response

router = APIRouter(prefix="/api/watching", tags=["watching"])
logger = logging.getLogger(__name__)

# Use the global limiter from main app
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=List[WatchingResponse], responses={
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def get_watching_list(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of series to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of series to return"),
    # TODO: Add user context parameter for multi-user support
    # user_context: Optional[UserContextBase] = Depends(get_current_user)
) -> List[WatchingResponse]:
    """Get list of all watched series.
    
    TODO: Add user filtering when user authentication is implemented.
    Currently returns all watched series in the system.
    """
    try:
        watched_series = await WatchingService.get_watched_series(db, skip=skip, limit=limit)
        return [WatchingResponse.from_series(series) for series in watched_series]
    except Exception as e:
        logger.error(f"Error getting watching list: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to get watching list",
            error_code="WATCHING_LIST_ERROR"
        )
        return JSONResponse(status_code=500, content=error_response)


@router.get("/{series_id}", response_model=WatchingResponse, responses={
    404: {"model": ErrorResponse, "description": "Series not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def get_watching_status(
    series_id: UUID, 
    db: AsyncSession = Depends(get_db)
    # TODO: Add user context for ownership validation
    # user_context: Optional[UserContextBase] = Depends(get_current_user)
) -> WatchingResponse:
    """Get watching status for a specific series.
    
    TODO: Add user context validation when authentication is implemented.
    """
    try:
        # Get the series to check its watching status
        from kiremisu.database.models import Series
        from sqlalchemy import select

        result = await db.execute(select(Series).where(Series.id == series_id))
        series = result.scalar_one_or_none()

        if not series:
            error_response = create_not_found_error("series", str(series_id))
            return JSONResponse(status_code=404, content=error_response)

        return WatchingResponse.from_series(series)
    except Exception as e:
        logger.error(f"Error getting watching status for series {series_id}: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to get watching status",
            error_code="WATCHING_STATUS_ERROR"
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post("/{series_id}", response_model=WatchingResponse, responses={
    404: {"model": ErrorResponse, "description": "Series not found"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
@limiter.limit("10/minute")
async def watch_series(
    request: Request, 
    series_id: UUID, 
    db: AsyncSession = Depends(get_db)
    # TODO: Add user context for ownership validation and user-specific watching
    # user_context: Optional[UserContextBase] = Depends(get_current_user)
) -> WatchingResponse:
    """Start watching a series.
    
    TODO: Implement user-specific watching when authentication is added.
    Currently enables watching for all users in single-user mode.
    """
    try:
        series = await WatchingService.toggle_watch(db=db, series_id=series_id, enabled=True)
        return WatchingResponse.from_series(series)
    except ValueError as e:
        error_response = create_not_found_error("series", str(series_id))
        return JSONResponse(status_code=404, content=error_response)
    except Exception as e:
        logger.error(f"Error watching series {series_id}: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to watch series",
            error_code="WATCH_TOGGLE_ERROR"
        )
        return JSONResponse(status_code=500, content=error_response)


@router.delete("/{series_id}", responses={
    200: {"description": "Series unwatched successfully"},
    404: {"model": ErrorResponse, "description": "Series not found"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
@limiter.limit("10/minute")
async def unwatch_series(
    request: Request, 
    series_id: UUID, 
    db: AsyncSession = Depends(get_db)
    # TODO: Add user context for ownership validation
    # user_context: Optional[UserContextBase] = Depends(get_current_user)
) -> dict:
    """Stop watching a series.
    
    TODO: Implement user-specific unwatching when authentication is added.
    """
    try:
        await WatchingService.toggle_watch(db=db, series_id=series_id, enabled=False)
        return {"message": "Series unwatched successfully", "status": "success"}
    except ValueError as e:
        error_response = create_not_found_error("series", str(series_id))
        return JSONResponse(status_code=404, content=error_response)
    except Exception as e:
        logger.error(f"Error unwatching series {series_id}: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to unwatch series",
            error_code="UNWATCH_ERROR"
        )
        return JSONResponse(status_code=500, content=error_response)