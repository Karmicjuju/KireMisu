from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_async_session
from app.services.series import SeriesService
from app.schemas.series import (
    SeriesCreate, 
    SeriesUpdate, 
    SeriesResponse, 
    SeriesListResponse,
    SeriesWithChaptersResponse
)
from app.users import current_active_user
from app.core.rate_limit import create_rate_limit_dependency

# Setup logging
logger = logging.getLogger(__name__)

# Rate limiting dependencies
# More restrictive for write operations, lenient for read operations
read_rate_limit = create_rate_limit_dependency(max_requests=200, window_seconds=3600)  # 200 reads per hour
write_rate_limit = create_rate_limit_dependency(max_requests=50, window_seconds=3600)   # 50 writes per hour
search_rate_limit = create_rate_limit_dependency(max_requests=100, window_seconds=3600)  # 100 searches per hour

router = APIRouter()


def get_series_service(db: AsyncSession = Depends(get_async_session)) -> SeriesService:
    """Dependency to get SeriesService instance."""
    return SeriesService(db)


@router.get("/", response_model=SeriesListResponse)
async def get_series(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search query for title, author, or artist"),
    status: Optional[str] = Query(None, description="Filter by series status"),
    author: Optional[str] = Query(None, description="Filter by author"),
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get paginated list of series with optional filtering.
    
    - **page**: Page number (starts from 1)
    - **size**: Number of items per page (max 100)
    - **search**: Search in title, author, or artist fields
    - **status**: Filter by series status (ongoing, completed, hiatus, etc.)
    - **author**: Filter by author name
    """
    try:
        if search:
            return series_service.search_series_paginated(search, page, size)
        elif status:
            return series_service.get_series_by_status_paginated(status, page, size)
        elif author:
            return series_service.get_series_by_author_paginated(author, page, size)
        else:
            return series_service.get_all_series_paginated(page, size)
    except ValueError as e:
        logger.warning(f"Invalid request in get_series: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving series"
        )


@router.post("/", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    request: Request,
    series_data: SeriesCreate,
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Create a new series.
    
    - **title**: Series title (required)
    - **description**: Series description (optional)
    - **author**: Series author (optional)
    - **artist**: Series artist (optional)
    - **status**: Series status (optional)
    - **cover_path**: Path to cover image (optional)
    - **metadata_json**: Additional metadata as JSON (optional)
    """
    try:
        series = series_service.create_series(series_data)
        return SeriesResponse.model_validate(series)
    except ValueError as e:
        logger.warning(f"Invalid request in create_series: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the series"
        )


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series_by_id(
    request: Request,
    series_id: int,
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get a series by ID.
    
    - **series_id**: The ID of the series to retrieve
    """
    series = series_service.get_series_by_id(series_id)
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series with ID {series_id} not found"
        )
    
    return SeriesResponse.model_validate(series)


@router.patch("/{series_id}", response_model=SeriesResponse)
async def update_series(
    request: Request,
    series_id: int,
    series_data: SeriesUpdate,
    preview: bool = Query(False, description="Preview changes without saving"),
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Update a series with partial update support.
    
    - **series_id**: The ID of the series to update
    - **preview**: If true, returns preview of changes without saving
    - All fields are optional and will only be updated if provided
    """
    try:
        updated_series = await series_service.update_series(
            series_id=series_id,
            series_data=series_data,
            user_id=str(current_user.id),
            preview_mode=preview,
        )
        
        if not updated_series:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Series with ID {series_id} not found"
            )
        
        # If in preview mode, return the preview data
        if preview and isinstance(updated_series, dict):
            return updated_series
        
        return SeriesResponse.model_validate(updated_series)
    except ValueError as e:
        logger.warning(f"Invalid request in update_series: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in update_series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the series"
        )


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series(
    request: Request,
    series_id: int,
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Delete a series.
    
    - **series_id**: The ID of the series to delete
    
    This will also delete all associated chapters.
    """
    try:
        success = series_service.delete_series(series_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Series with ID {series_id} not found"
            )
    except ValueError as e:
        logger.warning(f"Invalid request in delete_series: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in delete_series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the series"
        )


@router.get("/recent/", response_model=List[SeriesResponse])
async def get_recent_series(
    limit: int = Query(10, ge=1, le=50, description="Number of recent series to return"),
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
):
    """
    Get recently created series.
    
    - **limit**: Number of recent series to return (max 50)
    """
    try:
        return series_service.get_recent_series(limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving recent series"
        )


@router.get("/updated/", response_model=List[SeriesResponse])
async def get_updated_series(
    limit: int = Query(10, ge=1, le=50, description="Number of updated series to return"),
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
):
    """
    Get recently updated series.
    
    - **limit**: Number of updated series to return (max 50)
    """
    try:
        return series_service.get_updated_series(limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving updated series"
        )


@router.get("/statistics/")
async def get_series_statistics(
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
):
    """
    Get statistics about series in the database.
    
    Returns counts by status and total series count.
    """
    try:
        return series_service.get_series_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving series statistics"
        )


@router.get("/{series_id}/history")
async def get_series_history(
    request: Request,
    series_id: int,
    limit: int = Query(50, ge=1, le=100, description="Number of history entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get change history for a series.
    
    - **series_id**: The ID of the series
    - **limit**: Number of history entries to return (max 100)
    - **offset**: Number of entries to skip for pagination
    """
    try:
        history = await series_service.get_series_history(
            series_id=series_id,
            limit=limit,
            offset=offset,
        )
        return history
    except Exception as e:
        logger.error(f"Unexpected error in get_series_history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving series history"
        )


@router.post("/{series_id}/restore/{history_id}", response_model=SeriesResponse)
async def restore_series_from_history(
    request: Request,
    series_id: int,
    history_id: int,
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Restore a series to a previous state from history.
    
    - **series_id**: The ID of the series to restore
    - **history_id**: The ID of the history entry to restore from
    """
    try:
        restored_series = await series_service.restore_series_from_history(
            series_id=series_id,
            history_id=history_id,
            user_id=str(current_user.id),
        )
        
        if not restored_series:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Series with ID {series_id} or history entry {history_id} not found"
            )
        
        return SeriesResponse.model_validate(restored_series)
    except ValueError as e:
        logger.warning(f"Invalid request in restore_series_from_history: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in restore_series_from_history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while restoring the series"
        )


@router.patch("/bulk", response_model=List[SeriesResponse])
async def bulk_update_series(
    request: Request,
    series_ids: List[int] = Query(..., description="List of series IDs to update"),
    series_data: SeriesUpdate = ...,
    current_user = Depends(current_active_user),
    series_service: SeriesService = Depends(get_series_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Update multiple series with the same data.
    
    - **series_ids**: List of series IDs to update (max 100)
    - **series_data**: Updates to apply to all series
    """
    try:
        if len(series_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update more than 100 series at once"
            )
        
        updated_series = await series_service.bulk_update_series(
            series_ids=series_ids,
            update_data=series_data,
            user_id=str(current_user.id),
        )
        
        return [SeriesResponse.model_validate(series) for series in updated_series]
    except ValueError as e:
        logger.warning(f"Invalid request in bulk_update_series: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in bulk_update_series: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while bulk updating series"
        )