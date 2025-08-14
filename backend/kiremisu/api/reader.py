"""Reader API endpoints for chapter page streaming and reading progress."""

import asyncio
import logging
import mimetypes
import os
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from uuid import UUID

import fitz  # PyMuPDF
import rarfile
import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from kiremisu.database.connection import get_db
from kiremisu.core.unified_auth import get_current_user
from kiremisu.database.models import Chapter, Series
from kiremisu.database.schemas import ChapterProgressUpdate, ChapterProgressResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/reader", tags=["reader"])

# Thread pool for CPU-bound image operations
_thread_pool: Optional[ThreadPoolExecutor] = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Get or create thread pool for image processing."""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="reader-")
    return _thread_pool


def _extract_page_from_archive(
    archive_path: str, page_index: int, file_format: str
) -> Optional[bytes]:
    """Extract a specific page from archive file synchronously."""
    try:
        if file_format in {".cbz", ".zip"}:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Get list of image files, sorted
                image_files = sorted(
                    [
                        f
                        for f in zf.namelist()
                        if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"))
                    ]
                )

                if 0 <= page_index < len(image_files):
                    return zf.read(image_files[page_index])

        elif file_format in {".cbr", ".rar"}:
            with rarfile.RarFile(archive_path, "r") as rf:
                # Get list of image files, sorted
                image_files = sorted(
                    [
                        f
                        for f in rf.namelist()
                        if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"))
                    ]
                )

                if 0 <= page_index < len(image_files):
                    return rf.read(image_files[page_index])

    except Exception as e:
        logger.error(f"Error extracting page {page_index} from {archive_path}: {e}")

    return None


def _extract_page_from_pdf(pdf_path: str, page_index: int) -> Optional[bytes]:
    """Extract a specific page from PDF file synchronously."""
    try:
        doc = fitz.open(pdf_path)
        if 0 <= page_index < len(doc):
            page = doc.load_page(page_index)
            # Render page as PNG with high DPI for quality
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_data = pix.tobytes("png")
            doc.close()
            return img_data
    except Exception as e:
        logger.error(f"Error extracting page {page_index} from PDF {pdf_path}: {e}")
    return None


def _get_folder_page(folder_path: str, page_index: int) -> Optional[bytes]:
    """Get a specific page from folder structure synchronously."""
    try:
        # Get list of image files in folder, sorted
        image_files = []
        for f in os.listdir(folder_path):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
                image_files.append(f)

        image_files.sort()

        if 0 <= page_index < len(image_files):
            image_path = os.path.join(folder_path, image_files[page_index])
            with open(image_path, "rb") as img_file:
                return img_file.read()

    except Exception as e:
        logger.error(f"Error getting page {page_index} from folder {folder_path}: {e}")

    return None


async def _extract_chapter_page(chapter: Chapter, page_index: int) -> Optional[tuple[bytes, str]]:
    """Extract a specific page from chapter file."""
    file_path = chapter.file_path

    if not os.path.exists(file_path):
        logger.error(f"Chapter file not found: {file_path}")
        return None

    # Determine file type
    _, ext = os.path.splitext(file_path.lower())

    try:
        thread_pool = get_thread_pool()

        if ext in {".cbz", ".zip", ".cbr", ".rar"}:
            # Extract from archive
            image_data = await asyncio.get_event_loop().run_in_executor(
                thread_pool, _extract_page_from_archive, file_path, page_index, ext
            )
            if image_data:
                # Detect content type from image data
                content_type = "image/jpeg"  # Default
                if image_data.startswith(b"\x89PNG"):
                    content_type = "image/png"
                elif image_data.startswith(b"GIF"):
                    content_type = "image/gif"
                return image_data, content_type

        elif ext == ".pdf":
            # Extract from PDF
            image_data = await asyncio.get_event_loop().run_in_executor(
                thread_pool, _extract_page_from_pdf, file_path, page_index
            )
            if image_data:
                return image_data, "image/png"

        elif os.path.isdir(file_path):
            # Get from folder
            image_data = await asyncio.get_event_loop().run_in_executor(
                thread_pool, _get_folder_page, file_path, page_index
            )
            if image_data:
                # Detect content type
                content_type, _ = mimetypes.guess_type(f"image{os.path.splitext(file_path)[1]}")
                return image_data, content_type or "image/jpeg"

    except Exception as e:
        logger.error(f"Error extracting page {page_index} from chapter {chapter.id}: {e}")

    return None


@router.get("/chapter/{chapter_id}/page/{page_index}")
async def get_chapter_page(
    chapter_id: UUID, page_index: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)
) -> StreamingResponse:
    """Stream a specific page from a chapter.

    Args:
        chapter_id: UUID of the chapter
        page_index: Zero-based page index
        db: Database session

    Returns:
        StreamingResponse: Image data stream

    Raises:
        HTTPException: If chapter not found or page invalid
    """
    # Get chapter from database
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter not found: {chapter_id}"
        )

    # Validate page index
    if page_index < 0 or page_index >= chapter.page_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_index} not found. Chapter has {chapter.page_count} pages.",
        )

    # Extract page data
    page_data = await _extract_chapter_page(chapter, page_index)

    if not page_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract page {page_index} from chapter {chapter_id}",
        )

    image_data, content_type = page_data

    # Return streaming response
    def iter_image():
        yield image_data

    return StreamingResponse(
        iter_image(),
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "Content-Length": str(len(image_data)),
        },
    )


@router.get("/chapter/{chapter_id}/info")
async def get_chapter_info(chapter_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)) -> dict:
    """Get chapter information including reading progress.

    Args:
        chapter_id: UUID of the chapter
        db: Database session

    Returns:
        dict: Chapter information and progress
    """
    # Get chapter with series info
    result = await db.execute(
        select(Chapter, Series)
        .join(Series, Chapter.series_id == Series.id)
        .where(Chapter.id == chapter_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter not found: {chapter_id}"
        )

    chapter, series = row

    return {
        "id": str(chapter.id),
        "series_id": str(chapter.series_id),
        "series_title": series.title_primary,
        "chapter_number": chapter.chapter_number,
        "volume_number": chapter.volume_number,
        "title": chapter.title,
        "page_count": chapter.page_count,
        "is_read": chapter.is_read,
        "last_read_page": chapter.last_read_page,
        "read_at": chapter.read_at.isoformat() if chapter.read_at else None,
        "file_size": chapter.file_size,
        "created_at": chapter.created_at.isoformat(),
        "updated_at": chapter.updated_at.isoformat(),
    }


@router.put("/chapter/{chapter_id}/progress")
async def update_reading_progress(
    chapter_id: UUID, progress: ChapterProgressUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)
) -> ChapterProgressResponse:
    """Update reading progress for a chapter.

    Args:
        chapter_id: UUID of the chapter
        progress: Progress update data
        db: Database session

    Returns:
        ChapterProgressResponse: Updated progress information
    """
    # Get chapter
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter not found: {chapter_id}"
        )

    # Validate page number
    if progress.last_read_page < 0 or progress.last_read_page >= chapter.page_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid page number {progress.last_read_page}. Chapter has {chapter.page_count} pages.",
        )

    # Use the enhanced reading progress service for comprehensive tracking
    try:
        from kiremisu.services.reading_progress import ReadingProgressService
        from kiremisu.database.schemas import ReadingProgressUpdateRequest

        # Convert from ChapterProgressUpdate to ReadingProgressUpdateRequest
        progress_request = ReadingProgressUpdateRequest(
            current_page=progress.last_read_page, is_complete=progress.is_read
        )

        # Update progress using the enhanced service (this handles all the logic)
        await ReadingProgressService.update_chapter_progress(db, str(chapter_id), progress_request)

        # Get updated chapter
        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        updated_chapter = result.scalar_one()

    except ValueError as e:
        # Convert service errors to appropriate HTTP exceptions
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ChapterProgressResponse.from_model(updated_chapter)


@router.get("/series/{series_id}/chapters")
async def get_series_chapters(series_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)) -> dict:
    """Get all chapters for a series with reading progress.

    Args:
        series_id: UUID of the series
        db: Database session

    Returns:
        dict: Series info and chapters list
    """
    # Get series
    result = await db.execute(select(Series).where(Series.id == series_id))
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Series not found: {series_id}"
        )

    # Get chapters ordered by volume and chapter number
    result = await db.execute(
        select(Chapter)
        .where(Chapter.series_id == series_id)
        .order_by(Chapter.volume_number.asc().nulls_first(), Chapter.chapter_number.asc())
    )
    chapters = result.scalars().all()

    return {
        "series": {
            "id": str(series.id),
            "title": series.title_primary,
            "total_chapters": series.total_chapters,
            "read_chapters": series.read_chapters,
        },
        "chapters": [
            {
                "id": str(chapter.id),
                "chapter_number": chapter.chapter_number,
                "volume_number": chapter.volume_number,
                "title": chapter.title,
                "page_count": chapter.page_count,
                "is_read": chapter.is_read,
                "last_read_page": chapter.last_read_page,
                "read_at": chapter.read_at.isoformat() if chapter.read_at else None,
                "started_reading_at": getattr(chapter, "started_reading_at", None).isoformat()
                if getattr(chapter, "started_reading_at", None)
                else None,
            }
            for chapter in chapters
        ],
    }
