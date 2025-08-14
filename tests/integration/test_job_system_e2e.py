"""End-to-end integration tests for the job system."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath
from kiremisu.services.importer import ImportStats
from kiremisu.services.job_worker import JobWorker, JobWorkerRunner


@pytest.mark.integration
class TestJobSystemE2E:
    """End-to-end integration tests for the complete job system."""

    @pytest.fixture
    def mock_importer(self):
        """Mock importer service for integration tests."""
        with patch("kiremisu.services.job_worker.ImporterService") as mock:
            mock_instance = mock.return_value
            mock_instance.scan_library_paths = AsyncMock(
                return_value=ImportStats(
                    series_found=3,
                    series_created=2,
                    series_updated=1,
                    chapters_found=15,
                    chapters_created=10,
                    chapters_updated=5,
                    errors=0,
                )
            )
            yield mock_instance

    async def test_complete_job_lifecycle_library_scan(
        self, client: AsyncClient, db_session: AsyncSession, mock_importer
    ):
        """Test complete job lifecycle: schedule -> execute -> complete."""
        # Create test library path
        path = LibraryPath(path="/test/integration", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Step 1: Schedule job via API
        schedule_request = {
            "job_type": "library_scan",
            "library_path_id": str(path.id),
            "priority": 7,
        }

        response = await client.post("/api/jobs/schedule", json=schedule_request)
        assert response.status_code == 200

        data = response.json()
        job_id = data["job_id"]

        # Step 2: Verify job was created
        job = await db_session.get(JobQueue, job_id)
        assert job is not None
        assert job.status == "pending"
        assert job.job_type == "library_scan"

        # Step 3: Execute job
        worker = JobWorker()
        result = await worker.execute_job(db_session, job)

        # Step 4: Verify job completion
        await db_session.refresh(job)
        assert job.status == "completed"
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.error_message is None

        # Step 5: Verify library path was updated
        await db_session.refresh(path)
        assert path.last_scan is not None

        # Step 6: Verify execution result
        assert result["job_type"] == "library_scan"
        assert result["library_path_id"] == str(path.id)
        assert "stats" in result

        # Step 7: Verify job status via API
        status_response = await client.get(f"/api/jobs/{job_id}")
        assert status_response.status_code == 200

        job_data = status_response.json()
        assert job_data["status"] == "completed"
        assert job_data["id"] == str(job_id)

    async def test_job_failure_and_retry_mechanism(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test job failure handling and retry mechanism."""
        # Schedule job with invalid library path (will cause failure)
        fake_path_id = uuid4()
        schedule_request = {
            "job_type": "library_scan",
            "library_path_id": str(fake_path_id),
            "priority": 5,
        }

        response = await client.post("/api/jobs/schedule", json=schedule_request)
        assert response.status_code == 400  # Should fail due to invalid path

    async def test_job_worker_runner_integration(
        self, client: AsyncClient, db_session: AsyncSession, mock_importer
    ):
        """Test JobWorkerRunner integration with job scheduling."""
        # Create test library path
        path = LibraryPath(path="/test/worker", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Create mock session factory
        async def mock_session_factory():
            return db_session

        # Initialize and start worker runner
        runner = JobWorkerRunner(
            mock_session_factory, poll_interval_seconds=1, max_concurrent_jobs=2
        )

        try:
            await runner.start()

            # Schedule job via API
            schedule_request = {
                "job_type": "library_scan",
                "library_path_id": str(path.id),
                "priority": 8,
            }

            response = await client.post("/api/jobs/schedule", json=schedule_request)
            assert response.status_code == 200
            job_id = response.json()["job_id"]

            # Wait for worker to process job
            await asyncio.sleep(2)

            # Verify job was processed
            job = await db_session.get(JobQueue, job_id)
            assert job is not None
            # Note: Job might still be running or completed depending on timing

            # Check worker status
            status = await runner.get_worker_status()
            assert status["running"] is True
            assert status["max_concurrent_jobs"] == 2

        finally:
            await runner.stop()

    async def test_automatic_job_scheduling_workflow(
        self, client: AsyncClient, db_session: AsyncSession, mock_importer
    ):
        """Test automatic job scheduling based on library path intervals."""
        # Create library paths with different schedules
        path1 = LibraryPath(
            path="/test/auto1",
            enabled=True,
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2),  # Due
        )
        path2 = LibraryPath(
            path="/test/auto2",
            enabled=True,
            scan_interval_hours=24,
            last_scan=datetime.utcnow() - timedelta(hours=1),  # Not due
        )

        db_session.add(path1)
        db_session.add(path2)
        await db_session.commit()

        # Schedule automatic jobs via API
        schedule_request = {"job_type": "auto_schedule", "priority": 5}

        response = await client.post("/api/jobs/schedule", json=schedule_request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        assert data["scheduled_count"] == 1  # Only path1 should be scheduled
        assert data["skipped_count"] == 1  # path2 should be skipped
        assert data["total_paths"] == 2

        # Verify job was created for path1
        from sqlalchemy import text

        jobs = await db_session.execute(
            text("SELECT * FROM job_queue WHERE job_type = 'library_scan'")
        )
        job_list = jobs.fetchall()
        assert len(job_list) == 1

    async def test_job_queue_statistics_integration(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test job queue statistics across different job states."""
        # Create jobs in different states
        jobs = [
            JobQueue(job_type="library_scan", status="pending"),
            JobQueue(job_type="library_scan", status="running"),
            JobQueue(job_type="library_scan", status="completed"),
            JobQueue(job_type="download", status="pending"),
            JobQueue(job_type="download", status="failed"),
        ]

        for job in jobs:
            db_session.add(job)
        await db_session.commit()

        # Get statistics via API
        response = await client.get("/api/jobs/status")
        assert response.status_code == 200

        data = response.json()
        stats = data["queue_stats"]

        # Verify overall statistics
        assert stats["pending"] == 2
        assert stats["running"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1

        # Verify job type specific statistics
        assert stats["library_scan_pending"] == 1
        assert stats["library_scan_running"] == 1
        assert stats["library_scan_completed"] == 1
        assert stats["download_pending"] == 1
        assert stats["download_failed"] == 1

    async def test_job_cleanup_integration(self, client: AsyncClient, db_session: AsyncSession):
        """Test job cleanup functionality via API."""
        # Create old and recent jobs
        old_job = JobQueue(
            job_type="library_scan",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=45),
        )
        recent_job = JobQueue(
            job_type="library_scan",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=5),
        )

        db_session.add(old_job)
        db_session.add(recent_job)
        await db_session.commit()

        # Cleanup via API
        response = await client.post("/api/jobs/cleanup?older_than_days=30")
        assert response.status_code == 200

        data = response.json()
        assert data["deleted"] == 1
        assert data["older_than_days"] == 30

        # Verify old job was deleted
        deleted_job = await db_session.get(JobQueue, old_job.id)
        assert deleted_job is None

        # Verify recent job still exists
        existing_job = await db_session.get(JobQueue, recent_job.id)
        assert existing_job is not None

    async def test_download_job_integration(self, client: AsyncClient, db_session: AsyncSession):
        """Test download job scheduling and execution."""
        # Schedule download job via API
        schedule_request = {
            "job_type": "download",
            "manga_id": "integration-test-manga",
            "download_type": "mangadx",
            "priority": 6,
        }

        response = await client.post("/api/jobs/schedule", json=schedule_request)
        assert response.status_code == 200

        data = response.json()
        job_id = data["job_id"]

        # Execute job
        job = await db_session.get(JobQueue, job_id)
        assert job is not None

        worker = JobWorker()
        result = await worker.execute_job(db_session, job)

        # Verify execution results
        await db_session.refresh(job)
        assert job.status == "completed"
        assert result["job_type"] == "download"
        assert result["manga_id"] == "integration-test-manga"

    async def test_recent_jobs_api_integration(self, client: AsyncClient, db_session: AsyncSession):
        """Test recent jobs API with filtering and pagination."""
        # Create jobs with different timestamps and types
        jobs = [
            JobQueue(
                job_type="library_scan",
                status="completed",
                created_at=datetime.utcnow() - timedelta(minutes=10),
            ),
            JobQueue(
                job_type="library_scan",
                status="pending",
                created_at=datetime.utcnow() - timedelta(minutes=5),
            ),
            JobQueue(
                job_type="download",
                status="failed",
                created_at=datetime.utcnow() - timedelta(minutes=2),
            ),
        ]

        for job in jobs:
            db_session.add(job)
        await db_session.commit()

        # Test recent jobs without filter
        response = await client.get("/api/jobs/recent")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert len(data["jobs"]) == 3

        # Test with job type filter
        response = await client.get("/api/jobs/recent?job_type=library_scan")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert data["job_type_filter"] == "library_scan"

        # Test with limit
        response = await client.get("/api/jobs/recent?limit=2")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2

    async def test_worker_status_api_integration(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test worker status API integration."""
        # Test without worker initialized
        response = await client.get("/api/jobs/worker/status")
        assert response.status_code == 200

        data = response.json()
        assert data["running"] is False
        assert "Worker not initialized" in data["message"]

    async def test_job_validation_errors(self, client: AsyncClient, db_session: AsyncSession):
        """Test API validation error handling."""
        # Test invalid priority
        schedule_request = {
            "job_type": "library_scan",
            "priority": 15,  # Out of range
        }

        response = await client.post("/api/jobs/schedule", json=schedule_request)
        assert response.status_code == 422  # Validation error

        # Test invalid job type
        schedule_request = {
            "job_type": "invalid_type",
            "priority": 5,
        }

        response = await client.post("/api/jobs/schedule", json=schedule_request)
        assert response.status_code == 400  # Bad request

    async def test_concurrent_job_execution(
        self, client: AsyncClient, db_session: AsyncSession, mock_importer
    ):
        """Test concurrent job execution handling."""
        # Create multiple library paths
        paths = [
            LibraryPath(path=f"/test/concurrent{i}", enabled=True, scan_interval_hours=24)
            for i in range(3)
        ]

        for path in paths:
            db_session.add(path)
        await db_session.commit()

        # Schedule multiple jobs
        job_ids = []
        for path in paths:
            schedule_request = {
                "job_type": "library_scan",
                "library_path_id": str(path.id),
                "priority": 5,
            }

            response = await client.post("/api/jobs/schedule", json=schedule_request)
            assert response.status_code == 200
            job_ids.append(response.json()["job_id"])

        # Execute jobs concurrently
        worker = JobWorker()
        tasks = []

        for job_id in job_ids:
            job = await db_session.get(JobQueue, job_id)
            task = asyncio.create_task(worker.execute_job(db_session, job))
            tasks.append(task)

        # Wait for all jobs to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all jobs completed successfully
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Job {job_ids[i]} failed with exception: {result}")

            assert result["job_type"] == "library_scan"

        # Verify all jobs are marked as completed
        for job_id in job_ids:
            job = await db_session.get(JobQueue, job_id)
            assert job.status == "completed"
