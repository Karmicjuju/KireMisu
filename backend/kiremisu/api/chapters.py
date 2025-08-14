"""API endpoints for manga chapters and pages."""

import asyncio
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Iterator
from uuid import UUID

import fitz  # PyMuPDF
import rarfile
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from kiremisu.database.connection import get_db
from kiremisu.core.unified_auth import get_current_user
from kiremisu.database.models import Chapter, Series
from kiremisu.database.schemas import (
    ChapterResponse,
    SeriesResponse,
    ChapterPagesInfoResponse,
    PageInfoResponse,
    ChapterMarkReadResponse,
)

logger = structlog.get_logger(__name__)

# Thread pool for CPU-bound file operations
_cpu_pool = ThreadPoolExecutor(max_workers=2)

# Supported image formats
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> ChapterResponse:
    """Get chapter details by ID."""
    result = await db.execute(
        select(Chapter).options(selectinload(Chapter.series)).where(Chapter.id == chapter_id)
    )
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return ChapterResponse.from_model(chapter)


@router.get("/{chapter_id}/pages/{page_number}")
async def get_chapter_page(chapter_id: UUID, page_number: int, db: AsyncSession = Depends(get_db)):
    """Stream a specific page from a chapter."""
    # Get chapter from database
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Validate page number
    if page_number < 1 or page_number > chapter.page_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not found. Chapter has {chapter.page_count} pages.",
        )

    chapter_path = Path(chapter.file_path)

    # Security: Validate that the file path is within expected bounds
    try:
        # Resolve the path to prevent directory traversal attacks
        resolved_path = chapter_path.resolve()
        if not resolved_path.exists():
            logger.warning(
                "Chapter file not found", chapter_id=str(chapter_id), file_path=str(resolved_path)
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chapter file not found"
            )

        # Additional security check: ensure path doesn't contain suspicious patterns
        path_str = str(resolved_path)
        if ".." in path_str or path_str.startswith("/etc") or path_str.startswith("/usr"):
            logger.error(
                "Potential directory traversal attempt",
                chapter_id=str(chapter_id),
                file_path=path_str,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        chapter_path = resolved_path
    except (OSError, ValueError) as e:
        logger.error("Invalid chapter file path", chapter_id=str(chapter_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter file not found")

    try:
        # Handle different file types
        if chapter_path.is_dir():
            # Directory with loose image files
            page_image = await _get_page_from_directory_async(chapter_path, page_number)
        elif chapter_path.suffix.lower() in [".cbz", ".zip"]:
            # CBZ/ZIP archive
            page_image = await _get_page_from_zip_async(chapter_path, page_number)
        elif chapter_path.suffix.lower() in [".cbr", ".rar"]:
            # CBR/RAR archive
            page_image = await _get_page_from_rar_async(chapter_path, page_number)
        elif chapter_path.suffix.lower() == ".pdf":
            # PDF file
            page_image = await _get_page_from_pdf_async(chapter_path, page_number)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported chapter format"
            )

        if not page_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Page image not found"
            )

        # Determine content type based on file extension
        content_type = _get_content_type(page_image["filename"])

        # Return streaming response with additional security headers
        return StreamingResponse(
            page_image["data"],
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{page_image["filename"]}"',
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "X-Content-Type-Options": "nosniff",  # Prevent MIME type sniffing
                "X-Frame-Options": "SAMEORIGIN",  # Prevent clickjacking
            },
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(
            "Unexpected error reading page",
            chapter_id=str(chapter_id),
            page_number=page_number,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error reading page"
        )


@router.get("/{chapter_id}/pages", response_model=ChapterPagesInfoResponse)
async def get_chapter_pages_info(
    chapter_id: UUID, db: AsyncSession = Depends(get_db)
) -> ChapterPagesInfoResponse:
    """Get information about all pages in a chapter."""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return ChapterPagesInfoResponse(
        chapter_id=chapter_id,
        total_pages=chapter.page_count,
        pages=[
            PageInfoResponse(page_number=i, url=f"/api/chapters/{chapter_id}/pages/{i}")
            for i in range(1, chapter.page_count + 1)
        ],
    )


async def _get_page_from_directory_async(chapter_path: Path, page_number: int) -> Optional[dict]:
    """Get page image from a directory of loose files."""

    def _scan_directory(path: Path) -> List[Path]:
        """Scan directory for image files."""
        image_files = []
        try:
            for file_path in path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                    image_files.append(file_path)
        except (PermissionError, OSError):
            return []

        # Sort files naturally (handling numeric sorting)
        image_files.sort(key=lambda x: _natural_sort_key(x.name))
        return image_files

    # Use thread pool for I/O operation
    loop = asyncio.get_event_loop()
    image_files = await loop.run_in_executor(_cpu_pool, _scan_directory, chapter_path)

    if page_number > len(image_files) or not image_files:
        return None

    target_file = image_files[page_number - 1]

    def file_generator() -> Iterator[bytes]:
        try:
            with open(target_file, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        except (IOError, OSError) as e:
            logger.error("Error reading image file", file_path=str(target_file), error=str(e))
            return

    return {"filename": target_file.name, "data": file_generator()}


async def _get_page_from_zip_async(archive_path: Path, page_number: int) -> Optional[dict]:
    """Get page image from a CBZ/ZIP archive."""

    def _extract_zip_page(path: Path, page_num: int) -> Optional[dict]:
        """Extract page from ZIP archive."""
        try:
            with zipfile.ZipFile(path, "r") as zf:
                # Get all image files from the archive
                image_files = []

                for filename in zf.namelist():
                    # Check if it's an image file
                    if Path(filename).suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                        # Skip system files and directories
                        if not filename.startswith("__MACOSX/") and not filename.startswith(
                            ".DS_Store"
                        ):
                            image_files.append(filename)

                # Sort files naturally
                image_files.sort(key=_natural_sort_key)

                if page_num > len(image_files) or not image_files:
                    return None

                target_file = image_files[page_num - 1]

                def file_generator() -> Iterator[bytes]:
                    try:
                        with zipfile.ZipFile(path, "r") as inner_zf:
                            with inner_zf.open(target_file) as f:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    yield chunk
                    except (zipfile.BadZipFile, KeyError, IOError) as e:
                        logger.error(
                            "Error reading from ZIP archive",
                            archive_path=str(path),
                            target_file=target_file,
                            error=str(e),
                        )
                        return

                return {"filename": os.path.basename(target_file), "data": file_generator()}

        except (zipfile.BadZipFile, IOError, OSError):
            return None

    # Use thread pool for CPU-bound operation
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_cpu_pool, _extract_zip_page, archive_path, page_number)


async def _get_page_from_rar_async(archive_path: Path, page_number: int) -> Optional[dict]:
    """Get page image from a CBR/RAR archive."""

    def _extract_rar_page(path: Path, page_num: int) -> Optional[dict]:
        """Extract page from RAR archive."""
        try:
            with rarfile.RarFile(path, "r") as rf:
                # Get all image files from the archive
                image_files = []

                for info in rf.infolist():
                    filename = info.filename
                    if Path(filename).suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                        # Skip system files and directories
                        if not filename.startswith("__MACOSX/") and not filename.startswith(
                            ".DS_Store"
                        ):
                            image_files.append(filename)

                # Sort files naturally
                image_files.sort(key=_natural_sort_key)

                if page_num > len(image_files) or not image_files:
                    return None

                target_file = image_files[page_num - 1]

                def file_generator() -> Iterator[bytes]:
                    try:
                        with rarfile.RarFile(path, "r") as inner_rf:
                            with inner_rf.open(target_file) as f:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    yield chunk
                    except (rarfile.Error, IOError) as e:
                        logger.error(
                            "Error reading from RAR archive",
                            archive_path=str(path),
                            target_file=target_file,
                            error=str(e),
                        )
                        return

                return {"filename": os.path.basename(target_file), "data": file_generator()}

        except (rarfile.Error, IOError, OSError):
            return None

    # Use thread pool for CPU-bound operation
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_cpu_pool, _extract_rar_page, archive_path, page_number)


