"""Watching service for managing series watching functionality."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, Series

logger = logging.getLogger(__name__)


class WatchingService:
    """Service for managing series watching and scheduling update checks."""

    @staticmethod
    async def toggle_watch(db: AsyncSession, series_id: UUID, enabled: bool) -> Series:
        """Toggle watching status for a series.

        Args:
            db: Database session
            series_id: Series UUID to toggle
            enabled: Whether watching should be enabled

        Returns:
            Updated Series model

        Raises:
            ValueError: If series not found
        """
        logger.info(f"Toggling watch status for series {series_id}: enabled={enabled}")

        # Get the series
        result = await db.execute(select(Series).where(Series.id == series_id))
        series = result.scalar_one_or_none()

        if not series:
            raise ValueError(f"Series not found: {series_id}")

        # Update watching status and last check time
        update_values = {
            "watching_enabled": enabled,
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }

        # Reset last_watched_check when enabling to force immediate check
        if enabled:
            update_values["last_watched_check"] = None

        await db.execute(
            update(Series)
            .where(Series.id == series_id)
            .values(**update_values)
        )

        await db.commit()

        # Refresh the series to get updated values
        await db.refresh(series)

        logger.info(
            f"Successfully {'enabled' if enabled else 'disabled'} watching for series: {series.title_primary}"
        )
        return series

    @staticmethod
    async def schedule_update_checks(db: AsyncSession) -> Dict[str, int]:
        """Schedule chapter update check jobs for watched series.

        Args:
            db: Database session

        Returns:
            Dict with counts of scheduled jobs and skipped series
        """
        logger.info("Starting chapter update check job scheduling")

        # Get all series with watching enabled that have MangaDx IDs
        result = await db.execute(
            select(Series).where(
                and_(
                    Series.watching_enabled == True,
                    Series.mangadx_id.isnot(None),
                )
            )
        )
        watched_series = result.scalars().all()

        scheduled_count = 0
        skipped_count = 0

        for series in watched_series:
            # Check if there's already a pending/running job for this series
            existing_job = await WatchingService._get_existing_update_job(db, series.id)

            if existing_job:
                logger.debug(f"Skipping update check for series {series.id}: existing job found")
                skipped_count += 1
                continue

            # Create new chapter update check job
            job = JobQueue(
                job_type="chapter_update_check",
                payload={
                    "series_id": str(series.id),
                    "mangadx_id": series.mangadx_id,
                    "series_title": series.title_primary,
                },
                priority=2,  # Medium priority for automatic update checks
                scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

            db.add(job)
            scheduled_count += 1
            logger.info(f"Scheduled chapter update check job for series: {series.title_primary}")

        await db.commit()

        result = {
            "scheduled": scheduled_count,
            "skipped": skipped_count,
            "total_watched": len(watched_series),
        }

        logger.info(f"Chapter update check scheduling completed: {result}")
        return result

    @staticmethod
    async def get_watched_series(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Series]:
        """Get list of watched series.

        Args:
            db: Database session
            skip: Number of series to skip
            limit: Maximum number of series to return

        Returns:
            List of watched Series models
        """
        result = await db.execute(
            select(Series)
            .where(Series.watching_enabled == True)
            .order_by(Series.title_primary.asc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_watched_series_count(db: AsyncSession) -> int:
        """Get count of watched series.

        Args:
            db: Database session

        Returns:
            Number of series being watched
        """
        result = await db.execute(
            select(func.count(Series.id)).where(Series.watching_enabled == True)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_watching_stats(db: AsyncSession) -> Dict[str, int]:
        """Get statistics about watching system.

        Args:
            db: Database session

        Returns:
            Dict with watching statistics
        """
        # Count watched series
        watched_count = await WatchingService.get_watched_series_count(db)

        # Count series with MangaDx IDs (eligible for watching)
        result = await db.execute(
            select(func.count(Series.id)).where(Series.mangadx_id.isnot(None))
        )
        eligible_count = result.scalar() or 0

        # Count pending update check jobs
        result = await db.execute(
            select(func.count(JobQueue.id)).where(
                and_(
                    JobQueue.job_type == "chapter_update_check",
                    JobQueue.status == "pending",
                )
            )
        )
        pending_checks = result.scalar() or 0

        return {
            "watched_series": watched_count,
            "eligible_series": eligible_count,
            "pending_update_checks": pending_checks,
        }

    @staticmethod
    async def _get_existing_update_job(
        db: AsyncSession, series_id: UUID
    ) -> Optional[JobQueue]:
        """Check if there's already a pending or running update check job for this series.

        Args:
            db: Database session
            series_id: Series UUID

        Returns:
            Existing JobQueue or None
        """
        from sqlalchemy import text

        result = await db.execute(
            select(JobQueue)
            .where(
                and_(
                    JobQueue.job_type == "chapter_update_check",
                    JobQueue.status.in_(["pending", "running"]),
                    text("payload->>'series_id' = :series_id"),
                )
            )
            .params(series_id=str(series_id))
        )
        return result.scalar_one_or_none()


class WatchingScheduler:
    """Background scheduler for watching system that periodically checks for updates."""

    def __init__(self, db_session_factory, check_interval_minutes: int = 60):
        """Initialize watching scheduler.

        Args:
            db_session_factory: Factory function to create database sessions
            check_interval_minutes: How often to check for updates (default 60 minutes)
        """
        self.db_session_factory = db_session_factory
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self._running = False
        self._task = None

    async def start(self):
        """Start the background watching scheduler."""
        if self._running:
            logger.warning("Watching scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Started background watching scheduler (check interval: {self.check_interval}s)")

    async def stop(self):
        """Stop the background watching scheduler."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped background watching scheduler")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self._running:
            try:
                async with self.db_session_factory() as db:
                    await WatchingService.schedule_update_checks(db)

            except Exception as e:
                logger.error(f"Error in watching scheduler loop: {e}", exc_info=True)

            # Wait for next check interval
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break