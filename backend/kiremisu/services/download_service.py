"""Download service for manga chapters from external sources."""

import asyncio
import json
import logging
import os
import shutil
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, Series, Chapter, LibraryPath
from kiremisu.services.mangadx_client import MangaDxClient, MangaDxError

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised when download operation fails."""

    pass


class DownloadJobData:
    """Container for download job payload data."""

    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload

    @property
    def job_id(self) -> Optional[str]:
        """Get job ID from payload."""
        return self.payload.get("job_id")

    @property
    def download_type(self) -> str:
        """Get download type (mangadx, local, etc.)."""
        return self.payload.get("download_type", "mangadx")

    @property
    def manga_id(self) -> Optional[str]:
        """Get external manga ID."""
        return self.payload.get("manga_id")

    @property
    def series_id(self) -> Optional[str]:
        """Get local series ID."""
        return self.payload.get("series_id")

    @property
    def chapter_ids(self) -> List[str]:
        """Get list of chapter IDs to download."""
        return self.payload.get("chapter_ids", [])

    @property
    def batch_type(self) -> Optional[str]:
        """Get batch type (single, volume, series)."""
        return self.payload.get("batch_type")

    @property
    def volume_number(self) -> Optional[str]:
        """Get volume number for volume downloads."""
        return self.payload.get("volume_number")

    @property
    def destination_path(self) -> Optional[str]:
        """Get destination path for downloaded files."""
        return self.payload.get("destination_path")

    @property
    def progress_data(self) -> Dict[str, Any]:
        """Get progress tracking data."""
        return self.payload.get("progress", {})


class DownloadProgressTracker:
    """Tracks download progress for jobs."""

    def __init__(self, db: AsyncSession, job_id: UUID):
        self.db = db
        self.job_id = job_id
        self._progress = {
            "total_chapters": 0,
            "downloaded_chapters": 0,
            "current_chapter": None,
            "current_chapter_progress": 0.0,
            "error_count": 0,
            "errors": [],
            "started_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "estimated_completion": None,
        }

    async def initialize(self, total_chapters: int):
        """Initialize progress tracking."""
        self._progress["total_chapters"] = total_chapters
        await self._update_job_payload()

    async def start_chapter(self, chapter_id: str, chapter_title: str):
        """Start tracking a chapter download with atomic update."""
        # Update progress atomically to prevent race conditions
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

        self._progress["current_chapter"] = {
            "id": chapter_id,
            "title": chapter_title,
            "started_at": timestamp,
        }
        self._progress["current_chapter_progress"] = 0.0

        # Atomic database update
        await self._update_job_payload()

    async def update_chapter_progress(self, progress: float):
        """Update current chapter progress (0.0 to 1.0)."""
        self._progress["current_chapter_progress"] = progress
        await self._update_job_payload()

    async def complete_chapter(self, success: bool, error_message: Optional[str] = None):
        """Complete current chapter download with atomic update."""
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

        if success:
            self._progress["downloaded_chapters"] += 1
        else:
            self._progress["error_count"] += 1
            if error_message:
                # Ensure errors array exists
                if "errors" not in self._progress:
                    self._progress["errors"] = []

                self._progress["errors"].append(
                    {
                        "chapter_id": self._progress["current_chapter"]["id"]
                        if self._progress["current_chapter"]
                        else "unknown",
                        "error": error_message,
                        "timestamp": timestamp,
                    }
                )

        # Update completion estimate
        if self._progress["total_chapters"] > 0:
            completion_rate = (
                self._progress["downloaded_chapters"] / self._progress["total_chapters"]
            )
            if completion_rate > 0:
                # Simple ETA estimation based on elapsed time and completion rate
                start_time = datetime.fromisoformat(self._progress["started_at"])
                elapsed = (
                    datetime.now(timezone.utc).replace(tzinfo=None) - start_time
                ).total_seconds()
                estimated_total = elapsed / completion_rate
                remaining = max(0, estimated_total - elapsed)
                self._progress["estimated_completion"] = (
                    datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=remaining)
                ).isoformat()

        # Clear current chapter
        self._progress["current_chapter"] = None
        self._progress["current_chapter_progress"] = 0.0

        # Atomic database update
        await self._update_job_payload()

    async def _update_job_payload(self):
        """Update job payload with current progress using atomic operation."""
        from sqlalchemy import update, func
        import json

        # Use atomic JSONB update to prevent race conditions
        # This creates a new progress object and merges it atomically
        progress_json = json.dumps(self._progress)

        try:
            result = await self.db.execute(
                update(JobQueue)
                .where(JobQueue.id == self.job_id)
                .values(
                    payload=func.jsonb_set(
                        JobQueue.payload,
                        "{progress}",
                        progress_json,
                        True,  # Create path if it doesn't exist
                    ),
                    updated_at=func.now(),
                )
                .returning(JobQueue.id)
            )

            if result.rowcount == 0:
                logger.warning(f"Failed to update progress for job {self.job_id} - job not found")

            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to update job progress atomically: {e}")
            await self.db.rollback()
            raise

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress data."""
        return self._progress.copy()


