"""Job scheduling service for automatic library path scanning."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath

logger = logging.getLogger(__name__)


class JobScheduler:
    """Service for scheduling background jobs based on library path intervals."""

    @staticmethod
    async def schedule_library_scans(db: AsyncSession) -> Dict[str, int]:
        """Schedule library scan jobs for all enabled paths that need scanning.

        Args:
            db: Database session

        Returns:
            Dict with counts of scheduled jobs and skipped paths
        """
        logger.info("Starting library scan job scheduling")

        # Get all enabled library paths
        result = await db.execute(select(LibraryPath).where(LibraryPath.enabled == True))
        library_paths = result.scalars().all()

        scheduled_count = 0
        skipped_count = 0

        for path in library_paths:
            # Check if this path needs scanning
            if JobScheduler._should_schedule_scan(path):
                # Check if there's already a pending/running job for this path
                existing_job = await JobScheduler._get_existing_job(db, path.id)

                if existing_job:
                    logger.debug(f"Skipping job scheduling for path {path.id}: existing job found")
                    skipped_count += 1
                    continue

                # Create new scan job
                job = JobQueue(
                    job_type="library_scan",
                    payload={"library_path_id": str(path.id), "library_path": path.path},
                    priority=1,  # Normal priority for scheduled scans
                    scheduled_at=datetime.utcnow(),
                )

                db.add(job)
                scheduled_count += 1
                logger.info(f"Scheduled library scan job for path: {path.path}")
            else:
                skipped_count += 1
                logger.debug(f"Skipping path {path.path}: not due for scan")

        await db.commit()

        result = {
            "scheduled": scheduled_count,
            "skipped": skipped_count,
            "total_paths": len(library_paths),
        }

        logger.info(f"Job scheduling completed: {result}")
        return result

    @staticmethod
    async def schedule_manual_scan(
        db: AsyncSession,
        library_path_id: Optional[UUID] = None,
        priority: int = 5,  # Higher priority for manual scans
    ) -> UUID:
        """Schedule a manual library scan job with high priority.

        Args:
            db: Database session
            library_path_id: Optional specific library path to scan
            priority: Job priority (higher = more urgent)

        Returns:
            UUID of the created job
        """
        payload = {}
        if library_path_id:
            # Verify the library path exists
            result = await db.execute(select(LibraryPath).where(LibraryPath.id == library_path_id))
            library_path = result.scalar_one_or_none()

            if not library_path:
                raise ValueError(f"Library path not found: {library_path_id}")

            payload = {"library_path_id": str(library_path_id), "library_path": library_path.path}

        job = JobQueue(
            job_type="library_scan",
            payload=payload,
            priority=priority,
            scheduled_at=datetime.utcnow(),
        )

        db.add(job)
        await db.commit()

        logger.info(f"Scheduled manual library scan job {job.id} with payload: {payload}")
        return job.id

    @staticmethod
    async def get_job_status(db: AsyncSession, job_id: UUID) -> Optional[JobQueue]:
        """Get the status of a specific job.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            JobQueue model or None if not found
        """
        result = await db.execute(select(JobQueue).where(JobQueue.id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent_jobs(
        db: AsyncSession, job_type: Optional[str] = None, limit: int = 50
    ) -> List[JobQueue]:
        """Get recent jobs, optionally filtered by type.

        Args:
            db: Database session
            job_type: Optional job type filter
            limit: Maximum number of jobs to return

        Returns:
            List of JobQueue models ordered by creation time desc
        """
        query = select(JobQueue)

        if job_type:
            query = query.where(JobQueue.job_type == job_type)

        query = query.order_by(JobQueue.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_queue_stats(db: AsyncSession) -> Dict[str, int]:
        """Get statistics about the job queue.

        Args:
            db: Database session

        Returns:
            Dict with queue statistics
        """
        # Count jobs by status
        result = await db.execute(
            select(JobQueue.status, JobQueue.job_type).where(
                JobQueue.status.in_(["pending", "running", "failed"])
            )
        )
        jobs = result.all()

        stats = {
            "pending": 0,
            "running": 0,
            "failed": 0,
            "library_scan_pending": 0,
            "library_scan_running": 0,
            "library_scan_failed": 0,
        }

        for status, job_type in jobs:
            stats[status] = stats.get(status, 0) + 1
            if job_type == "library_scan":
                stats[f"{job_type}_{status}"] = stats.get(f"{job_type}_{status}", 0) + 1

        return stats

    @staticmethod
    async def cleanup_old_jobs(db: AsyncSession, older_than_days: int = 30) -> int:
        """Clean up completed jobs older than specified days.

        Args:
            db: Database session
            older_than_days: Remove jobs completed more than this many days ago

        Returns:
            Number of jobs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        # Delete completed jobs older than cutoff
        result = await db.execute(
            select(JobQueue).where(
                and_(JobQueue.status == "completed", JobQueue.completed_at < cutoff_date)
            )
        )
        old_jobs = result.scalars().all()

        for job in old_jobs:
            await db.delete(job)

        await db.commit()

        deleted_count = len(old_jobs)
        logger.info(f"Cleaned up {deleted_count} old jobs older than {older_than_days} days")
        return deleted_count

    @staticmethod
    def _should_schedule_scan(library_path: LibraryPath) -> bool:
        """Check if a library path should be scheduled for scanning.

        Args:
            library_path: LibraryPath model

        Returns:
            True if scan should be scheduled
        """
        if not library_path.enabled:
            return False

        # If never scanned, schedule immediately
        if library_path.last_scan is None:
            return True

        # Check if enough time has passed since last scan
        next_scan_time = library_path.last_scan + timedelta(hours=library_path.scan_interval_hours)
        return datetime.utcnow() >= next_scan_time

    @staticmethod
    async def _get_existing_job(db: AsyncSession, library_path_id: UUID) -> Optional[JobQueue]:
        """Check if there's already a pending or running job for this library path.

        Args:
            db: Database session
            library_path_id: Library path UUID

        Returns:
            Existing JobQueue or None
        """
        result = await db.execute(
            select(JobQueue).where(
                and_(
                    JobQueue.job_type == "library_scan",
                    JobQueue.status.in_(["pending", "running"]),
                    JobQueue.payload["library_path_id"].astext == str(library_path_id),
                )
            )
        )
        return result.scalar_one_or_none()


class SchedulerRunner:
    """Background scheduler that periodically schedules jobs."""

    def __init__(self, db_session_factory, check_interval_minutes: int = 5):
        """Initialize scheduler runner.

        Args:
            db_session_factory: Factory function to create database sessions
            check_interval_minutes: How often to check for scheduling (default 5 minutes)
        """
        self.db_session_factory = db_session_factory
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self._running = False
        self._task = None

    async def start(self):
        """Start the background scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Started background job scheduler (check interval: {self.check_interval}s)")

    async def stop(self):
        """Stop the background scheduler."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped background job scheduler")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self._running:
            try:
                async with self.db_session_factory() as db:
                    await JobScheduler.schedule_library_scans(db)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            # Wait for next check interval
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
