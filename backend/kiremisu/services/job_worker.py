"""Job execution service for processing background jobs."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath
from kiremisu.services.importer import ImporterService

logger = logging.getLogger(__name__)


class JobExecutionError(Exception):
    """Exception raised when job execution fails."""

    pass


class JobWorker:
    """Worker service for executing background jobs."""

    def __init__(self):
        self.importer = ImporterService()

    async def execute_job(self, db: AsyncSession, job: JobQueue) -> Dict[str, Any]:
        """Execute a single job and update its status.

        Uses a single transaction for all database operations to ensure consistency.

        Args:
            db: Database session
            job: JobQueue model to execute

        Returns:
            Dict with execution results

        Raises:
            JobExecutionError: If job execution fails
        """
        logger.info(f"Starting execution of job {job.id} (type: {job.job_type})")

        try:
            # Job is already marked as running from atomic claim, just verify status
            if job.status != "running":
                raise JobExecutionError(f"Job {job.id} has invalid status {job.status}")

            # Execute job based on type
            if job.job_type == "library_scan":
                result = await self._execute_library_scan(db, job)
            elif job.job_type == "download":
                result = await self._execute_download(db, job)
            else:
                raise JobExecutionError(f"Unknown job type: {job.job_type}")

            # Complete job successfully - mark as completed
            await self._update_job_status(
                db, job.id, "completed", completed_at=datetime.now(timezone.utc).replace(tzinfo=None), error_message=None
            )

            # Commit all changes in single transaction
            await db.commit()

            logger.info(f"Job {job.id} completed successfully")
            return result

        except Exception as e:
            # Rollback any partial changes
            await db.rollback()

            error_msg = str(e)
            logger.error(f"Job {job.id} failed: {error_msg}", exc_info=True)

            # Handle retry logic in separate transaction
            await self._handle_job_failure(db, job, error_msg)

            raise JobExecutionError(f"Job execution failed: {error_msg}")

    async def _handle_job_failure(self, db: AsyncSession, job: JobQueue, error_msg: str):
        """Handle job failure with retry logic in separate transaction.

        Args:
            db: Database session
            job: Failed job
            error_msg: Error message
        """
        try:
            # Refresh job to get current state
            await db.refresh(job)

            # Determine if we should retry
            should_retry = job.retry_count < job.max_retries

            if should_retry:
                # Mark for retry - increment retry count and set back to pending
                new_retry_count = job.retry_count + 1
                await self._update_job_status(
                    db,
                    job.id,
                    "pending",
                    error_message=error_msg,
                    retry_count=new_retry_count,
                    started_at=None,  # Clear started_at for retry
                )
                logger.info(
                    f"Job {job.id} will be retried (attempt {new_retry_count}/{job.max_retries})"
                )
            else:
                # Mark as failed
                await self._update_job_status(
                    db,
                    job.id,
                    "failed",
                    completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    error_message=error_msg,
                )
                logger.error(f"Job {job.id} failed permanently after {job.retry_count} retries")

            # Commit failure status update
            await db.commit()

        except Exception as retry_error:
            await db.rollback()
            logger.error(f"Failed to update job failure status: {retry_error}", exc_info=True)

    async def _execute_library_scan(self, db: AsyncSession, job: JobQueue) -> Dict[str, Any]:
        """Execute a library scan job.

        Args:
            db: Database session
            job: JobQueue model with library_scan type

        Returns:
            Dict with scan results
        """
        payload = job.payload
        library_path_id_str = payload.get("library_path_id")
        library_path_id = UUID(library_path_id_str) if library_path_id_str else None

        logger.info(f"Executing library scan for path_id: {library_path_id}")

        # Execute the scan using the importer service
        stats = await self.importer.scan_library_paths(db=db, library_path_id=library_path_id)

        # Update last_scan timestamp for the library path(s)
        if library_path_id:
            # Update specific library path
            await self._update_library_path_last_scan(db, library_path_id)
        else:
            # Update all enabled library paths
            await self._update_all_library_paths_last_scan(db)

        result = {
            "job_type": "library_scan",
            "library_path_id": library_path_id_str,
            "stats": stats if isinstance(stats, dict) else stats.to_dict(),
        }

        logger.info(f"Library scan completed: {result}")
        return result

    async def _execute_download(self, db: AsyncSession, job: JobQueue) -> Dict[str, Any]:
        """Execute a download job for manga from external sources.

        Args:
            db: Database session
            job: JobQueue model with download type

        Returns:
            Dict with download results
        """
        payload = job.payload
        download_type = payload.get("download_type", "mangadx")
        manga_id = payload.get("manga_id")
        series_id = payload.get("series_id")

        if not manga_id:
            raise JobExecutionError("Download job missing required 'manga_id' in payload")

        logger.info(f"Executing download job for {download_type} manga_id: {manga_id}")

        # For now, this is a placeholder implementation
        # In a full implementation, this would:
        # 1. Connect to external API (MangaDx, etc.)
        # 2. Download chapter files
        # 3. Store them in appropriate directory structure
        # 4. Update database with new chapters

        result = {
            "job_type": "download",
            "download_type": download_type,
            "manga_id": manga_id,
            "series_id": series_id,
            "status": "completed",
            "downloaded_chapters": 0,  # Placeholder
            "message": f"Download job completed for {download_type} manga {manga_id}",
        }

        logger.info(f"Download job completed: {result}")
        return result

    async def _update_job_status(
        self,
        db: AsyncSession,
        job_id: UUID,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
    ):
        """Update job status and related fields.

        Args:
            db: Database session
            job_id: Job UUID
            status: New status
            started_at: Optional started timestamp (use None to clear)
            completed_at: Optional completed timestamp
            error_message: Optional error message
            retry_count: Optional retry count
        """
        update_values = {"status": status, "updated_at": datetime.now(timezone.utc).replace(tzinfo=None)}

        # Handle started_at explicitly - None means clear it for retries
        if started_at is not None:
            update_values["started_at"] = started_at
        elif status == "pending":  # Clear started_at when resetting to pending for retry
            update_values["started_at"] = None

        if completed_at is not None:
            update_values["completed_at"] = completed_at
        if error_message is not None:
            update_values["error_message"] = error_message
        if retry_count is not None:
            update_values["retry_count"] = retry_count

        await db.execute(update(JobQueue).where(JobQueue.id == job_id).values(**update_values))
        # Note: Commit is handled by caller for transaction consistency

    async def _update_library_path_last_scan(self, db: AsyncSession, library_path_id: UUID):
        """Update last_scan timestamp for a specific library path.

        Args:
            db: Database session
            library_path_id: Library path UUID
        """
        await db.execute(
            update(LibraryPath)
            .where(LibraryPath.id == library_path_id)
            .values(last_scan=datetime.now(timezone.utc).replace(tzinfo=None), updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        # Note: Commit is handled by caller for transaction consistency

    async def _update_all_library_paths_last_scan(self, db: AsyncSession):
        """Update last_scan timestamp for all enabled library paths.

        Args:
            db: Database session
        """
        await db.execute(
            update(LibraryPath)
            .where(LibraryPath.enabled == True)
            .values(last_scan=datetime.now(timezone.utc).replace(tzinfo=None), updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        # Note: Commit is handled by caller for transaction consistency


class JobWorkerRunner:
    """Background worker that polls and executes jobs from the queue."""

    def __init__(
        self, db_session_factory, poll_interval_seconds: int = 10, max_concurrent_jobs: int = 3
    ):
        """Initialize job worker runner.

        Args:
            db_session_factory: Factory function to create database sessions
            poll_interval_seconds: How often to poll for jobs (default 10 seconds)
            max_concurrent_jobs: Maximum number of concurrent jobs (default 3)
        """
        self.db_session_factory = db_session_factory
        self.poll_interval = poll_interval_seconds
        self.max_concurrent_jobs = max_concurrent_jobs
        self._running = False
        self._task = None
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._active_jobs = set()

    async def start(self):
        """Start the background job worker."""
        if self._running:
            logger.warning("Job worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_worker())
        logger.info(
            f"Started background job worker (poll interval: {self.poll_interval}s, max concurrent: {self.max_concurrent_jobs})"
        )

    async def stop(self):
        """Stop the background job worker."""
        if not self._running:
            return

        self._running = False

        # Cancel main worker task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Wait for active jobs to complete
        if self._active_jobs:
            logger.info(f"Waiting for {len(self._active_jobs)} active jobs to complete...")
            await asyncio.gather(*self._active_jobs, return_exceptions=True)

        logger.info("Stopped background job worker")

    async def _run_worker(self):
        """Main worker loop."""
        while self._running:
            try:
                await self._process_available_jobs()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)

            # Wait for next poll interval
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    async def _process_available_jobs(self):
        """Process all available jobs up to the concurrency limit."""
        # Check how many job slots are available
        available_slots = self.max_concurrent_jobs - len(self._active_jobs)
        if available_slots <= 0:
            return

        async with self.db_session_factory() as db:
            # Atomically claim jobs to prevent race conditions between workers
            # First, get the IDs of jobs we want to claim
            job_ids_result = await db.execute(
                select(JobQueue.id)
                .where(
                    and_(
                        JobQueue.status == "pending",
                        JobQueue.scheduled_at <= datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
                .order_by(JobQueue.priority.desc(), JobQueue.scheduled_at.asc())
                .limit(available_slots)
            )
            job_ids = [row[0] for row in job_ids_result.fetchall()]

            if not job_ids:
                return

            # Atomically claim these jobs by updating their status to 'running'
            claimed_jobs_result = await db.execute(
                update(JobQueue)
                .where(
                    and_(
                        JobQueue.id.in_(job_ids),
                        JobQueue.status == "pending",  # Double-check they're still pending
                    )
                )
                .values(status="running", started_at=datetime.now(timezone.utc).replace(tzinfo=None))
                .returning(JobQueue)
            )

            await db.commit()
            jobs = claimed_jobs_result.scalars().all()

        # Start processing jobs
        for job in jobs:
            if len(self._active_jobs) >= self.max_concurrent_jobs:
                break

            # Create task for job execution
            task = asyncio.create_task(self._execute_job_with_cleanup(job))
            self._active_jobs.add(task)

    async def _execute_job_with_cleanup(self, job: JobQueue):
        """Execute a job and handle cleanup.

        Args:
            job: JobQueue model to execute
        """
        async with self._semaphore:  # Limit concurrency
            try:
                async with self.db_session_factory() as db:
                    worker = JobWorker()
                    await worker.execute_job(db, job)

            except Exception as e:
                logger.error(f"Job execution failed: {e}", exc_info=True)

            finally:
                # Remove from active jobs set
                current_task = asyncio.current_task()
                if current_task in self._active_jobs:
                    self._active_jobs.remove(current_task)

    async def get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status.

        Returns:
            Dict with worker status information
        """
        return {
            "running": self._running,
            "active_jobs": len(self._active_jobs),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "poll_interval_seconds": self.poll_interval,
        }
