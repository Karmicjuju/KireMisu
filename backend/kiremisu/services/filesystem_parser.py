"""Filesystem parser utility for extracting manga series and chapter information.

This module provides comprehensive parsing of various manga file formats and directory
structures to extract metadata and organize series/chapter information for import into
the KireMisu database.

Supported formats:
- CBZ (zip archives)
- CBR (rar archives)
- PDF files
- Folder structures with images

The parser follows async patterns for I/O operations and uses ThreadPoolExecutor
for CPU-bound file processing operations.
"""

import asyncio
import logging
import os
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import fitz  # PyMuPDF
import rarfile
import structlog
from PIL import Image

logger = structlog.get_logger(__name__)

# Supported image formats for manga pages
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}

# Supported archive formats
SUPPORTED_ARCHIVE_FORMATS = {".cbz", ".zip", ".cbr", ".rar"}

# Supported document formats
SUPPORTED_DOCUMENT_FORMATS = {".pdf"}

# All supported file formats
ALL_SUPPORTED_FORMATS = (
    SUPPORTED_IMAGE_FORMATS | SUPPORTED_ARCHIVE_FORMATS | SUPPORTED_DOCUMENT_FORMATS
)


@dataclass
class ChapterInfo:
    """Information about a parsed chapter."""

    file_path: str
    chapter_number: float
    volume_number: Optional[int] = None
    title: Optional[str] = None
    file_size: int = 0
    page_count: int = 0

    # Metadata from parsing
    source_metadata: Dict = field(default_factory=dict)


@dataclass
class SeriesInfo:
    """Information about a parsed series."""

    title_primary: str
    file_path: str
    chapters: List[ChapterInfo] = field(default_factory=list)

    # Optional metadata
    title_alternative: Optional[str] = None
    author: Optional[str] = None
    artist: Optional[str] = None
    description: Optional[str] = None
    cover_image_path: Optional[str] = None

    # Metadata from parsing
    source_metadata: Dict = field(default_factory=dict)

    @property
    def total_chapters(self) -> int:
        """Get total chapter count."""
        return len(self.chapters)