class DownloadService:
    """Service for downloading manga chapters from external sources."""

    def __init__(self):
        self.mangadx_client = MangaDxClient()
        self.download_timeout = 300.0  # 5 minutes per chapter
        self.retry_attempts = 3

    async def _fetch_manga_metadata(self, manga_id: str) -> Dict[str, Optional[str]]:
        """Fetch manga metadata from MangaDx API for better UI display."""
        try:
            async with self.mangadx_client:
                manga_data = await self.mangadx_client.get_manga(manga_id)

                # Extract title (prefer English, fall back to original)
                title = None
                if manga_data.title:
                    title = (
                        manga_data.title.get("en")
                        or manga_data.title.get("ja-ro")
                        or manga_data.title.get("ja")
                        or list(manga_data.title.values())[0]
                        if manga_data.title.values()
                        else None
                    )

                # Extract author using the relationships method from MangaDxMangaResponse
                author = None
                if hasattr(manga_data, "relationships") and manga_data.relationships:
                    author_info, _ = manga_data.get_author_info()
                    author = author_info

                # Extract cover URL (basic - would need cover art relationship processing)
                cover_url = None
                # Cover art processing would require additional API calls

                return {"manga_title": title, "manga_author": author, "manga_cover_url": cover_url}

        except Exception as e:
            logger.warning(f"Failed to fetch metadata for manga {manga_id}: {e}")
            return {"manga_title": None, "manga_author": None, "manga_cover_url": None}

    async def enqueue_single_chapter_download(
        self,
        db: AsyncSession,
        manga_id: str,
        chapter_id: str,
        series_id: Optional[UUID] = None,
        priority: int = 3,
        destination_path: Optional[str] = None,
    ) -> UUID:
        """
        Enqueue a single chapter download.

        Args:
            db: Database session
            manga_id: External manga ID (MangaDx UUID)
            chapter_id: External chapter ID to download
            series_id: Optional local series ID to associate with
            priority: Job priority (higher = more urgent)
            destination_path: Optional custom destination path

        Returns:
            UUID of the created download job
        """
        job_id = uuid4()

        # Fetch manga metadata for better UI display
        metadata = await self._fetch_manga_metadata(manga_id)

        payload = {
            "job_id": str(job_id),
            "download_type": "mangadx",
            "manga_id": manga_id,
            "chapter_ids": [chapter_id],
            "batch_type": "single",
            "series_id": str(series_id) if series_id else None,
            "destination_path": destination_path,
            "progress": {},
            **metadata,  # Include manga_title, manga_author, manga_cover_url
        }

        job = JobQueue(
            id=job_id,
            job_type="download",
            payload=payload,
            priority=priority,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(job)
        await db.commit()

        title_info = f" ({metadata['manga_title']})" if metadata.get("manga_title") else ""
        logger.info(
            f"Enqueued single chapter download job {job_id} for chapter {chapter_id}{title_info}"
        )
        return job_id

    async def enqueue_batch_download(
        self,
        db: AsyncSession,
        manga_id: str,
        chapter_ids: List[str],
        batch_type: str = "multiple",
        series_id: Optional[UUID] = None,
        volume_number: Optional[str] = None,
        priority: int = 3,
        destination_path: Optional[str] = None,
    ) -> UUID:
        """
        Enqueue a batch download of multiple chapters.

        Args:
            db: Database session
            manga_id: External manga ID (MangaDx UUID)
            chapter_ids: List of chapter IDs to download
            batch_type: Type of batch (multiple, volume, series)
            series_id: Optional local series ID to associate with
            volume_number: Optional volume number for volume downloads
            priority: Job priority (higher = more urgent)
            destination_path: Optional custom destination path

        Returns:
            UUID of the created download job
        """
        job_id = uuid4()

        # Fetch manga metadata for better UI display
        metadata = await self._fetch_manga_metadata(manga_id)

        payload = {
            "job_id": str(job_id),
            "download_type": "mangadx",
            "manga_id": manga_id,
            "chapter_ids": chapter_ids,
            "batch_type": batch_type,
            "series_id": str(series_id) if series_id else None,
            "volume_number": volume_number,
            "destination_path": destination_path,
            "progress": {},
            **metadata,  # Include manga_title, manga_author, manga_cover_url
        }

        job = JobQueue(
            id=job_id,
            job_type="download",
            payload=payload,
            priority=priority,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(job)
        await db.commit()

        title_info = f" ({metadata['manga_title']})" if metadata.get("manga_title") else ""
        logger.info(
            f"Enqueued batch download job {job_id} for {len(chapter_ids)} chapters{title_info}"
        )
        return job_id

    async def enqueue_series_download(
        self,
        db: AsyncSession,
        manga_id: str,
        series_id: Optional[UUID] = None,
        priority: int = 2,
        destination_path: Optional[str] = None,
    ) -> UUID:
        """
        Enqueue a complete series download.

        Args:
            db: Database session
            manga_id: External manga ID (MangaDx UUID)
            series_id: Optional local series ID to associate with
            priority: Job priority (higher = more urgent)
            destination_path: Optional custom destination path

        Returns:
            UUID of the created download job
        """
        # First get all chapters for this manga from MangaDx API
        try:
            async with self.mangadx_client:
                # This is a placeholder - MangaDx client would need chapter listing endpoint
                chapter_ids = await self._get_all_chapter_ids(manga_id)
        except Exception as e:
            logger.error(f"Failed to get chapter list for manga {manga_id}: {e}")
            raise DownloadError(f"Failed to get chapter list: {e}")

        return await self.enqueue_batch_download(
            db=db,
            manga_id=manga_id,
            chapter_ids=chapter_ids,
            batch_type="series",
            series_id=series_id,
            priority=priority,
            destination_path=destination_path,
        )

    async def execute_download_job(self, db: AsyncSession, job: JobQueue) -> Dict[str, Any]:
        """
        Execute a download job with progress tracking.

        Args:
            db: Database session
            job: JobQueue model with download type

        Returns:
            Dict with download results

        Raises:
            DownloadError: If download fails
        """
        job_data = DownloadJobData(job.payload)
        progress_tracker = DownloadProgressTracker(db, job.id)

        logger.info(f"Executing download job {job.id} for {len(job_data.chapter_ids)} chapters")

        try:
            # Initialize progress tracking
            await progress_tracker.initialize(len(job_data.chapter_ids))

            # Get destination path
            destination_path = await self._get_destination_path(db, job_data)

            # Download each chapter
            downloaded_chapters = []
            errors = []

            async with self.mangadx_client:
                for chapter_id in job_data.chapter_ids:
                    try:
                        # Download individual chapter with configurable quality
                        download_quality = job_data.payload.get("download_quality", "data")
                        chapter_result = await self._download_single_chapter(
                            progress_tracker=progress_tracker,
                            manga_id=job_data.manga_id,
                            chapter_id=chapter_id,
                            destination_path=destination_path,
                            quality=download_quality,
                        )
                        downloaded_chapters.append(chapter_result)
                        await progress_tracker.complete_chapter(success=True)

                    except Exception as e:
                        error_msg = f"Failed to download chapter {chapter_id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        await progress_tracker.complete_chapter(
                            success=False, error_message=error_msg
                        )

            # Update database with downloaded chapters
            if job_data.series_id and downloaded_chapters:
                await self._update_series_with_downloads(
                    db, job_data.series_id, downloaded_chapters
                )

            result = {
                "job_id": str(job.id),
                "job_type": "download",
                "download_type": job_data.download_type,
                "manga_id": job_data.manga_id,
                "series_id": job_data.series_id,
                "batch_type": job_data.batch_type,
                "total_chapters": len(job_data.chapter_ids),
                "downloaded_chapters": len(downloaded_chapters),
                "error_count": len(errors),
                "destination_path": destination_path,
                "downloaded_files": [ch["file_path"] for ch in downloaded_chapters],
                "progress": progress_tracker.get_progress(),
            }

            logger.info(
                f"Download job {job.id} completed: {len(downloaded_chapters)} chapters downloaded, {len(errors)} errors"
            )
            return result

        except Exception as e:
            logger.error(f"Download job {job.id} failed: {e}")
            raise DownloadError(f"Download job execution failed: {e}")

    async def _download_single_chapter(
        self,
        progress_tracker: DownloadProgressTracker,
        manga_id: str,
        chapter_id: str,
        destination_path: str,
        quality: str = "data",
    ) -> Dict[str, Any]:
        """
        Download a single chapter from MangaDx with real implementation.

        Args:
            progress_tracker: Progress tracker for updates
            manga_id: MangaDx manga UUID
            chapter_id: MangaDx chapter UUID
            destination_path: Local destination path
            quality: Download quality ("data" for full, "data-saver" for compressed)

        Returns:
            Dict with chapter download results
        """
        try:
            logger.info(f"Starting real download for chapter {chapter_id} from manga {manga_id}")

            # Step 1: Get chapter metadata (10% progress)
            await progress_tracker.update_chapter_progress(0.1)
            chapter_response = await self.mangadx_client._make_request(
                "GET", f"/chapter/{chapter_id}"
            )

            # Import here to avoid circular imports
            from kiremisu.database.schemas import MangaDxChapterResponse

            chapter_data = MangaDxChapterResponse(**chapter_response["data"])

            # Create chapter title from metadata
            chapter_title = self._format_chapter_title(chapter_data)
            await progress_tracker.start_chapter(chapter_id, chapter_title)

            logger.info(f"Downloaded chapter metadata: {chapter_title}")

            # Step 2: Get @Home server information (20% progress)
            await progress_tracker.update_chapter_progress(0.2)
            at_home_response = await self.mangadx_client.get_chapter_at_home_server(chapter_id)

            logger.info(f"Got @Home server: {at_home_response.base_url}")

            # Step 3: Download all pages (20% to 90% progress)
            await progress_tracker.update_chapter_progress(0.3)
            page_filenames = at_home_response.chapter.get_page_filenames(quality)

            if not page_filenames:
                raise DownloadError(f"No pages found for chapter {chapter_id}")

            logger.info(f"Downloading {len(page_filenames)} pages for chapter {chapter_id}")

            # Download pages with progress updates
            page_data_list = []
            total_pages = len(page_filenames)

            # Create a progress callback for individual page downloads
            async def page_download_progress(page_index: int):
                """Update progress as each page completes."""
                base_progress = 0.3
                download_progress = 0.6 * (page_index / total_pages)
                await progress_tracker.update_chapter_progress(base_progress + download_progress)

            page_data_list = await self._download_chapter_pages_with_progress(
                chapter_id=chapter_id,
                base_url=at_home_response.base_url,
                chapter_hash=at_home_response.chapter.hash,
                page_filenames=page_filenames,
                quality=quality,
                progress_callback=page_download_progress,
            )

            logger.info(f"Downloaded {len(page_data_list)} pages for chapter {chapter_id}")

            # Step 4: Create CBZ file (90% to 100% progress)
            await progress_tracker.update_chapter_progress(0.9)

            # Ensure destination directory exists
            os.makedirs(destination_path, exist_ok=True)

            # Create sanitized filename
            safe_filename = self._create_safe_filename(chapter_data, chapter_id)
            chapter_file_path = os.path.join(destination_path, f"{safe_filename}.cbz")

            # Create CBZ archive with downloaded pages
            await self._create_cbz_archive(
                chapter_file_path=chapter_file_path,
                page_data_list=page_data_list,
                chapter_metadata=chapter_data,
            )

            await progress_tracker.update_chapter_progress(1.0)

            file_size = os.path.getsize(chapter_file_path)
            logger.info(f"Created CBZ file: {chapter_file_path} ({file_size / 1024 / 1024:.1f}MB)")

            return {
                "chapter_id": chapter_id,
                "title": chapter_title,
                "file_path": chapter_file_path,
                "file_size": file_size,
                "page_count": len(page_data_list),
                "download_quality": quality,
                "chapter_number": chapter_data.get_chapter_number(),
                "volume_number": chapter_data.get_volume_number(),
            }

        except Exception as e:
            logger.error(f"Failed to download chapter {chapter_id}: {e}")
            raise DownloadError(f"Chapter download failed: {e}")

    async def _download_chapter_pages_with_progress(
        self,
        chapter_id: str,
        base_url: str,
        chapter_hash: str,
        page_filenames: List[str],
        quality: str = "data",
        progress_callback=None,
        max_concurrent: int = 3,
        timeout_per_page: float = 30.0,
        max_retries_per_page: int = 3,
    ) -> List[bytes]:
        """
        Download chapter pages with progress tracking and enhanced error handling.

        Args:
            chapter_id: MangaDx chapter UUID
            base_url: @Home server base URL
            chapter_hash: Chapter hash for URL construction
            page_filenames: List of page filenames
            quality: Quality setting ("data" or "data-saver")
            progress_callback: Optional callback for progress updates
            max_concurrent: Maximum concurrent downloads
            timeout_per_page: Timeout per page in seconds
            max_retries_per_page: Maximum retries per failed page

        Returns:
            List of downloaded page image data as bytes
        """
        if not page_filenames:
            return []

        # Construct page URLs
        quality_path = "data-saver" if quality == "data-saver" else "data"
        page_urls = [
            f"{base_url}/{quality_path}/{chapter_hash}/{filename}" for filename in page_filenames
        ]

        downloaded_pages = [None] * len(page_urls)
        failed_pages = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_single_page(url: str, page_index: int) -> bool:
            """Download a single page with retries."""
            async with semaphore:
                for attempt in range(max_retries_per_page):
                    try:
                        # Rate limiting
                        await self.mangadx_client.rate_limiter.acquire()

                        logger.debug(
                            f"Downloading page {page_index + 1}/{len(page_urls)} (attempt {attempt + 1})"
                        )

                        response = await self.mangadx_client.client.get(
                            url,
                            timeout=httpx.Timeout(timeout_per_page),
                            follow_redirects=True,
                        )

                        if response.status_code == 200:
                            downloaded_pages[page_index] = response.content

                            # Update progress if callback provided
                            if progress_callback:
                                await progress_callback(page_index + 1)

                            return True
                        else:
                            logger.warning(
                                f"Page {page_index + 1} HTTP {response.status_code} (attempt {attempt + 1})"
                            )
                            if attempt == max_retries_per_page - 1:
                                raise DownloadError(f"HTTP {response.status_code}")

                    except Exception as e:
                        logger.warning(
                            f"Page {page_index + 1} download failed (attempt {attempt + 1}): {e}"
                        )
                        if attempt == max_retries_per_page - 1:
                            failed_pages.append((page_index + 1, str(e)))
                            return False

                        # Exponential backoff for retries
                        await asyncio.sleep(min(2**attempt, 10))

                return False

        # Download all pages concurrently
        tasks = [download_single_page(url, i) for i, url in enumerate(page_urls)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None values (failed downloads)
        successful_pages = [page for page in downloaded_pages if page is not None]

        if failed_pages:
            failure_rate = len(failed_pages) / len(page_urls)
            error_msg = f"{len(failed_pages)}/{len(page_urls)} pages failed to download"
            logger.error(f"Chapter {chapter_id}: {error_msg}")

            # Fail if too many pages failed
            if failure_rate > 0.3:  # Allow up to 30% page failure
                raise DownloadError(f"Too many page failures ({failure_rate:.1%}): {error_msg}")

        logger.info(f"Successfully downloaded {len(successful_pages)}/{len(page_urls)} pages")
        return successful_pages

    async def _create_cbz_archive(
        self,
        chapter_file_path: str,
        page_data_list: List[bytes],
        chapter_metadata: "MangaDxChapterResponse",
    ):
        """
        Create a CBZ archive from downloaded page data.

        Args:
            chapter_file_path: Path where CBZ file should be created
            page_data_list: List of page image data as bytes
            chapter_metadata: Chapter metadata for archive info
        """
        try:
            with zipfile.ZipFile(chapter_file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add pages with sequential naming
                for i, page_data in enumerate(page_data_list, 1):
                    # Detect image format from bytes
                    if page_data.startswith(b"\xff\xd8\xff"):
                        ext = "jpg"
                    elif page_data.startswith(b"\x89PNG"):
                        ext = "png"
                    elif page_data.startswith(b"WEBP"):
                        ext = "webp"
                    else:
                        ext = "jpg"  # Default fallback

                    page_filename = f"{i:03d}.{ext}"
                    zf.writestr(page_filename, page_data)

                # Add metadata file
                metadata = {
                    "title": chapter_metadata.attributes.title
                    or f"Chapter {chapter_metadata.attributes.chapter}",
                    "chapter": chapter_metadata.attributes.chapter,
                    "volume": chapter_metadata.attributes.volume,
                    "pages": len(page_data_list),
                    "language": chapter_metadata.attributes.translated_language,
                    "mangadx_id": chapter_metadata.id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                import json

                zf.writestr("metadata.json", json.dumps(metadata, indent=2))

        except Exception as e:
            logger.error(f"Failed to create CBZ archive {chapter_file_path}: {e}")
            # Clean up partial file
            if os.path.exists(chapter_file_path):
                try:
                    os.remove(chapter_file_path)
                except:
                    pass
            raise DownloadError(f"CBZ creation failed: {e}")

    def _format_chapter_title(self, chapter_data: "MangaDxChapterResponse") -> str:
        """Format a human-readable chapter title."""
        parts = []

        if chapter_data.attributes.volume:
            parts.append(f"Vol.{chapter_data.attributes.volume}")

        if chapter_data.attributes.chapter:
            parts.append(f"Ch.{chapter_data.attributes.chapter}")

        if chapter_data.attributes.title:
            parts.append(chapter_data.attributes.title)

        if not parts:
            parts.append(f"Chapter {chapter_data.id[:8]}")

        return " - ".join(parts)

    def _create_safe_filename(self, chapter_data: "MangaDxChapterResponse", chapter_id: str) -> str:
        """Create a filesystem-safe filename for the chapter."""
        parts = []

        if chapter_data.attributes.volume:
            parts.append(f"v{chapter_data.attributes.volume}")

        if chapter_data.attributes.chapter:
            # Pad chapter numbers for proper sorting
            try:
                ch_num = float(chapter_data.attributes.chapter)
                if ch_num.is_integer():
                    parts.append(f"c{int(ch_num):04d}")
                else:
                    parts.append(f"c{ch_num:07.1f}")
            except:
                parts.append(f"c{chapter_data.attributes.chapter}")

        if chapter_data.attributes.title:
            # Sanitize title for filename
            safe_title = "".join(
                c for c in chapter_data.attributes.title if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            if safe_title:
                parts.append(safe_title[:50])  # Limit length

        filename = "_".join(parts) if parts else f"chapter_{chapter_id[:8]}"

        # Replace spaces with underscores and ensure safe characters
        filename = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in filename)

        return filename

    async def _get_destination_path(self, db: AsyncSession, job_data: DownloadJobData) -> str:
        """
        Get the destination path for downloads.

        Args:
            db: Database session
            job_data: Download job data

        Returns:
            Absolute destination path
        """
        if job_data.destination_path:
            return job_data.destination_path

        # Get first enabled library path as default
        result = await db.execute(
            select(LibraryPath)
            .where(LibraryPath.enabled == True)
            .order_by(LibraryPath.created_at.asc())
            .limit(1)
        )
        library_path = result.scalar_one_or_none()

        if not library_path:
            raise DownloadError("No enabled library paths configured for downloads")

        # Create downloads subfolder
        download_path = os.path.join(library_path.path, "downloads", job_data.manga_id)
        return download_path

    async def _update_series_with_downloads(
        self, db: AsyncSession, series_id: str, downloaded_chapters: List[Dict[str, Any]]
    ):
        """
        Update series database records with downloaded chapters.

        Args:
            db: Database session
            series_id: Local series UUID
            downloaded_chapters: List of downloaded chapter data
        """
        try:
            # This would create Chapter records in the database
            # For now, this is a placeholder
            logger.info(
                f"Would update series {series_id} with {len(downloaded_chapters)} downloaded chapters"
            )

        except Exception as e:
            logger.error(f"Failed to update series {series_id} with downloads: {e}")

    async def _get_all_chapter_ids(
        self, manga_id: str, language: List[str] = ["en"], max_chapters: Optional[int] = None
    ) -> List[str]:
        """
        Get all chapter IDs for a manga from MangaDx API.

        Args:
            manga_id: MangaDx manga UUID
            language: List of language codes to filter by
            max_chapters: Optional limit on number of chapters to return

        Returns:
            List of chapter UUIDs
        """
        try:
            logger.info(f"Fetching all chapters for manga {manga_id}")

            all_chapter_ids = []
            offset = 0
            limit = 100  # Reduced limit to avoid 400 Bad Request errors

            # Paginate through all chapters
            while True:
                chapter_response = await self.mangadx_client.get_manga_chapters(
                    manga_id=manga_id,
                    translated_language=language,
                    limit=limit,
                    offset=offset,
                    order_by="chapter",
                    order_direction="asc",
                )

                # Extract chapter IDs from response
                chapter_ids = [chapter.id for chapter in chapter_response.data]
                all_chapter_ids.extend(chapter_ids)

                logger.info(
                    f"Retrieved {len(chapter_ids)} chapters (offset {offset}, total so far: {len(all_chapter_ids)})"
                )

                # Check if we have more chapters or hit our limit
                if not chapter_response.has_more:
                    break

                if max_chapters and len(all_chapter_ids) >= max_chapters:
                    all_chapter_ids = all_chapter_ids[:max_chapters]
                    break

                offset += limit

                # Safety check to prevent infinite loops
                if offset > 10000:  # Reasonable upper limit
                    logger.warning(f"Hit safety limit of 10000 chapters for manga {manga_id}")
                    break

            logger.info(f"Found {len(all_chapter_ids)} total chapters for manga {manga_id}")
            return all_chapter_ids

        except Exception as e:
            logger.error(f"Failed to get chapters for manga {manga_id}: {e}")
            raise DownloadError(f"Failed to get chapter list: {e}")

    async def get_download_jobs(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[JobQueue], int]:
        """
        Get download jobs with optional filtering.

        Args:
            db: Database session
            status: Optional status filter
            limit: Maximum number of jobs to return
            offset: Offset for pagination

        Returns:
            Tuple of (jobs list, total count)
        """
        query = select(JobQueue).where(JobQueue.job_type == "download")

        if status:
            query = query.where(JobQueue.status == status)

        # Get total count
        count_result = await db.execute(
            select(JobQueue.id).where(
                and_(
                    JobQueue.job_type == "download",
                    JobQueue.status == status if status else True,
                )
            )
        )
        total_count = len(count_result.fetchall())

        # Get paginated results
        query = query.order_by(desc(JobQueue.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        jobs = result.scalars().all()

        return jobs, total_count

    async def cancel_download_job(self, db: AsyncSession, job_id: UUID) -> bool:
        """
        Cancel a pending or running download job.

        Args:
            db: Database session
            job_id: Job UUID to cancel

        Returns:
            True if successfully cancelled
        """
        from sqlalchemy import update

        result = await db.execute(
            update(JobQueue)
            .where(
                and_(
                    JobQueue.id == job_id,
                    JobQueue.job_type == "download",
                    JobQueue.status.in_(["pending", "running"]),
                )
            )
            .values(
                status="failed",
                error_message="Cancelled by user",
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        await db.commit()

        cancelled = result.rowcount > 0
        if cancelled:
            logger.info(f"Cancelled download job {job_id}")
        else:
            logger.warning(f"Could not cancel download job {job_id} - not found or not cancellable")

        return cancelled

    async def retry_download_job(self, db: AsyncSession, job_id: UUID) -> bool:
        """
        Retry a failed download job.

        Args:
            db: Database session
            job_id: Job UUID to retry

        Returns:
            True if successfully queued for retry
        """
        from sqlalchemy import update

        result = await db.execute(
            update(JobQueue)
            .where(
                and_(
                    JobQueue.id == job_id,
                    JobQueue.job_type == "download",
                    JobQueue.status == "failed",
                )
            )
            .values(
                status="pending",
                error_message=None,
                started_at=None,
                completed_at=None,
                scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        await db.commit()

        retried = result.rowcount > 0
        if retried:
            logger.info(f"Queued download job {job_id} for retry")
        else:
            logger.warning(f"Could not retry download job {job_id} - not found or not failed")

        return retried

    async def cleanup(self):
        """Clean up resources."""
        await self.mangadx_client.close()
