"""Download service for manga chapters from external sources."""

import asyncio
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
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
        """Start tracking a chapter download."""
        self._progress["current_chapter"] = {
            "id": chapter_id,
            "title": chapter_title,
            "started_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }
        self._progress["current_chapter_progress"] = 0.0
        await self._update_job_payload()
    
    async def update_chapter_progress(self, progress: float):
        """Update current chapter progress (0.0 to 1.0)."""
        self._progress["current_chapter_progress"] = progress
        await self._update_job_payload()
    
    async def complete_chapter(self, success: bool, error_message: Optional[str] = None):
        """Complete current chapter download."""
        if success:
            self._progress["downloaded_chapters"] += 1
        else:
            self._progress["error_count"] += 1
            if error_message:
                self._progress["errors"].append({
                    "chapter_id": self._progress["current_chapter"]["id"] if self._progress["current_chapter"] else "unknown",
                    "error": error_message,
                    "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                })
        
        # Clear current chapter
        self._progress["current_chapter"] = None
        self._progress["current_chapter_progress"] = 0.0
        await self._update_job_payload()
    
    async def _update_job_payload(self):
        """Update job payload with current progress."""
        from sqlalchemy import update
        
        await self.db.execute(
            update(JobQueue)
            .where(JobQueue.id == self.job_id)
            .values(payload=JobQueue.payload.op("||")({"progress": self._progress}))
        )
        await self.db.commit()
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress data."""
        return self._progress.copy()


class DownloadService:
    """Service for downloading manga chapters from external sources."""
    
    def __init__(self):
        self.mangadx_client = MangaDxClient()
        self.download_timeout = 300.0  # 5 minutes per chapter
        self.retry_attempts = 3
    
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
        
        payload = {
            "job_id": str(job_id),
            "download_type": "mangadx",
            "manga_id": manga_id,
            "chapter_ids": [chapter_id],
            "batch_type": "single",
            "series_id": str(series_id) if series_id else None,
            "destination_path": destination_path,
            "progress": {},
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
        
        logger.info(f"Enqueued single chapter download job {job_id} for chapter {chapter_id}")
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
        
        logger.info(f"Enqueued batch download job {job_id} for {len(chapter_ids)} chapters")
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
                        # Download individual chapter
                        chapter_result = await self._download_single_chapter(
                            progress_tracker=progress_tracker,
                            manga_id=job_data.manga_id,
                            chapter_id=chapter_id,
                            destination_path=destination_path,
                        )
                        downloaded_chapters.append(chapter_result)
                        await progress_tracker.complete_chapter(success=True)
                        
                    except Exception as e:
                        error_msg = f"Failed to download chapter {chapter_id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        await progress_tracker.complete_chapter(success=False, error_message=error_msg)
            
            # Update database with downloaded chapters
            if job_data.series_id and downloaded_chapters:
                await self._update_series_with_downloads(db, job_data.series_id, downloaded_chapters)
            
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
            
            logger.info(f"Download job {job.id} completed: {len(downloaded_chapters)} chapters downloaded, {len(errors)} errors")
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
    ) -> Dict[str, Any]:
        """
        Download a single chapter from MangaDx.
        
        Args:
            progress_tracker: Progress tracker for updates
            manga_id: MangaDx manga UUID
            chapter_id: MangaDx chapter UUID
            destination_path: Local destination path
            
        Returns:
            Dict with chapter download results
        """
        chapter_title = f"Chapter {chapter_id}"  # Placeholder
        await progress_tracker.start_chapter(chapter_id, chapter_title)
        
        try:
            # Get chapter information from MangaDx
            # This is a placeholder implementation - real implementation would:
            # 1. Get chapter metadata from MangaDx API
            # 2. Get at-home server URL for chapter pages
            # 3. Download all pages and create CBZ file
            
            await asyncio.sleep(1)  # Simulate download time
            await progress_tracker.update_chapter_progress(0.5)
            
            # Create a placeholder CBZ file
            chapter_filename = f"{chapter_title.replace(' ', '_')}.cbz"
            chapter_file_path = os.path.join(destination_path, chapter_filename)
            
            # Ensure destination directory exists
            os.makedirs(destination_path, exist_ok=True)
            
            # Create empty CBZ file as placeholder
            with zipfile.ZipFile(chapter_file_path, 'w') as zf:
                zf.writestr("page_001.jpg", b"placeholder_image_data")
            
            await progress_tracker.update_chapter_progress(1.0)
            
            return {
                "chapter_id": chapter_id,
                "title": chapter_title,
                "file_path": chapter_file_path,
                "file_size": os.path.getsize(chapter_file_path),
                "page_count": 1,  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Failed to download chapter {chapter_id}: {e}")
            raise DownloadError(f"Chapter download failed: {e}")
    
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
        self,
        db: AsyncSession,
        series_id: str,
        downloaded_chapters: List[Dict[str, Any]]
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
            logger.info(f"Would update series {series_id} with {len(downloaded_chapters)} downloaded chapters")
            
        except Exception as e:
            logger.error(f"Failed to update series {series_id} with downloads: {e}")
    
    async def _get_all_chapter_ids(self, manga_id: str) -> List[str]:
        """
        Get all chapter IDs for a manga from MangaDx.
        
        Args:
            manga_id: MangaDx manga UUID
            
        Returns:
            List of chapter UUIDs
        """
        # This is a placeholder implementation
        # Real implementation would use MangaDx chapter listing API
        return [f"chapter-{i}" for i in range(1, 6)]  # Placeholder: 5 chapters
    
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