async def _get_page_from_pdf_async(pdf_path: Path, page_number: int) -> Optional[dict]:
    """Get page image from a PDF file."""

    def _extract_pdf_page(path: Path, page_num: int) -> Optional[dict]:
        """Extract page from PDF as image."""
        try:
            doc = fitz.open(str(path))

            if page_num > doc.page_count or page_num < 1:
                doc.close()
                return None

            # Get the page (0-indexed in PyMuPDF)
            page = doc[page_num - 1]

            # Render page as image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)

            def file_generator() -> Iterator[bytes]:
                try:
                    # Convert to PNG bytes
                    png_data = pix.tobytes("png")
                    # Yield data in chunks
                    chunk_size = 8192
                    for i in range(0, len(png_data), chunk_size):
                        yield png_data[i : i + chunk_size]
                finally:
                    pix = None  # Free memory
                    doc.close()

            return {"filename": f"page_{page_num:03d}.png", "data": file_generator()}

        except Exception as e:
            logger.error(
                "Error extracting PDF page", pdf_path=str(path), page_number=page_num, error=str(e)
            )
            return None

    # Use thread pool for CPU-bound operation
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_cpu_pool, _extract_pdf_page, pdf_path, page_number)


def _natural_sort_key(filename: str) -> List:
    """Generate a natural sort key for filename sorting."""
    import re

    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    return [convert(c) for c in re.split(r"(\d+)", filename)]


def _get_content_type(filename: str) -> str:
    """Get content type based on file extension."""
    ext = Path(filename).suffix.lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    return content_types.get(ext, "application/octet-stream")


@router.get("/series/{series_id}/chapters", response_model=List[ChapterResponse])
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


@router.put("/{chapter_id}/mark-read", response_model=ChapterMarkReadResponse)
async def toggle_chapter_read_status(
    chapter_id: UUID, db: AsyncSession = Depends(get_db)
) -> ChapterMarkReadResponse:
    """Toggle chapter read status and update series aggregate."""
    from datetime import datetime

    # Get chapter with series relationship
    result = await db.execute(
        select(Chapter).options(selectinload(Chapter.series)).where(Chapter.id == chapter_id)
    )
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Toggle read status
    new_read_status = not chapter.is_read
    read_at_value = datetime.utcnow() if new_read_status else None

    # Update chapter read status
    await db.execute(
        update(Chapter)
        .where(Chapter.id == chapter_id)
        .values(
            is_read=new_read_status,
            read_at=read_at_value,
            updated_at=datetime.utcnow(),
        )
    )

    # Update series read_chapters count by recalculating from all chapters
    read_chapters_count = await db.execute(
        select(func.count()).where(Chapter.series_id == chapter.series_id, Chapter.is_read == True)
    )
    new_read_count = read_chapters_count.scalar()

    # Update series read_chapters and updated_at
    await db.execute(
        update(Series)
        .where(Series.id == chapter.series_id)
        .values(read_chapters=new_read_count, updated_at=datetime.utcnow())
    )

    # Commit the transaction
    await db.commit()

    logger.info(
        "Chapter read status toggled",
        chapter_id=str(chapter_id),
        series_id=str(chapter.series_id),
        new_status=new_read_status,
        new_series_read_count=new_read_count,
    )

    return ChapterMarkReadResponse(
        id=chapter_id,
        is_read=new_read_status,
        read_at=read_at_value,
        series_read_chapters=new_read_count,
    )
