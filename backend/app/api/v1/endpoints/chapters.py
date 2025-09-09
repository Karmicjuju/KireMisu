from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_async_session
from app.services.chapter import ChapterService
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterWithSeriesResponse,
    ChapterListResponse,
    BulkChapterUpdate,
)
from app.schemas.metadata_history import (
    MetadataHistoryWithUserResponse,
    HistoryListResponse,
)
from app.users import current_active_user
from app.core.rate_limit import create_rate_limit_dependency

# Setup logging
logger = logging.getLogger(__name__)

# Rate limiting dependencies
read_rate_limit = create_rate_limit_dependency(max_requests=200, window_seconds=3600)  # 200 reads per hour
write_rate_limit = create_rate_limit_dependency(max_requests=50, window_seconds=3600)   # 50 writes per hour
bulk_rate_limit = create_rate_limit_dependency(max_requests=10, window_seconds=3600)    # 10 bulk ops per hour

router = APIRouter()


def get_chapter_service(db: AsyncSession = Depends(get_async_session)) -> ChapterService:
    """Dependency to get ChapterService instance."""
    return ChapterService(db)


@router.get("/", response_model=ChapterListResponse)
async def get_chapters(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    series_id: Optional[int] = Query(None, description="Filter by series ID"),
    volume: Optional[Decimal] = Query(None, description="Filter by volume number"),
    read_status: Optional[bool] = Query(None, description="Filter by read status"),
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get paginated list of chapters with optional filtering.
    
    - **page**: Page number (starts from 1)
    - **size**: Number of items per page (max 100)
    - **series_id**: Filter by series ID
    - **volume**: Filter by volume number
    - **read_status**: Filter by read status (true/false)
    """
    try:
        return await chapter_service.get_chapters_paginated(
            page=page,
            size=size,
            series_id=series_id,
            volume=volume,
            read_status=read_status,
        )
    except ValueError as e:
        logger.warning(f"Invalid request in get_chapters: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_chapters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving chapters"
        )


@router.post("/", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    request: Request,
    chapter_data: ChapterCreate,
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Create a new chapter.
    
    - **series_id**: ID of the parent series (required)
    - **number**: Chapter number (required)
    - **title**: Chapter title (optional)
    - **file_path**: Path to chapter file (required)
    - **volume**: Volume number (optional)
    - **description**: Chapter description (optional)
    - **release_date**: Chapter release date (optional)
    - **page_count**: Number of pages (optional)
    - **file_size**: File size in bytes (optional)
    - **metadata_json**: Additional metadata as JSON (optional)
    """
    try:
        chapter = await chapter_service.create_chapter(
            chapter_data=chapter_data,
            user_id=str(current_user.id),
        )
        return ChapterResponse.model_validate(chapter)
    except ValueError as e:
        logger.warning(f"Invalid request in create_chapter: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_chapter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the chapter"
        )


@router.get("/{chapter_id}", response_model=ChapterWithSeriesResponse)
async def get_chapter_by_id(
    request: Request,
    chapter_id: int,
    include_series: bool = Query(False, description="Include series information"),
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get a chapter by ID.
    
    - **chapter_id**: The ID of the chapter to retrieve
    - **include_series**: Whether to include parent series information
    """
    chapter = await chapter_service.get_chapter_by_id(
        chapter_id=chapter_id,
        include_series=include_series,
    )
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter with ID {chapter_id} not found"
        )
    
    if include_series:
        return ChapterWithSeriesResponse.model_validate(chapter)
    else:
        return ChapterResponse.model_validate(chapter)


@router.patch("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    request: Request,
    chapter_id: int,
    chapter_data: ChapterUpdate,
    preview: bool = Query(False, description="Preview changes without saving"),
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Update a chapter.
    
    - **chapter_id**: The ID of the chapter to update
    - **preview**: If true, returns preview of changes without saving
    - All fields are optional and will only be updated if provided
    """
    try:
        updated_chapter = await chapter_service.update_chapter(
            chapter_id=chapter_id,
            update_data=chapter_data,
            user_id=str(current_user.id),
            preview_mode=preview,
        )
        
        if not updated_chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chapter with ID {chapter_id} not found"
            )
        
        # If in preview mode, return the preview data
        if preview and isinstance(updated_chapter, dict):
            return updated_chapter
        
        return ChapterResponse.model_validate(updated_chapter)
    except ValueError as e:
        logger.warning(f"Invalid request in update_chapter: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in update_chapter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the chapter"
        )


@router.patch("/bulk", response_model=List[ChapterResponse])
async def bulk_update_chapters(
    request: Request,
    bulk_data: BulkChapterUpdate,
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(bulk_rate_limit),
):
    """
    Update multiple chapters with the same data.
    
    - **chapter_ids**: List of chapter IDs to update (max 100)
    - **updates**: Updates to apply to all chapters
    """
    try:
        updated_chapters = await chapter_service.bulk_update_chapters(
            bulk_data=bulk_data,
            user_id=str(current_user.id),
        )
        
        return [ChapterResponse.model_validate(ch) for ch in updated_chapters]
    except ValueError as e:
        logger.warning(f"Invalid request in bulk_update_chapters: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in bulk_update_chapters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while bulk updating chapters"
        )


@router.delete("/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    request: Request,
    chapter_id: int,
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Delete a chapter.
    
    - **chapter_id**: The ID of the chapter to delete
    """
    try:
        success = await chapter_service.delete_chapter(
            chapter_id=chapter_id,
            user_id=str(current_user.id),
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chapter with ID {chapter_id} not found"
            )
    except ValueError as e:
        logger.warning(f"Invalid request in delete_chapter: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in delete_chapter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the chapter"
        )


@router.get("/{chapter_id}/history", response_model=List[MetadataHistoryWithUserResponse])
async def get_chapter_history(
    request: Request,
    chapter_id: int,
    limit: int = Query(50, ge=1, le=100, description="Number of history entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get change history for a chapter.
    
    - **chapter_id**: The ID of the chapter
    - **limit**: Number of history entries to return (max 100)
    - **offset**: Number of entries to skip for pagination
    """
    try:
        history = await chapter_service.get_chapter_history(
            chapter_id=chapter_id,
            limit=limit,
            offset=offset,
        )
        return [MetadataHistoryWithUserResponse.model_validate(entry) for entry in history]
    except Exception as e:
        logger.error(f"Unexpected error in get_chapter_history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving chapter history"
        )


@router.post("/{chapter_id}/restore/{history_id}", response_model=ChapterResponse)
async def restore_chapter_from_history(
    request: Request,
    chapter_id: int,
    history_id: int,
    current_user = Depends(current_active_user),
    chapter_service: ChapterService = Depends(get_chapter_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Restore a chapter to a previous state from history.
    
    - **chapter_id**: The ID of the chapter to restore
    - **history_id**: The ID of the history entry to restore from
    """
    try:
        restored_chapter = await chapter_service.restore_chapter_from_history(
            chapter_id=chapter_id,
            history_id=history_id,
            user_id=str(current_user.id),
        )
        
        if not restored_chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chapter with ID {chapter_id} or history entry {history_id} not found"
            )
        
        return ChapterResponse.model_validate(restored_chapter)
    except ValueError as e:
        logger.warning(f"Invalid request in restore_chapter_from_history: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in restore_chapter_from_history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while restoring the chapter"
        )