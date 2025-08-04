"""Tests for job scheduler service."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath
from kiremisu.services.job_scheduler import JobScheduler, SchedulerRunner


class TestJobScheduler:
    """Test cases for JobScheduler service."""

    async def test_schedule_library_scans_with_due_paths(self, db_session: AsyncSession):
        """Test scheduling scans for paths that are due."""
        # Create test library paths - one due, one not due
        import uuid
        path1 = LibraryPath(
            path=f"/test/path1_{uuid.uuid4()}",
            enabled=True,
            scan_interval_hours=1,  
            last_scan=datetime.utcnow() - timedelta(hours=2)  # Due for scan
        )
        path2 = LibraryPath(
            path=f"/test/path2_{uuid.uuid4()}",
            enabled=True,
            scan_interval_hours=24,
            last_scan=datetime.utcnow() - timedelta(hours=1)  # Not due
        )
        path3 = LibraryPath(
            path=f"/test/path3_{uuid.uuid4()}",
            enabled=True,
            scan_interval_hours=1,
            last_scan=None  # Never scanned, should be scheduled
        )
        path4 = LibraryPath(
            path=f"/test/path4_{uuid.uuid4()}",
            enabled=False,  # Disabled, should not be scheduled
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2)
        )

        db_session.add(path1)
        db_session.add(path2)
        db_session.add(path3)
        db_session.add(path4)
        await db_session.commit()

        # Schedule scans
        result = await JobScheduler.schedule_library_scans(db_session)

        # Should schedule path1 (due) and path3 (never scanned)
        assert result["scheduled"] == 2
        assert result["skipped"] == 1  # path2 not due
        assert result["total_paths"] == 3  # path4 disabled, not counted

        # Verify jobs were created
        jobs = await db_session.execute(
            "SELECT * FROM job_queue WHERE job_type = 'library_scan'"
        )
        job_list = jobs.fetchall()
        assert len(job_list) == 2

    async def test_schedule_library_scans_skips_existing_jobs(self, db_session: AsyncSession):
        """Test that scheduling skips paths with existing pending jobs."""
        # Create test library path
        path = LibraryPath(
            path="/test/path",
            enabled=True,
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2)  # Due for scan
        )
        db_session.add(path)
        await db_session.commit()

        # Create existing pending job for this path
        existing_job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": str(path.id)},
            status="pending"
        )
        db_session.add(existing_job)
        await db_session.commit()

        # Schedule scans
        result = await JobScheduler.schedule_library_scans(db_session)

        # Should skip the path due to existing job
        assert result["scheduled"] == 0
        assert result["skipped"] == 1
        assert result["total_paths"] == 1

    async def test_schedule_manual_scan_specific_path(self, db_session: AsyncSession):
        """Test scheduling manual scan for specific path."""
        # Create test library path
        path = LibraryPath(
            path="/test/path",
            enabled=True,
            scan_interval_hours=24
        )
        db_session.add(path)
        await db_session.commit()

        # Schedule manual scan
        job_id = await JobScheduler.schedule_manual_scan(db_session, path.id, priority=8)

        # Verify job was created
        job = await JobScheduler.get_job_status(db_session, job_id)
        assert job is not None
        assert job.job_type == "library_scan"
        assert job.priority == 8
        assert job.payload["library_path_id"] == str(path.id)
        assert job.payload["library_path"] == path.path

    async def test_schedule_manual_scan_all_paths(self, db_session: AsyncSession):
        """Test scheduling manual scan for all paths."""
        # Schedule manual scan for all paths
        job_id = await JobScheduler.schedule_manual_scan(db_session, priority=9)

        # Verify job was created
        job = await JobScheduler.get_job_status(db_session, job_id)
        assert job is not None
        assert job.job_type == "library_scan"
        assert job.priority == 9
        assert job.payload == {}  # Empty payload for all paths

    async def test_schedule_manual_scan_invalid_path(self, db_session: AsyncSession):
        """Test scheduling manual scan with invalid path ID."""
        invalid_path_id = uuid4()

        with pytest.raises(ValueError, match="Library path not found"):
            await JobScheduler.schedule_manual_scan(db_session, invalid_path_id)

    async def test_get_recent_jobs(self, db_session: AsyncSession):
        """Test getting recent jobs."""
        # Create test jobs
        job1 = JobQueue(
            job_type="library_scan",
            status="completed",
            created_at=datetime.utcnow() - timedelta(minutes=5)
        )
        job2 = JobQueue(
            job_type="library_scan",
            status="pending",
            created_at=datetime.utcnow() - timedelta(minutes=2)
        )
        job3 = JobQueue(
            job_type="other_job",
            status="failed",
            created_at=datetime.utcnow() - timedelta(minutes=1)
        )

        db_session.add(job1)
        db_session.add(job2)
        db_session.add(job3)
        await db_session.commit()

        # Get all recent jobs
        all_jobs = await JobScheduler.get_recent_jobs(db_session)
        assert len(all_jobs) == 3
        # Should be ordered by creation time desc
        assert all_jobs[0].id == job3.id
        assert all_jobs[1].id == job2.id
        assert all_jobs[2].id == job1.id

        # Get recent jobs filtered by type
        scan_jobs = await JobScheduler.get_recent_jobs(db_session, job_type="library_scan")
        assert len(scan_jobs) == 2

        # Get limited number of jobs
        limited_jobs = await JobScheduler.get_recent_jobs(db_session, limit=2)
        assert len(limited_jobs) == 2

    async def test_get_queue_stats(self, db_session: AsyncSession):
        """Test getting queue statistics."""
        # Create test jobs
        jobs = [
            JobQueue(job_type="library_scan", status="pending"),
            JobQueue(job_type="library_scan", status="running"),
            JobQueue(job_type="library_scan", status="failed"),
            JobQueue(job_type="other_job", status="pending"),
            JobQueue(job_type="other_job", status="completed"),  # Completed jobs not counted
        ]

        for job in jobs:
            db_session.add(job)
        await db_session.commit()

        # Get stats
        stats = await JobScheduler.get_queue_stats(db_session)

        assert stats["pending"] == 2
        assert stats["running"] == 1
        assert stats["failed"] == 1
        assert stats["library_scan_pending"] == 1
        assert stats["library_scan_running"] == 1
        assert stats["library_scan_failed"] == 1

    async def test_cleanup_old_jobs(self, db_session: AsyncSession):
        """Test cleaning up old completed jobs."""
        # Create test jobs
        old_job = JobQueue(
            job_type="library_scan",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=35)
        )
        recent_job = JobQueue(
            job_type="library_scan",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=5)
        )
        pending_job = JobQueue(
            job_type="library_scan",
            status="pending"
        )

        db_session.add(old_job)
        db_session.add(recent_job)
        db_session.add(pending_job)
        await db_session.commit()

        # Cleanup jobs older than 30 days
        deleted_count = await JobScheduler.cleanup_old_jobs(db_session, older_than_days=30)

        assert deleted_count == 1

        # Verify only old completed job was deleted
        remaining_jobs = await JobScheduler.get_recent_jobs(db_session)
        remaining_ids = [job.id for job in remaining_jobs]
        assert old_job.id not in remaining_ids
        assert recent_job.id in remaining_ids
        assert pending_job.id in remaining_ids

    def test_should_schedule_scan_disabled_path(self):
        """Test should_schedule_scan with disabled path."""
        path = LibraryPath(
            path="/test/path",
            enabled=False,
            scan_interval_hours=1
        )

        assert not JobScheduler._should_schedule_scan(path)

    def test_should_schedule_scan_never_scanned(self):
        """Test should_schedule_scan with never scanned path."""
        path = LibraryPath(
            path="/test/path",
            enabled=True,
            scan_interval_hours=24,
            last_scan=None
        )

        assert JobScheduler._should_schedule_scan(path)

    def test_should_schedule_scan_due_for_scan(self):
        """Test should_schedule_scan with path due for scan."""
        path = LibraryPath(
            path="/test/path",
            enabled=True,
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2)
        )

        assert JobScheduler._should_schedule_scan(path)

    def test_should_schedule_scan_not_due(self):
        """Test should_schedule_scan with path not due for scan."""
        path = LibraryPath(
            path="/test/path",
            enabled=True,
            scan_interval_hours=24,
            last_scan=datetime.utcnow() - timedelta(hours=1)
        )

        assert not JobScheduler._should_schedule_scan(path)


class TestSchedulerRunner:
    """Test cases for SchedulerRunner background service."""

    @pytest.fixture
    def mock_db_session_factory(self):
        """Mock database session factory."""
        mock_session = AsyncMock()
        mock_factory = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_factory

    async def test_scheduler_runner_start_stop(self, mock_db_session_factory):
        """Test starting and stopping scheduler runner."""
        runner = SchedulerRunner(mock_db_session_factory, check_interval_minutes=1)

        # Start runner
        await runner.start()
        assert runner._running is True
        assert runner._task is not None

        # Stop runner
        await runner.stop()
        assert runner._running is False

    async def test_scheduler_runner_already_running(self, mock_db_session_factory):
        """Test starting runner when already running."""
        runner = SchedulerRunner(mock_db_session_factory, check_interval_minutes=1)

        await runner.start()
        
        # Try to start again - should not create new task
        old_task = runner._task
        await runner.start()
        assert runner._task is old_task

        await runner.stop()

    async def test_scheduler_runner_schedules_jobs(self, mock_db_session_factory):
        """Test that scheduler runner calls job scheduling."""
        mock_session = mock_db_session_factory.return_value.__aenter__.return_value
        
        # Mock the schedule_library_scans method
        original_schedule = JobScheduler.schedule_library_scans
        JobScheduler.schedule_library_scans = AsyncMock(return_value={"scheduled": 1, "skipped": 0})
        
        try:
            runner = SchedulerRunner(mock_db_session_factory, check_interval_minutes=0.01)  # Very short interval
            
            await runner.start()
            
            # Wait a bit for the scheduler to run
            await asyncio.sleep(0.1)
            
            await runner.stop()
            
            # Verify schedule_library_scans was called
            JobScheduler.schedule_library_scans.assert_called()
            
        finally:
            # Restore original method
            JobScheduler.schedule_library_scans = original_schedule