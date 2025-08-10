"""Comprehensive tests for WatchingService functionality."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Series, JobQueue
from kiremisu.services.watching_service import WatchingService, WatchingScheduler


class TestWatchingService:
    """Test suite for WatchingService functionality."""

    async def test_toggle_watch_enable_success(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test successfully enabling watch status for a series."""
        # Verify initial state
        assert not sample_series.watching_enabled
        original_updated_at = sample_series.updated_at
        
        # Enable watching
        updated_series = await WatchingService.toggle_watch(
            db=db_session, series_id=sample_series.id, enabled=True
        )
        
        assert updated_series.id == sample_series.id
        assert updated_series.watching_enabled is True
        assert updated_series.last_watched_check is None  # Reset when enabling
        assert updated_series.updated_at > original_updated_at
        
        # Verify persistence
        await db_session.refresh(sample_series)
        assert sample_series.watching_enabled is True
        assert sample_series.last_watched_check is None

    async def test_toggle_watch_disable_success(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test successfully disabling watch status for a series."""
        # First enable watching
        sample_series.watching_enabled = True
        sample_series.last_watched_check = datetime.now(timezone.utc).replace(tzinfo=None)
        await db_session.commit()
        
        original_check_time = sample_series.last_watched_check
        
        # Disable watching
        updated_series = await WatchingService.toggle_watch(
            db=db_session, series_id=sample_series.id, enabled=False
        )
        
        assert updated_series.watching_enabled is False
        # last_watched_check should be preserved when disabling
        assert updated_series.last_watched_check == original_check_time

    async def test_toggle_watch_nonexistent_series(
        self, db_session: AsyncSession
    ):
        """Test toggling watch for non-existent series raises ValueError."""
        fake_id = uuid4()
        
        with pytest.raises(ValueError, match="Series not found"):
            await WatchingService.toggle_watch(
                db=db_session, series_id=fake_id, enabled=True
            )

    async def test_toggle_watch_idempotent_enable(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that enabling watching multiple times is idempotent."""
        # First enable
        await WatchingService.toggle_watch(
            db=db_session, series_id=sample_series.id, enabled=True
        )
        
        first_updated_at = sample_series.updated_at
        
        # Enable again
        updated_series = await WatchingService.toggle_watch(
            db=db_session, series_id=sample_series.id, enabled=True
        )
        
        assert updated_series.watching_enabled is True
        # Should still update the timestamp
        assert updated_series.updated_at > first_updated_at

    async def test_schedule_update_checks_no_watched_series(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test scheduling when no series are being watched."""
        # Ensure series is not being watched
        sample_series.watching_enabled = False
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == 0
        assert result["skipped"] == 0
        assert result["total_watched"] == 0

    async def test_schedule_update_checks_success(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test successfully scheduling update checks for watched series."""
        # Set up watched series with MangaDx ID
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-mangadx-123"
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == 1
        assert result["skipped"] == 0
        assert result["total_watched"] == 1
        
        # Verify job was created
        job_result = await db_session.execute(
            select(JobQueue).where(JobQueue.job_type == "chapter_update_check")
        )
        jobs = job_result.scalars().all()
        
        assert len(jobs) == 1
        job = jobs[0]
        
        assert job.job_type == "chapter_update_check"
        assert job.payload["series_id"] == str(sample_series.id)
        assert job.payload["mangadx_id"] == sample_series.mangadx_id
        assert job.payload["series_title"] == sample_series.title_primary
        assert job.priority == 2
        assert job.status == "pending"

    async def test_schedule_update_checks_no_mangadx_id(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that series without MangaDx ID are not scheduled."""
        # Set up watched series without MangaDx ID
        sample_series.watching_enabled = True
        sample_series.mangadx_id = None
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == 0
        assert result["skipped"] == 0
        assert result["total_watched"] == 0

    async def test_schedule_update_checks_existing_job_skip(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that existing pending jobs prevent new job creation."""
        # Set up watched series
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-mangadx-123"
        await db_session.commit()
        
        # Create existing job
        existing_job = JobQueue(
            job_type="chapter_update_check",
            payload={"series_id": str(sample_series.id)},
            status="pending"
        )
        db_session.add(existing_job)
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == 0
        assert result["skipped"] == 1
        assert result["total_watched"] == 1

    async def test_schedule_update_checks_running_job_skip(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that running jobs also prevent new job creation."""
        # Set up watched series
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-mangadx-123"
        await db_session.commit()
        
        # Create running job
        running_job = JobQueue(
            job_type="chapter_update_check",
            payload={"series_id": str(sample_series.id)},
            status="running"
        )
        db_session.add(running_job)
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == 0
        assert result["skipped"] == 1
        assert result["total_watched"] == 1

    async def test_schedule_update_checks_completed_job_allows_new(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that completed jobs don't prevent new job creation."""
        # Set up watched series
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-mangadx-123"
        await db_session.commit()
        
        # Create completed job
        completed_job = JobQueue(
            job_type="chapter_update_check",
            payload={"series_id": str(sample_series.id)},
            status="completed"
        )
        db_session.add(completed_job)
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == 1
        assert result["skipped"] == 0
        assert result["total_watched"] == 1

    async def test_get_watched_series_empty(
        self, db_session: AsyncSession
    ):
        """Test getting watched series when none exist."""
        result = await WatchingService.get_watched_series(db_session)
        assert result == []

    async def test_get_watched_series_with_data(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test getting watched series with data."""
        # Enable watching
        sample_series.watching_enabled = True
        await db_session.commit()
        
        result = await WatchingService.get_watched_series(db_session)
        
        assert len(result) == 1
        assert result[0].id == sample_series.id
        assert result[0].watching_enabled is True

    async def test_get_watched_series_pagination(
        self, db_session: AsyncSession
    ):
        """Test pagination of watched series."""
        # Create multiple watched series
        watched_series = []
        for i in range(5):
            series = Series(
                title_primary=f"Watched Series {i}",
                watching_enabled=True,
                file_path=f"/test/path/{i}"
            )
            db_session.add(series)
            watched_series.append(series)
        
        await db_session.commit()
        
        # Test first page
        page1 = await WatchingService.get_watched_series(
            db_session, skip=0, limit=2
        )
        assert len(page1) == 2
        
        # Test second page
        page2 = await WatchingService.get_watched_series(
            db_session, skip=2, limit=2
        )
        assert len(page2) == 2
        
        # Ensure different series
        page1_ids = {s.id for s in page1}
        page2_ids = {s.id for s in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_get_watched_series_count(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test getting count of watched series."""
        # Initially no watched series
        count = await WatchingService.get_watched_series_count(db_session)
        assert count == 0
        
        # Enable watching
        sample_series.watching_enabled = True
        await db_session.commit()
        
        count = await WatchingService.get_watched_series_count(db_session)
        assert count == 1

    async def test_get_watching_stats_comprehensive(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test getting comprehensive watching statistics."""
        # Set up test data
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-id-123"
        await db_session.commit()
        
        # Create a pending update check job
        job = JobQueue(
            job_type="chapter_update_check",
            payload={"series_id": str(sample_series.id)},
            status="pending"
        )
        db_session.add(job)
        await db_session.commit()
        
        stats = await WatchingService.get_watching_stats(db_session)
        
        assert stats["watched_series"] == 1
        assert stats["eligible_series"] == 1  # Has MangaDx ID
        assert stats["pending_update_checks"] == 1

    async def test_get_watching_stats_edge_cases(
        self, db_session: AsyncSession
    ):
        """Test watching stats with edge cases."""
        # Create series without MangaDx ID
        non_eligible_series = Series(
            title_primary="Non-Eligible Series",
            watching_enabled=True,  # Watching enabled but no MangaDx ID
            file_path="/test/path/non-eligible",
            mangadx_id=None
        )
        db_session.add(non_eligible_series)
        await db_session.commit()
        
        stats = await WatchingService.get_watching_stats(db_session)
        
        assert stats["watched_series"] == 1
        assert stats["eligible_series"] == 0  # No MangaDx ID
        assert stats["pending_update_checks"] == 0

    async def test_get_existing_update_job_found(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test finding existing update job."""
        # Create a job
        job = JobQueue(
            job_type="chapter_update_check",
            payload={"series_id": str(sample_series.id)},
            status="pending"
        )
        db_session.add(job)
        await db_session.commit()
        
        existing_job = await WatchingService._get_existing_update_job(
            db_session, sample_series.id
        )
        
        assert existing_job is not None
        assert existing_job.id == job.id

    async def test_get_existing_update_job_not_found(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test when no existing update job is found."""
        existing_job = await WatchingService._get_existing_update_job(
            db_session, sample_series.id
        )
        
        assert existing_job is None

    async def test_get_existing_update_job_ignore_completed(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that completed jobs are ignored when checking for existing jobs."""
        # Create a completed job
        job = JobQueue(
            job_type="chapter_update_check",
            payload={"series_id": str(sample_series.id)},
            status="completed"
        )
        db_session.add(job)
        await db_session.commit()
        
        existing_job = await WatchingService._get_existing_update_job(
            db_session, sample_series.id
        )
        
        assert existing_job is None  # Should ignore completed jobs

    async def test_schedule_update_checks_multiple_series(
        self, db_session: AsyncSession
    ):
        """Test scheduling for multiple watched series."""
        # Create multiple watched series
        watched_count = 3
        for i in range(watched_count):
            series = Series(
                title_primary=f"Watched Series {i}",
                watching_enabled=True,
                mangadx_id=f"test-id-{i}",
                file_path=f"/test/path/{i}"
            )
            db_session.add(series)
        
        await db_session.commit()
        
        result = await WatchingService.schedule_update_checks(db_session)
        
        assert result["scheduled"] == watched_count
        assert result["skipped"] == 0
        assert result["total_watched"] == watched_count
        
        # Verify all jobs were created
        job_result = await db_session.execute(
            select(func.count(JobQueue.id)).where(
                JobQueue.job_type == "chapter_update_check"
            )
        )
        job_count = job_result.scalar()
        assert job_count == watched_count


class TestWatchingScheduler:
    """Test suite for WatchingScheduler functionality."""

    def test_scheduler_initialization(self):
        """Test scheduler initialization with different parameters."""
        mock_session_factory = AsyncMock()
        
        # Default parameters
        scheduler = WatchingScheduler(mock_session_factory)
        assert scheduler.db_session_factory == mock_session_factory
        assert scheduler.check_interval == 3600  # 60 minutes in seconds
        assert not scheduler._running
        assert scheduler._task is None
        
        # Custom parameters
        scheduler_custom = WatchingScheduler(mock_session_factory, check_interval_minutes=30)
        assert scheduler_custom.check_interval == 1800  # 30 minutes in seconds

    async def test_scheduler_start_stop(self):
        """Test scheduler start and stop functionality."""
        mock_session_factory = AsyncMock()
        scheduler = WatchingScheduler(mock_session_factory, check_interval_minutes=1)
        
        # Test start
        await scheduler.start()
        assert scheduler._running is True
        assert scheduler._task is not None
        
        # Test double start (should warn but not fail)
        await scheduler.start()  # Should handle gracefully
        
        # Test stop
        await scheduler.stop()
        assert scheduler._running is False
        
        # Test double stop (should handle gracefully)
        await scheduler.stop()

    async def test_scheduler_run_loop_success(self):
        """Test scheduler run loop with successful execution."""
        mock_session = AsyncMock()
        mock_session_factory = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        scheduler = WatchingScheduler(mock_session_factory, check_interval_minutes=0.01)  # Very short interval
        
        with patch.object(WatchingService, 'schedule_update_checks') as mock_schedule:
            mock_schedule.return_value = {"scheduled": 1, "skipped": 0, "total_watched": 1}
            
            # Start scheduler briefly
            await scheduler.start()
            await asyncio.sleep(0.1)  # Let it run briefly
            await scheduler.stop()
            
            # Verify schedule_update_checks was called
            assert mock_schedule.call_count >= 1

    async def test_scheduler_error_handling(self):
        """Test scheduler error handling in run loop."""
        mock_session = AsyncMock()
        mock_session_factory = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        scheduler = WatchingScheduler(mock_session_factory, check_interval_minutes=0.01)
        
        with patch.object(WatchingService, 'schedule_update_checks') as mock_schedule:
            mock_schedule.side_effect = Exception("Database error")
            
            with patch('kiremisu.services.watching_service.logger') as mock_logger:
                # Start scheduler briefly
                await scheduler.start()
                await asyncio.sleep(0.1)  # Let it run briefly
                await scheduler.stop()
                
                # Verify error was logged
                mock_logger.error.assert_called()

    async def test_scheduler_cancellation_handling(self):
        """Test scheduler handles cancellation gracefully."""
        mock_session_factory = AsyncMock()
        scheduler = WatchingScheduler(mock_session_factory, check_interval_minutes=1)
        
        # Mock asyncio.sleep to raise CancelledError
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()
            
            await scheduler.start()
            await asyncio.sleep(0.1)  # Let it try to run
            await scheduler.stop()
            
            # Should handle cancellation gracefully
            assert not scheduler._running

    async def test_scheduler_integration_with_service(
        self, async_session_factory, sample_series: Series
    ):
        """Test scheduler integration with actual WatchingService."""
        # This would be a more realistic integration test
        scheduler = WatchingScheduler(async_session_factory, check_interval_minutes=0.01)
        
        # Set up watched series
        async with async_session_factory() as db:
            sample_series.watching_enabled = True
            sample_series.mangadx_id = "test-integration-id"
            await db.commit()
        
        try:
            await scheduler.start()
            await asyncio.sleep(0.2)  # Let scheduler run a few times
        finally:
            await scheduler.stop()
        
        # Verify jobs were created
        async with async_session_factory() as db:
            job_result = await db.execute(
                select(func.count(JobQueue.id)).where(
                    JobQueue.job_type == "chapter_update_check"
                )
            )
            job_count = job_result.scalar()
            assert job_count >= 1  # At least one job should have been created


# Additional test helpers and fixtures
@pytest.fixture
async def async_session_factory(db_session: AsyncSession):
    """Factory for creating async database sessions in tests."""
    async def factory():
        return db_session
    return factory