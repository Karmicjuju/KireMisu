"""API endpoints for manga reader functionality."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.database import get_async_session
from app.users import current_active_user
from app.models.user import User
from app.core.rate_limit import create_rate_limit_dependency
from app.schemas.reader import (
    ChapterPagesResponse,
    ReadingProgressUpdate,
    ReadingProgressResponse,
    ChapterNavigationResponse,
    PageNavigationRequest,
    PageNavigationResponse,
    ChapterInfoResponse,
    ErrorResponse
)
from app.services.reader import ReaderService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize reader service
reader_service = ReaderService()

# Rate limiting dependencies
reader_rate_limit = create_rate_limit_dependency(max_requests=200, window_seconds=3600)  # 200 requests per hour
image_rate_limit = create_rate_limit_dependency(max_requests=500, window_seconds=3600)   # 500 image requests per hour
progress_rate_limit = create_rate_limit_dependency(max_requests=100, window_seconds=3600) # 100 progress updates per hour


@router.get("/chapters/{chapter_id}/pages", response_model=ChapterPagesResponse)
async def get_chapter_pages(
    request: Request,
    chapter_id: int,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(reader_rate_limit)
):
    """
    Get list of pages for a chapter with reading progress.
    
    Args:
        chapter_id: ID of the chapter to retrieve pages for
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Chapter pages information including reading progress
        
    Raises:
        HTTPException: If chapter not found or access denied
    """
    try:
        result = await reader_service.get_chapter_pages(chapter_id, db, current_user.id)
        return ChapterPagesResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chapter pages for chapter {chapter_id}", exc_info=False)
        logger.debug(f"Chapter pages error details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load chapter pages")


@router.get("/chapters/{chapter_id}/pages/{page_filename}")
async def get_page_image(
    request: Request,
    chapter_id: int,
    page_filename: str,
    max_width: Optional[int] = Query(None, ge=100, le=4000, description="Maximum width for resizing"),
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(image_rate_limit)
):
    """
    Get image data for a specific page.
    
    Args:
        chapter_id: ID of the chapter
        page_filename: Filename of the page to retrieve
        max_width: Optional maximum width for resizing
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Image data as streaming response
        
    Raises:
        HTTPException: If chapter/page not found or access denied
    """
    try:
        # Get image data from reader service
        image_data, content_type = await reader_service.get_page_image(
            chapter_id, page_filename, db, current_user.id, max_width
        )
        
        # Create streaming response
        image_stream = io.BytesIO(image_data)
        
        return StreamingResponse(
            io.BytesIO(image_data),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Length": str(len(image_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page image from chapter {chapter_id}", exc_info=False)
        logger.debug(f"Page image error details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load image")


@router.post("/chapters/{chapter_id}/progress", response_model=ReadingProgressResponse)
async def update_reading_progress(
    request: Request,
    chapter_id: int,
    progress_update: ReadingProgressUpdate,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(progress_rate_limit)
):
    """
    Update user's reading progress for a chapter.
    
    Args:
        chapter_id: ID of the chapter
        progress_update: Reading progress update data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated reading progress information
        
    Raises:
        HTTPException: If chapter not found or invalid page number
    """
    try:
        # Update reading progress
        progress = await reader_service.update_reading_progress(
            chapter_id, progress_update.page_number, db, current_user.id
        )
        
        # Start preloading next pages asynchronously
        await reader_service.preload_pages(
            chapter_id, progress_update.page_number, db, current_user.id
        )
        
        return ReadingProgressResponse(
            chapter_id=progress.chapter_id,
            current_page=progress.current_page,
            total_pages=progress.total_pages,
            is_completed=progress.is_completed,
            last_read=progress.last_read
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reading progress for chapter {chapter_id}", exc_info=False)
        logger.debug(f"Reading progress error details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to update reading progress")


@router.get("/chapters/{chapter_id}/navigation", response_model=ChapterNavigationResponse)
async def get_chapter_navigation(
    request: Request,
    chapter_id: int,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(reader_rate_limit)
):
    """
    Get navigation information for a chapter (previous/next chapters).
    
    Args:
        chapter_id: ID of the current chapter
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Chapter navigation information
        
    Raises:
        HTTPException: If chapter not found
    """
    try:
        result = await reader_service.get_chapter_navigation(chapter_id, db, current_user.id)
        return ChapterNavigationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chapter navigation for {chapter_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load navigation information")


@router.post("/chapters/{chapter_id}/navigate", response_model=PageNavigationResponse)
async def navigate_pages(
    request: Request,
    chapter_id: int,
    navigation: PageNavigationRequest,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(reader_rate_limit)
):
    """
    Navigate between pages with boundary handling.
    
    Args:
        chapter_id: ID of the current chapter
        navigation: Navigation request data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Navigation result with new page information
        
    Raises:
        HTTPException: If chapter not found or invalid navigation
    """
    try:
        # Get chapter pages
        chapter_info = await reader_service.get_chapter_pages(chapter_id, db, current_user.id)
        pages = chapter_info['pages']
        current_page = navigation.current_page
        
        # Calculate new page based on direction
        new_page = current_page
        is_boundary = False
        next_chapter_id = None
        message = None
        
        if navigation.direction == "next":
            if current_page < len(pages) - 1:
                new_page = current_page + 1
            else:
                # End of chapter - check for next chapter
                nav_info = await reader_service.get_chapter_navigation(chapter_id, db, current_user.id)
                if nav_info['next_chapter']:
                    is_boundary = True
                    next_chapter_id = nav_info['next_chapter']['id']
                    message = f"End of chapter. Next: {nav_info['next_chapter']['title']}"
                else:
                    message = "End of series"
                    
        elif navigation.direction == "prev":
            if current_page > 0:
                new_page = current_page - 1
            else:
                # Beginning of chapter - check for previous chapter
                nav_info = await reader_service.get_chapter_navigation(chapter_id, db, current_user.id)
                if nav_info['previous_chapter']:
                    is_boundary = True
                    next_chapter_id = nav_info['previous_chapter']['id']
                    message = f"Beginning of chapter. Previous: {nav_info['previous_chapter']['title']}"
                else:
                    message = "Beginning of series"
                    
        elif navigation.direction == "first":
            new_page = 0
            
        elif navigation.direction == "last":
            new_page = len(pages) - 1
            
        else:
            raise HTTPException(status_code=400, detail="Invalid navigation direction")
        
        # Get page filename for new page
        page_filename = pages[new_page] if 0 <= new_page < len(pages) else pages[current_page]
        
        # Update reading progress if page changed
        if new_page != current_page and not is_boundary:
            await reader_service.update_reading_progress(chapter_id, new_page, db, current_user.id)
        
        return PageNavigationResponse(
            new_page=new_page,
            page_filename=page_filename,
            is_chapter_boundary=is_boundary,
            next_chapter_id=next_chapter_id,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error navigating pages for chapter {chapter_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to navigate pages")


@router.get("/chapters/{chapter_id}/info", response_model=ChapterInfoResponse)
async def get_chapter_info(
    request: Request,
    chapter_id: int,
    db: Session = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(reader_rate_limit)
):
    """
    Get detailed information about a chapter file.
    
    Args:
        chapter_id: ID of the chapter
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Chapter information including format and metadata
        
    Raises:
        HTTPException: If chapter not found
    """
    try:
        # Get chapter from database
        from app.models.chapter import Chapter
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Get chapter info from extractor
        info = reader_service.extractor.get_chapter_info(chapter.file_path)
        
        return ChapterInfoResponse(
            chapter_id=chapter_id,
            format=info['format'],
            page_count=info['page_count'],
            file_size=info['file_size'],
            pages=info['pages'],
            is_valid=info['is_valid'],
            metadata=info['metadata']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chapter info for {chapter_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load chapter information")


@router.post("/cache/clear")
async def clear_reader_cache(
    request: Request,
    current_user: User = Depends(current_active_user),
    _rate_limit = Depends(reader_rate_limit)
):
    """
    Clear the reader image cache.
    
    Args:
        current_user: Authenticated user (admin access could be required)
        
    Returns:
        Success message
    """
    try:
        reader_service.clear_cache()
        return {"message": "Reader cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing reader cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to clear cache")


@router.get("/health")
async def reader_health_check():
    """
    Health check endpoint for reader service.
    
    Returns:
        Health status information
    """
    try:
        cache_size = reader_service.image_cache.current_size / (1024 * 1024)  # MB
        cache_entries = len(reader_service.image_cache.cache)
        progress_entries = len(reader_service.progress_cache)
        
        return {
            "status": "healthy",
            "service": "reader",
            "cache": {
                "size_mb": round(cache_size, 2),
                "entries": cache_entries,
                "max_size_mb": reader_service.image_cache.max_size_bytes / (1024 * 1024)
            },
            "progress_tracking": {
                "active_sessions": progress_entries
            }
        }
        
    except Exception as e:
        logger.error(f"Error in reader health check: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "reader",
            "error": "Health check failed"
        }