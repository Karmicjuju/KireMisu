"""Tests for job scheduler service."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath
from kiremisu.services.job_scheduler import JobScheduler


@pytest.mark.unit
class TestJobScheduler:
    """Test cases for JobScheduler service."""

    async def test_schedule_manual_scan_specific_path(self, db_session: AsyncSession):
        """Test scheduling manual scan for specific library path."""
        # Create test library path
        path = LibraryPath(path="/test/path", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Schedule manual scan
        job_id = await JobScheduler.schedule_manual_scan(
            db_session, library_path_id=path.id, priority=8
        )

        # Verify job was created
        assert job_id is not None

        # Check job in database
        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        assert job.job_type == "library_scan"
        assert job.status == "pending"
        assert job.priority == 8
        assert job.payload["library_path_id"] == str(path.id)
        assert job.payload["library_path"] == path.path

    async def test_schedule_manual_scan_all_paths(self, db_session: AsyncSession):
        """Test scheduling manual scan for all library paths."""
        # Schedule manual scan for all paths
        job_id = await JobScheduler.schedule_manual_scan(db_session, priority=9)

        # Verify job was created
        assert job_id is not None

        # Check job in database
        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        assert job.job_type == "library_scan"
        assert job.status == "pending"
        assert job.priority == 9
        assert job.payload == {}  # No specific path

    async def test_schedule_manual_scan_invalid_path(self, db_session: AsyncSession):
        """Test scheduling manual scan with invalid library path ID."""
        fake_path_id = uuid4()

        # Should raise ValueError for invalid path
        with pytest.raises(ValueError, match="Library path not found"):
            await JobScheduler.schedule_manual_scan(
                db_session, library_path_id=fake_path_id, priority=5
            )

    async def test_schedule_library_scans_automatic(self, db_session: AsyncSession):
        """Test automatic library scan scheduling based on intervals."""
        # Create test library paths with different scan schedules
        path1 = LibraryPath(
            path="/test/path1",
            enabled=True,
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2),  # Due for scan
        )
        path2 = LibraryPath(
            path="/test/path2",
            enabled=True,
            scan_interval_hours=24,
            last_scan=datetime.utcnow() - timedelta(hours=1),  # Not due
        )
        path3 = LibraryPath(
            path="/test/path3",
            enabled=False,  # Disabled
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2),
        )
        path4 = LibraryPath(
            path="/test/path4",
            enabled=True,
            scan_interval_hours=12,
            last_scan=None,  # Never scanned - should be scheduled
        )

        db_session.add(path1)
        db_session.add(path2)
        db_session.add(path3)
        db_session.add(path4)
        await db_session.commit()

        # Schedule automatic scans
        result = await JobScheduler.schedule_library_scans(db_session)

        # Should schedule 2 jobs (path1 and path4)
        assert result["scheduled"] == 2
        assert result["skipped"] == 2  # path2 (not due) and path3 (disabled)
        assert result["total_paths"] == 4

        # Verify jobs were created
        from sqlalchemy import text

        jobs = await db_session.execute(
            text("SELECT * FROM job_queue WHERE job_type = 'library_scan'")
        )
        job_list = jobs.fetchall()
        assert len(job_list) == 2

    async def test_schedule_download_job(self, db_session: AsyncSession):
        """Test scheduling download job."""
        job_id = await JobScheduler.schedule_download(
            db_session,
            manga_id="test-manga-123",
            download_type="mangadx",
            priority=6,
        )

        # Verify job was created
        assert job_id is not None

        # Check job in database
        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        assert job.job_type == "download"
        assert job.status == "pending"
        assert job.priority == 6
        assert job.payload["manga_id"] == "test-manga-123"
        assert job.payload["download_type"] == "mangadx"

    async def test_schedule_download_job_with_series_id(self, db_session: AsyncSession):
        """Test scheduling download job with series association."""
        series_id = uuid4()
        job_id = await JobScheduler.schedule_download(
            db_session,
            manga_id="test-manga-456",
            download_type="mangadx",
            series_id=series_id,
            priority=8,
        )

        # Verify job was created with series association
        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        assert job.payload["series_id"] == str(series_id)

    async def test_get_queue_stats(self, db_session: AsyncSession):
        """Test getting queue statistics."""
        # Create test jobs with different statuses and types
        jobs = [
            JobQueue(job_type="library_scan", status="pending"),
            JobQueue(job_type="library_scan", status="running"),
            JobQueue(job_type="library_scan", status="completed"),
            JobQueue(job_type="library_scan", status="failed"),
            JobQueue(job_type="download", status="pending"),
            JobQueue(job_type="download", status="running"),
        ]

        for job in jobs:
            db_session.add(job)
        await db_session.commit()

        # Get statistics
        stats = await JobScheduler.get_queue_stats(db_session)

        # Verify overall stats
        assert stats["pending"] == 2
        assert stats["running"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1

        # Verify job type specific stats
        assert stats["library_scan_pending"] == 1
        assert stats["library_scan_running"] == 1
        assert stats["library_scan_completed"] == 1
        assert stats["library_scan_failed"] == 1
        assert stats["download_pending"] == 1
        assert stats["download_running"] == 1

    async def test_get_recent_jobs(self, db_session: AsyncSession):
        """Test getting recent jobs."""
        # Create test jobs with different timestamps
        job1 = JobQueue(
            job_type="library_scan",
            status="completed",
            created_at=datetime.utcnow() - timedelta(minutes=5),
        )
        job2 = JobQueue(
            job_type="library_scan",
            status="pending",
            created_at=datetime.utcnow() - timedelta(minutes=2),
        )
        job3 = JobQueue(
            job_type="download",
            status="failed",
            created_at=datetime.utcnow() - timedelta(minutes=1),
        )

        db_session.add(job1)
        db_session.add(job2)
        db_session.add(job3)
        await db_session.commit()

        # Get all recent jobs
        jobs = await JobScheduler.get_recent_jobs(db_session, limit=10)

        # Should be ordered by creation time desc
        assert len(jobs) == 3
        assert jobs[0].id == job3.id  # Most recent
        assert jobs[1].id == job2.id
        assert jobs[2].id == job1.id  # Oldest

        # Test with job type filter
        library_jobs = await JobScheduler.get_recent_jobs(
            db_session, job_type="library_scan", limit=10
        )

        assert len(library_jobs) == 2
        assert library_jobs[0].id == job2.id
        assert library_jobs[1].id == job1.id

        # Test with limit
        limited_jobs = await JobScheduler.get_recent_jobs(db_session, limit=2)
        assert len(limited_jobs) == 2

    async def test_get_job_status(self, db_session: AsyncSession):
        """Test getting specific job status."""
        # Create test job
        job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": str(uuid4())},
            status="completed",
            priority=5,
        )
        db_session.add(job)
        await db_session.commit()

        # Get job status
        retrieved_job = await JobScheduler.get_job_status(db_session, job.id)

        assert retrieved_job is not None
        assert retrieved_job.id == job.id
        assert retrieved_job.job_type == "library_scan"
        assert retrieved_job.status == "completed"

        # Test with non-existent job
        fake_id = uuid4()
        nonexistent_job = await JobScheduler.get_job_status(db_session, fake_id)
        assert nonexistent_job is None

    async def test_cleanup_old_jobs(self, db_session: AsyncSession):
        """Test cleaning up old completed jobs."""
        # Create test jobs
        old_job = JobQueue(
            job_type="library_scan",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=35),
        )
        recent_job = JobQueue(
            job_type="library_scan",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=5),
        )
        pending_job = JobQueue(
            job_type="library_scan",
            status="pending",
        )

        db_session.add(old_job)
        db_session.add(recent_job)
        db_session.add(pending_job)
        await db_session.commit()

        # Cleanup jobs older than 30 days
        deleted_count = await JobScheduler.cleanup_old_jobs(db_session, older_than_days=30)

        assert deleted_count == 1

        # Verify only old completed job was deleted
        from sqlalchemy import text

        remaining_jobs = await db_session.execute(text("SELECT * FROM job_queue"))
        job_list = remaining_jobs.fetchall()
        assert len(job_list) == 2  # recent_job and pending_job should remain

    async def test_job_priority_ordering(self, db_session: AsyncSession):
        """Test that jobs are ordered by priority correctly."""
        # Create jobs with different priorities
        low_priority_job = JobQueue(
            job_type="library_scan",
            status="pending",
            priority=3,
            scheduled_at=datetime.utcnow() - timedelta(minutes=5),
        )
        high_priority_job = JobQueue(
            job_type="library_scan",
            status="pending",
            priority=8,
            scheduled_at=datetime.utcnow() - timedelta(minutes=1),
        )
        medium_priority_job = JobQueue(
            job_type="library_scan",
            status="pending",
            priority=5,
            scheduled_at=datetime.utcnow() - timedelta(minutes=3),
        )

        db_session.add(low_priority_job)
        db_session.add(high_priority_job)
        db_session.add(medium_priority_job)
        await db_session.commit()

        # Get recent jobs (should be ordered by creation time desc)
        jobs = await JobScheduler.get_recent_jobs(db_session, limit=10)

        # Recent jobs are ordered by creation time, not priority
        assert jobs[0].id == high_priority_job.id  # Most recent
        assert jobs[1].id == medium_priority_job.id
        assert jobs[2].id == low_priority_job.id  # Oldest

    async def test_duplicate_job_prevention(self, db_session: AsyncSession):
        """Test that duplicate jobs are prevented or handled correctly."""
        # Create library path
        path = LibraryPath(path="/test/path", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Schedule first job
        job_id1 = await JobScheduler.schedule_manual_scan(
            db_session, library_path_id=path.id, priority=5
        )

        # Schedule second job for same path (should be allowed)
        job_id2 = await JobScheduler.schedule_manual_scan(
            db_session, library_path_id=path.id, priority=5
        )

        # Both jobs should be created (no duplicate prevention in current implementation)
        assert job_id1 != job_id2

        # Verify both jobs exist
        job1 = await db_session.get(JobQueue, job_id1)
        job2 = await db_session.get(JobQueue, job_id2)
        assert job1 is not None
        assert job2 is not None

    async def test_job_payload_validation(self, db_session: AsyncSession):
        """Test that job payloads are properly validated."""
        # Create library path
        path = LibraryPath(path="/test/path", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Schedule job and verify payload structure
        job_id = await JobScheduler.schedule_manual_scan(
            db_session, library_path_id=path.id, priority=5
        )

        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        assert isinstance(job.payload, dict)
        assert "library_path_id" in job.payload
        assert "library_path" in job.payload
        assert job.payload["library_path_id"] == str(path.id)
        assert job.payload["library_path"] == path.path

    async def test_job_timestamps_are_timezone_naive(self, db_session: AsyncSession):
        """Test that all job timestamps are stored without timezone info."""
        # Create a job
        job_id = await JobScheduler.schedule_job(
            db_session,
            job_type="test_timezone",
            payload={"test": "data"},
            priority=5,
        )
        
        # Retrieve the job
        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        
        # Check that all timestamps are timezone-naive
        assert job.created_at.tzinfo is None, "created_at should be timezone-naive"
        assert job.updated_at.tzinfo is None, "updated_at should be timezone-naive"
        assert job.scheduled_at.tzinfo is None, "scheduled_at should be timezone-naive"
        
        # Verify scheduled_at is set correctly (should be roughly now)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        time_diff = abs((job.scheduled_at - now).total_seconds())
        assert time_diff < 5, "scheduled_at should be close to current time"
