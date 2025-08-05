"""Tests for job worker service."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath
from kiremisu.services.job_worker import JobWorker, JobWorkerRunner, JobExecutionError
from kiremisu.services.importer import ImportStats


class TestJobWorker:
    """Test cases for JobWorker service."""

    @pytest.fixture
    def mock_importer(self):
        """Mock importer service."""
        with patch("kiremisu.services.job_worker.ImporterService") as mock:
            mock_instance = mock.return_value
            mock_instance.scan_library_paths = AsyncMock(
                return_value=ImportStats(
                    series_found=2,
                    series_created=1,
                    series_updated=1,
                    chapters_found=10,
                    chapters_created=5,
                    chapters_updated=5,
                    errors=0,
                )
            )
            yield mock_instance

    async def test_execute_library_scan_job_success(self, db_session: AsyncSession, mock_importer):
        """Test successful execution of library scan job."""
        # Create test library path
        path = LibraryPath(path="/test/path", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Create test job
        job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": str(path.id), "library_path": path.path},
            status="pending",
        )
        db_session.add(job)
        await db_session.commit()

        # Execute job
        worker = JobWorker()
        result = await worker.execute_job(db_session, job)

        # Verify job was marked as completed
        await db_session.refresh(job)
        assert job.status == "completed"
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.error_message is None

        # Verify library path last_scan was updated
        await db_session.refresh(path)
        assert path.last_scan is not None

        # Verify result contains expected data
        assert result["job_type"] == "library_scan"
        assert result["library_path_id"] == str(path.id)
        assert "stats" in result

    async def test_execute_library_scan_job_all_paths(
        self, db_session: AsyncSession, mock_importer
    ):
        """Test execution of library scan job for all paths."""
        # Create test library paths
        path1 = LibraryPath(path="/test/path1", enabled=True, scan_interval_hours=24)
        path2 = LibraryPath(path="/test/path2", enabled=True, scan_interval_hours=24)
        db_session.add(path1)
        db_session.add(path2)
        await db_session.commit()

        # Create test job for all paths (no library_path_id)
        job = JobQueue(job_type="library_scan", payload={}, status="pending")
        db_session.add(job)
        await db_session.commit()

        # Execute job
        worker = JobWorker()
        result = await worker.execute_job(db_session, job)

        # Verify job was marked as completed
        await db_session.refresh(job)
        assert job.status == "completed"

        # Verify all enabled library paths had last_scan updated
        await db_session.refresh(path1)
        await db_session.refresh(path2)
        assert path1.last_scan is not None
        assert path2.last_scan is not None

        # Verify result
        assert result["job_type"] == "library_scan"
        assert result["library_path_id"] is None

    async def test_execute_job_unknown_type(self, db_session: AsyncSession):
        """Test execution of job with unknown type."""
        job = JobQueue(job_type="unknown_job", payload={}, status="pending")
        db_session.add(job)
        await db_session.commit()

        worker = JobWorker()

        with pytest.raises(JobExecutionError, match="Job execution failed"):
            await worker.execute_job(db_session, job)

        # Verify job was marked as failed
        await db_session.refresh(job)
        assert job.status == "failed"
        assert "Unknown job type" in job.error_message

    async def test_execute_job_with_retry(self, db_session: AsyncSession):
        """Test job execution with retry on failure."""
        # Create job with max_retries = 2
        job = JobQueue(
            job_type="library_scan",
            payload={
                "library_path_id": str(uuid4()),  # Invalid ID will cause failure
                "library_path": "/invalid/path",
            },
            status="pending",
            max_retries=2,
            retry_count=0,
        )
        db_session.add(job)
        await db_session.commit()

        worker = JobWorker()

        # First attempt should fail and set up retry
        with pytest.raises(JobExecutionError):
            await worker.execute_job(db_session, job)

        await db_session.refresh(job)
        assert job.status == "pending"  # Set back to pending for retry
        assert job.retry_count == 1
        assert job.error_message is not None

        # Second attempt should also fail and set up retry
        with pytest.raises(JobExecutionError):
            await worker.execute_job(db_session, job)

        await db_session.refresh(job)
        assert job.status == "pending"
        assert job.retry_count == 2

        # Third attempt should fail permanently
        with pytest.raises(JobExecutionError):
            await worker.execute_job(db_session, job)

        await db_session.refresh(job)
        assert job.status == "failed"
        assert job.retry_count == 2

    async def test_execute_job_marks_running_status(self, db_session: AsyncSession, mock_importer):
        """Test that job is marked as running during execution."""
        job = JobQueue(job_type="library_scan", payload={}, status="pending")
        db_session.add(job)
        await db_session.commit()

        # Mock importer to allow checking job status during execution
        async def check_running_status(*args, **kwargs):
            await db_session.refresh(job)
            assert job.status == "running"
            assert job.started_at is not None
            return mock_importer.scan_library_paths.return_value

        mock_importer.scan_library_paths.side_effect = check_running_status

        worker = JobWorker()
        await worker.execute_job(db_session, job)

    async def test_update_library_path_last_scan(self, db_session: AsyncSession):
        """Test updating last_scan for specific library path."""
        path = LibraryPath(path="/test/path", enabled=True, scan_interval_hours=24, last_scan=None)
        db_session.add(path)
        await db_session.commit()

        worker = JobWorker()
        await worker._update_library_path_last_scan(db_session, path.id)

        await db_session.refresh(path)
        assert path.last_scan is not None

    async def test_update_all_library_paths_last_scan(self, db_session: AsyncSession):
        """Test updating last_scan for all enabled library paths."""
        path1 = LibraryPath(
            path="/test/path1", enabled=True, scan_interval_hours=24, last_scan=None
        )
        path2 = LibraryPath(
            path="/test/path2", enabled=True, scan_interval_hours=24, last_scan=None
        )
        path3 = LibraryPath(
            path="/test/path3", enabled=False, scan_interval_hours=24, last_scan=None
        )

        db_session.add(path1)
        db_session.add(path2)
        db_session.add(path3)
        await db_session.commit()

        worker = JobWorker()
        await worker._update_all_library_paths_last_scan(db_session)

        await db_session.refresh(path1)
        await db_session.refresh(path2)
        await db_session.refresh(path3)

        # Only enabled paths should be updated
        assert path1.last_scan is not None
        assert path2.last_scan is not None
        assert path3.last_scan is None

    async def test_execute_download_job_success(self, db_session: AsyncSession):
        """Test successful execution of download job."""
        # Create test job
        job = JobQueue(
            job_type="download",
            payload={"manga_id": "test-manga-123", "download_type": "mangadx"},
            status="pending",
        )
        db_session.add(job)
        await db_session.commit()

        # Execute job
        worker = JobWorker()
        result = await worker.execute_job(db_session, job)

        # Verify job was marked as completed
        await db_session.refresh(job)
        assert job.status == "completed"
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.error_message is None

        # Verify result contains expected data
        assert result["job_type"] == "download"
        assert result["manga_id"] == "test-manga-123"
        assert result["download_type"] == "mangadx"
        assert result["status"] == "completed"

    async def test_execute_download_job_missing_manga_id(self, db_session: AsyncSession):
        """Test download job execution with missing manga_id."""
        job = JobQueue(
            job_type="download",
            payload={"download_type": "mangadx"},  # Missing manga_id
            status="pending",
        )
        db_session.add(job)
        await db_session.commit()

        worker = JobWorker()

        with pytest.raises(JobExecutionError, match="Job execution failed"):
            await worker.execute_job(db_session, job)

        # Verify job was marked as failed
        await db_session.refresh(job)
        assert job.status == "failed"
        assert "missing required 'manga_id'" in job.error_message

    async def test_execute_download_job_with_series_id(self, db_session: AsyncSession):
        """Test download job execution with series association."""
        from uuid import uuid4

        series_id = uuid4()
        job = JobQueue(
            job_type="download",
            payload={
                "manga_id": "test-manga-456",
                "download_type": "mangadx",
                "series_id": str(series_id),
            },
            status="pending",
        )
        db_session.add(job)
        await db_session.commit()

        # Execute job
        worker = JobWorker()
        result = await worker.execute_job(db_session, job)

        # Verify job was completed and series association preserved
        await db_session.refresh(job)
        assert job.status == "completed"
        assert result["series_id"] == str(series_id)


class TestJobWorkerRunner:
    """Test cases for JobWorkerRunner background service."""

    @pytest.fixture
    def mock_db_session_factory(self):
        """Mock database session factory."""
        mock_session = AsyncMock()
        mock_factory = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_factory

    async def test_worker_runner_start_stop(self, mock_db_session_factory):
        """Test starting and stopping worker runner."""
        runner = JobWorkerRunner(
            mock_db_session_factory, poll_interval_seconds=1, max_concurrent_jobs=2
        )

        # Start runner
        await runner.start()
        assert runner._running is True
        assert runner._task is not None

        # Stop runner
        await runner.stop()
        assert runner._running is False

    async def test_worker_runner_already_running(self, mock_db_session_factory):
        """Test starting runner when already running."""
        runner = JobWorkerRunner(mock_db_session_factory, poll_interval_seconds=1)

        await runner.start()

        # Try to start again - should not create new task
        old_task = runner._task
        await runner.start()
        assert runner._task is old_task

        await runner.stop()

    async def test_get_worker_status(self, mock_db_session_factory):
        """Test getting worker status."""
        runner = JobWorkerRunner(
            mock_db_session_factory, poll_interval_seconds=10, max_concurrent_jobs=5
        )

        status = await runner.get_worker_status()

        assert status["running"] is False
        assert status["active_jobs"] == 0
        assert status["max_concurrent_jobs"] == 5
        assert status["poll_interval_seconds"] == 10

        # Start runner and check status
        await runner.start()

        status = await runner.get_worker_status()
        assert status["running"] is True

        await runner.stop()

    async def test_process_available_jobs_with_pending_jobs(self, mock_db_session_factory):
        """Test processing available jobs."""
        # Create mock jobs
        job1 = MagicMock()
        job1.id = uuid4()
        job1.job_type = "library_scan"
        job1.priority = 5
        job1.scheduled_at = datetime.utcnow()
        job1.status = "pending"

        job2 = MagicMock()
        job2.id = uuid4()
        job2.job_type = "library_scan"
        job2.priority = 3
        job2.scheduled_at = datetime.utcnow()
        job2.status = "pending"

        # Mock database query to return jobs
        mock_session = mock_db_session_factory.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [job1, job2]
        mock_session.execute.return_value = mock_result

        runner = JobWorkerRunner(
            mock_db_session_factory, poll_interval_seconds=1, max_concurrent_jobs=2
        )

        # Process jobs (just check that it doesn't error)
        await runner._process_available_jobs()

        # Verify database was queried
        mock_session.execute.assert_called_once()

    async def test_concurrency_limit_respected(self, mock_db_session_factory):
        """Test that concurrency limit is respected."""
        runner = JobWorkerRunner(
            mock_db_session_factory, poll_interval_seconds=1, max_concurrent_jobs=2
        )

        # Simulate having 2 active jobs (at limit)
        runner._active_jobs = {MagicMock(), MagicMock()}

        # Mock database to return pending jobs
        mock_session = mock_db_session_factory.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Process jobs - should not query database since at capacity
        await runner._process_available_jobs()

        # Database should not be queried since we're at capacity
        mock_session.execute.assert_not_called()

    async def test_execute_job_with_cleanup_removes_from_active_set(self, mock_db_session_factory):
        """Test that completed jobs are removed from active set."""
        mock_session = mock_db_session_factory.return_value.__aenter__.return_value

        # Mock job
        job = MagicMock()
        job.id = uuid4()
        job.job_type = "library_scan"

        runner = JobWorkerRunner(mock_db_session_factory, poll_interval_seconds=1)

        # Mock JobWorker.execute_job to raise an exception
        with patch("kiremisu.services.job_worker.JobWorker") as mock_worker_class:
            mock_worker = mock_worker_class.return_value
            mock_worker.execute_job = AsyncMock(side_effect=Exception("Test error"))

            # Execute job with cleanup
            initial_active_count = len(runner._active_jobs)
            await runner._execute_job_with_cleanup(job)

            # Job should be removed from active set even if it failed
            assert len(runner._active_jobs) == initial_active_count