class FilesystemParser:
    """Main parser class for extracting manga information from filesystem."""

    def __init__(self, max_cpu_workers: int = 2, max_io_workers: int = 4):
        """Initialize parser with thread pool configuration.

        Args:
            max_cpu_workers: Max workers for CPU-bound operations (conservative)
            max_io_workers: Max workers for I/O-bound operations (more aggressive)
        """
        self.cpu_pool = ThreadPoolExecutor(max_workers=max_cpu_workers)
        self.io_pool = ThreadPoolExecutor(max_workers=max_io_workers)

        # Compile regex patterns for chapter/volume parsing
        self._compile_regex_patterns()

    def _compile_regex_patterns(self) -> None:
        """Compile regex patterns for parsing chapter/volume numbers."""
        # Common patterns for chapter numbers (including fractional)
        self.chapter_patterns = [
            # "Chapter 01", "Ch 1.5", "Ch. 12", etc.
            re.compile(r"(?:chapter|ch\.?)\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
            # "c001", "c01.5", etc.
            re.compile(r"c(\d+(?:\.\d+)?)", re.IGNORECASE),
            # Just numbers at end "- 01", "_12.5", etc.
            re.compile(r"[_\-\s](\d+(?:\.\d+)?)(?:\s*$|\s*\.)"),
            # Numbers at start "01 -", "1.5_", etc.
            re.compile(r"^(\d+(?:\.\d+)?)[_\-\s]"),
        ]

        # Patterns for volume numbers
        self.volume_patterns = [
            # "Volume 01", "Vol 2", "V03", etc.
            re.compile(r"(?:volume|vol\.?|v)\s*(\d+)", re.IGNORECASE),
        ]

    async def scan_library_path(self, path: str) -> List[SeriesInfo]:
        """Scan a library path and extract all series information.

        Args:
            path: Root path to scan for manga series

        Returns:
            List of SeriesInfo objects found in the path

        Raises:
            ValueError: If path doesn't exist or isn't accessible
        """
        operation_logger = logger.bind(operation_type="library_scan", library_path=path)

        if not os.path.exists(path):
            raise ValueError(f"Library path does not exist: {path}")

        if not os.path.isdir(path):
            raise ValueError(f"Library path is not a directory: {path}")

        if not os.access(path, os.R_OK):
            raise ValueError(f"Library path is not readable: {path}")

        operation_logger.info("Starting library scan")

        series_list = []
        path_obj = Path(path)

        # Find potential series directories and files
        series_candidates = await self._find_series_candidates(path_obj)

        operation_logger.info("Found series candidates", count=len(series_candidates))

        # Process each series candidate
        for series_path in series_candidates:
            try:
                series_info = await self.parse_series(str(series_path))
                if series_info and series_info.chapters:
                    series_list.append(series_info)
                    operation_logger.debug(
                        "Parsed series successfully",
                        series_title=series_info.title_primary,
                        chapter_count=len(series_info.chapters),
                    )
            except Exception as e:
                operation_logger.warning(
                    "Failed to parse series", series_path=str(series_path), error=str(e)
                )
                continue

        operation_logger.info(
            "Library scan completed",
            series_found=len(series_list),
            total_chapters=sum(len(s.chapters) for s in series_list),
        )

        return series_list

    async def _find_series_candidates(self, root_path: Path) -> List[Path]:
        """Find potential series directories and files in the root path."""
        candidates = []

        def _scan_directory(directory: Path) -> List[Path]:
            """Synchronous directory scanning for thread pool."""
            local_candidates = []

            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        # Check if directory contains manga files
                        has_manga_files = any(
                            f.suffix.lower() in ALL_SUPPORTED_FORMATS
                            for f in item.iterdir()
                            if f.is_file()
                        )
                        if has_manga_files:
                            local_candidates.append(item)
                    elif (
                        item.is_file()
                        and item.suffix.lower()
                        in SUPPORTED_ARCHIVE_FORMATS | SUPPORTED_DOCUMENT_FORMATS
                    ):
                        # Individual archive/PDF files can be series
                        local_candidates.append(item)
            except (PermissionError, OSError):
                # Skip inaccessible directories
                pass

            return local_candidates

        # Use I/O thread pool for directory scanning
        loop = asyncio.get_event_loop()
        candidates = await loop.run_in_executor(self.io_pool, _scan_directory, root_path)

        return candidates

    async def parse_series(self, series_path: str) -> Optional[SeriesInfo]:
        """Parse a series from a directory or file path.

        Args:
            series_path: Path to series directory or file

        Returns:
            SeriesInfo object if successfully parsed, None otherwise
        """
        operation_logger = logger.bind(operation_type="series_parsing", series_path=series_path)

        path_obj = Path(series_path)

        if not path_obj.exists():
            operation_logger.warning("Series path does not exist")
            return None

        operation_logger.info("Starting series parsing")

        # Initialize series info with path-derived title
        series_info = SeriesInfo(
            title_primary=self._extract_series_title(path_obj.name), file_path=series_path
        )

        if path_obj.is_file():
            # Single file series (archive or PDF)
            chapter_info = await self.parse_chapter(series_path)
            if chapter_info:
                series_info.chapters.append(chapter_info)
        elif path_obj.is_dir():
            # Directory-based series
            chapters = await self._parse_directory_chapters(path_obj)
            series_info.chapters.extend(chapters)

            # Look for cover image
            cover_path = await self._find_cover_image(path_obj)
            if cover_path:
                series_info.cover_image_path = str(cover_path)

        # Sort chapters by volume and chapter number
        series_info.chapters.sort(key=lambda c: (c.volume_number or 0, c.chapter_number))

        operation_logger.info(
            "Series parsing completed",
            title=series_info.title_primary,
            chapter_count=len(series_info.chapters),
        )

        return series_info if series_info.chapters else None

    async def _parse_directory_chapters(self, directory: Path) -> List[ChapterInfo]:
        """Parse all chapters from a directory."""
        chapters = []

        def _scan_chapter_files(dir_path: Path) -> List[Path]:
            """Find all potential chapter files in directory."""
            chapter_files = []

            try:
                for item in dir_path.iterdir():
                    if item.is_file():
                        suffix = item.suffix.lower()
                        if suffix in SUPPORTED_ARCHIVE_FORMATS | SUPPORTED_DOCUMENT_FORMATS:
                            chapter_files.append(item)
                        elif suffix in SUPPORTED_IMAGE_FORMATS:
                            # For loose image files, group them by containing directory
                            chapter_files.append(item.parent)
                    elif item.is_dir():
                        # Check if subdirectory contains images (chapter folder)
                        has_images = any(
                            f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
                            for f in item.iterdir()
                            if f.is_file()
                        )
                        if has_images:
                            chapter_files.append(item)
            except (PermissionError, OSError):
                pass

            # Remove duplicates and return unique paths
            return list(set(chapter_files))

        # Use I/O thread pool for file scanning
        loop = asyncio.get_event_loop()
        chapter_files = await loop.run_in_executor(self.io_pool, _scan_chapter_files, directory)

        # Parse each chapter file/directory
        for chapter_path in chapter_files:
            try:
                chapter_info = await self.parse_chapter(str(chapter_path))
                if chapter_info:
                    chapters.append(chapter_info)
            except Exception as e:
                logger.warning(
                    "Failed to parse chapter", chapter_path=str(chapter_path), error=str(e)
                )
                continue

        return chapters

    async def parse_chapter(self, file_path: str) -> Optional[ChapterInfo]:
        """Parse chapter information from a file or directory.

        Args:
            file_path: Path to chapter file or directory

        Returns:
            ChapterInfo object if successfully parsed, None otherwise
        """
        operation_logger = logger.bind(operation_type="chapter_parsing", chapter_path=file_path)

        path_obj = Path(file_path)

        if not path_obj.exists():
            operation_logger.warning("Chapter path does not exist")
            return None

        operation_logger.debug("Starting chapter parsing")

        # Extract chapter and volume numbers from filename/directory name
        chapter_number, volume_number = self._extract_chapter_volume_numbers(path_obj.name)

        if chapter_number is None:
            operation_logger.warning("Could not extract chapter number")
            return None

        # Initialize chapter info
        chapter_info = ChapterInfo(
            file_path=file_path,
            chapter_number=chapter_number,
            volume_number=volume_number,
            title=self._extract_chapter_title(path_obj.name),
        )

        # Get file size and page count based on type
        if path_obj.is_file():
            chapter_info.file_size = path_obj.stat().st_size

            suffix = path_obj.suffix.lower()
            if suffix in {".cbz", ".zip"}:
                chapter_info.page_count = await self._count_pages_in_zip(path_obj)
            elif suffix in {".cbr", ".rar"}:
                chapter_info.page_count = await self._count_pages_in_rar(path_obj)
            elif suffix == ".pdf":
                chapter_info.page_count = await self._count_pages_in_pdf(path_obj)

        elif path_obj.is_dir():
            # Directory with loose images
            chapter_info.file_size = await self._calculate_directory_size(path_obj)
            chapter_info.page_count = await self._count_images_in_directory(path_obj)

        operation_logger.debug(
            "Chapter parsing completed",
            chapter_number=chapter_info.chapter_number,
            volume_number=chapter_info.volume_number,
            page_count=chapter_info.page_count,
        )

        return chapter_info

    def _extract_series_title(self, name: str) -> str:
        """Extract series title from directory/file name."""
        # Remove common file extensions
        title = name
        for ext in ALL_SUPPORTED_FORMATS:
            if title.lower().endswith(ext):
                title = title[: -len(ext)]
                break

        # Clean up common separators and formatting
        title = re.sub(r"[_\-\.]+", " ", title)
        title = re.sub(r"\s+", " ", title).strip()

        # Remove trailing volume/chapter indicators
        title = re.sub(r"\s+(?:vol|volume|ch|chapter)\s*\d+.*$", "", title, flags=re.IGNORECASE)

        return title or "Unknown Series"

    def _extract_chapter_title(self, name: str) -> Optional[str]:
        """Extract chapter title from filename, if present."""
        # Look for patterns like "Chapter 01 - Title" or "01 - Title"
        patterns = [
            r"(?:chapter|ch\.?)\s*\d+(?:\.\d+)?\s*[_\-]\s*(.+)",
            r"\d+(?:\.\d+)?\s*[_\-]\s*(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                title = match.group(1)
                # Clean up and remove file extension
                title = re.sub(r"\.[^.]+$", "", title)
                title = re.sub(r"[_\-\.]+", " ", title)
                title = re.sub(r"\s+", " ", title).strip()
                return title if title else None

        return None

    def _extract_chapter_volume_numbers(self, name: str) -> Tuple[Optional[float], Optional[int]]:
        """Extract chapter and volume numbers from filename."""
        chapter_number = None
        volume_number = None

        # Try to extract volume number first
        for pattern in self.volume_patterns:
            match = pattern.search(name)
            if match:
                try:
                    volume_number = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Try to extract chapter number
        for pattern in self.chapter_patterns:
            match = pattern.search(name)
            if match:
                try:
                    chapter_number = float(match.group(1))
                    break
                except ValueError:
                    continue

        # If no chapter number found, try to extract any number as chapter
        if chapter_number is None:
            number_match = re.search(r"(\d+(?:\.\d+)?)", name)
            if number_match:
                try:
                    chapter_number = float(number_match.group(1))
                except ValueError:
                    pass

        return chapter_number, volume_number

    async def _count_pages_in_zip(self, zip_path: Path) -> int:
        """Count image pages in a ZIP/CBZ file."""

        def _count_zip_images(path: Path) -> int:
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    return sum(
                        1
                        for name in zf.namelist()
                        if Path(name).suffix.lower() in SUPPORTED_IMAGE_FORMATS
                        and not name.startswith("__MACOSX/")
                        and not name.startswith(".DS_Store")
                    )
            except (zipfile.BadZipFile, PermissionError):
                return 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.cpu_pool, _count_zip_images, zip_path)

    async def _count_pages_in_rar(self, rar_path: Path) -> int:
        """Count image pages in a RAR/CBR file."""

        def _count_rar_images(path: Path) -> int:
            try:
                with rarfile.RarFile(path, "r") as rf:
                    return sum(
                        1
                        for info in rf.infolist()
                        if Path(info.filename).suffix.lower() in SUPPORTED_IMAGE_FORMATS
                        and not info.filename.startswith("__MACOSX/")
                        and not info.filename.startswith(".DS_Store")
                    )
            except (rarfile.Error, PermissionError):
                return 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.cpu_pool, _count_rar_images, rar_path)

    async def _count_pages_in_pdf(self, pdf_path: Path) -> int:
        """Count pages in a PDF file."""

        def _count_pdf_pages(path: Path) -> int:
            try:
                doc = fitz.open(str(path))
                page_count = doc.page_count
                doc.close()
                return page_count
            except Exception:
                return 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.cpu_pool, _count_pdf_pages, pdf_path)

    async def _count_images_in_directory(self, directory: Path) -> int:
        """Count image files in a directory."""

        def _count_directory_images(path: Path) -> int:
            try:
                return sum(
                    1
                    for f in path.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
                )
            except (PermissionError, OSError):
                return 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.io_pool, _count_directory_images, directory)

    async def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of files in directory."""

        def _calculate_size(path: Path) -> int:
            try:
                return sum(
                    f.stat().st_size
                    for f in path.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
                )
            except (PermissionError, OSError):
                return 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.io_pool, _calculate_size, directory)

    async def _find_cover_image(self, directory: Path) -> Optional[Path]:
        """Find cover image in series directory."""

        def _find_cover(path: Path) -> Optional[Path]:
            # Look for common cover image names
            cover_names = {
                "cover",
                "folder",
                "series",
                "poster",
                "thumbnail",
                "00",
                "000",
                "001",
                "cover.jpg",
                "cover.png",
            }

            try:
                for f in path.iterdir():
                    if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                        name_lower = f.stem.lower()
                        if any(cover_name in name_lower for cover_name in cover_names):
                            return f

                # If no explicit cover found, use first image alphabetically
                image_files = [
                    f
                    for f in path.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
                ]
                if image_files:
                    return sorted(image_files)[0]

            except (PermissionError, OSError):
                pass

            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.io_pool, _find_cover, directory)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup thread pools."""
        self.cpu_pool.shutdown(wait=True)
        self.io_pool.shutdown(wait=True)


# Convenience function for simple usage
async def parse_library_path(path: str) -> List[SeriesInfo]:
    """Convenience function to parse a library path.

    Args:
        path: Library path to scan

    Returns:
        List of SeriesInfo objects found
    """
    async with FilesystemParser() as parser:
        return await parser.scan_library_path(path)
