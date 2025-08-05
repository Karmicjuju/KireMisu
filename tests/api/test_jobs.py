"""Integration tests for job management API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import JobQueue, LibraryPath
from kiremisu.services.job_worker import JobWorkerRunner


@pytest.mark.api
class TestJobsAPI:
    """Test cases for job management API endpoints."""

    async def test_get_job_status_endpoint(self, client: AsyncClient, db_session: AsyncSession):
        """Test GET /api/jobs/status endpoint."""
        # Create test jobs
        job1 = JobQueue(job_type="library_scan", status="pending")
        job2 = JobQueue(job_type="library_scan", status="running")
        job3 = JobQueue(job_type="library_scan", status="failed")

        db_session.add(job1)
        db_session.add(job2)
        db_session.add(job3)
        await db_session.commit()

        # Test endpoint
        response = await client.get("/api/jobs/status")

        assert response.status_code == 200
        data = response.json()

        assert "queue_stats" in data
        assert "timestamp" in data
        assert data["queue_stats"]["pending"] == 1
        assert data["queue_stats"]["running"] == 1
        assert data["queue_stats"]["failed"] == 1
        assert data["queue_stats"]["library_scan_pending"] == 1
        assert data["queue_stats"]["library_scan_running"] == 1
        assert data["queue_stats"]["library_scan_failed"] == 1

    async def test_get_recent_jobs_endpoint(self, client: AsyncClient, db_session: AsyncSession):
        """Test GET /api/jobs/recent endpoint."""
        # Create test jobs
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
            job_type="other_job",
            status="failed",
            created_at=datetime.utcnow() - timedelta(minutes=1),
        )

        db_session.add(job1)
        db_session.add(job2)
        db_session.add(job3)
        await db_session.commit()

        # Test endpoint without filter
        response = await client.get("/api/jobs/recent")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["jobs"]) == 3
        assert data["job_type_filter"] is None

        # Jobs should be ordered by creation time desc
        assert data["jobs"][0]["id"] == str(job3.id)
        assert data["jobs"][1]["id"] == str(job2.id)
        assert data["jobs"][2]["id"] == str(job1.id)

        # Test endpoint with job type filter
        response = await client.get("/api/jobs/recent?job_type=library_scan")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["jobs"]) == 2
        assert data["job_type_filter"] == "library_scan"

        # Test endpoint with limit
        response = await client.get("/api/jobs/recent?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["jobs"]) == 2

    async def test_get_specific_job_endpoint(self, client: AsyncClient, db_session: AsyncSession):
        """Test GET /api/jobs/{job_id} endpoint."""
        # Create test job
        job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": str(uuid4())},
            status="completed",
            priority=5,
            retry_count=0,
            max_retries=3,
        )
        db_session.add(job)
        await db_session.commit()

        # Test endpoint
        response = await client.get(f"/api/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(job.id)
        assert data["job_type"] == "library_scan"
        assert data["status"] == "completed"
        assert data["priority"] == 5
        assert data["retry_count"] == 0
        assert data["max_retries"] == 3

        # Test with non-existent job ID
        fake_id = uuid4()
        response = await client.get(f"/api/jobs/{fake_id}")

        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    async def test_schedule_manual_library_scan_specific_path(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST /api/jobs/schedule for manual library scan of specific path."""
        # Create test library path
        path = LibraryPath(path="/test/path", enabled=True, scan_interval_hours=24)
        db_session.add(path)
        await db_session.commit()

        # Test endpoint
        request_data = {"job_type": "library_scan", "library_path_id": str(path.id), "priority": 8}

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "scheduled"
        assert "Manual library scan scheduled for path" in data["message"]
        assert data["scheduled_count"] == 1
        assert "job_id" in data

        # Verify job was created in database
        from sqlalchemy import text

        jobs = await db_session.execute(
            text("SELECT * FROM job_queue WHERE job_type = 'library_scan'")
        )
        job_list = jobs.fetchall()
        assert len(job_list) == 1

    async def test_schedule_manual_library_scan_all_paths(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST /api/jobs/schedule for manual library scan of all paths."""
        request_data = {"job_type": "library_scan", "priority": 9}

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "scheduled"
        assert "Manual library scan scheduled for all paths" in data["message"]
        assert data["scheduled_count"] == 1
        assert "job_id" in data

    async def test_schedule_manual_library_scan_invalid_path(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST /api/jobs/schedule with invalid library path ID."""
        fake_path_id = uuid4()

        request_data = {
            "job_type": "library_scan",
            "library_path_id": str(fake_path_id),
            "priority": 5,
        }

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 400
        assert "Library path not found" in response.json()["detail"]

    async def test_schedule_auto_jobs(self, client: AsyncClient, db_session: AsyncSession):
        """Test POST /api/jobs/schedule for automatic job scheduling."""
        # Create test library paths
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

        db_session.add(path1)
        db_session.add(path2)
        await db_session.commit()

        # Test endpoint
        request_data = {"job_type": "auto_schedule", "priority": 3}

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert "Scheduled 1 automatic scans" in data["message"]
        assert data["scheduled_count"] == 1
        assert data["skipped_count"] == 1
        assert data["total_paths"] == 2

    async def test_schedule_invalid_job_type(self, client: AsyncClient, db_session: AsyncSession):
        """Test POST /api/jobs/schedule with invalid job type."""
        request_data = {"job_type": "invalid_job", "priority": 5}

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 400
        assert "Unknown job type" in response.json()["detail"]

    async def test_schedule_job_validation_error(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST /api/jobs/schedule with validation errors."""
        # Test invalid priority
        request_data = {
            "job_type": "library_scan",
            "priority": 15,  # Out of valid range (1-10)
        }

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 422  # Validation error

    async def test_cleanup_old_jobs_endpoint(self, client: AsyncClient, db_session: AsyncSession):
        """Test POST /api/jobs/cleanup endpoint."""
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

        db_session.add(old_job)
        db_session.add(recent_job)
        await db_session.commit()

        # Test cleanup
        response = await client.post("/api/jobs/cleanup?older_than_days=30")

        assert response.status_code == 200
        data = response.json()

        assert data["deleted"] == 1
        assert data["older_than_days"] == 30

    async def test_cleanup_old_jobs_validation(self, client: AsyncClient, db_session: AsyncSession):
        """Test POST /api/jobs/cleanup with validation errors."""
        # Test invalid older_than_days parameter
        response = await client.post("/api/jobs/cleanup?older_than_days=400")  # Out of range

        assert response.status_code == 422  # Validation error

    async def test_get_worker_status_no_worker(self, client: AsyncClient, db_session: AsyncSession):
        """Test GET /api/jobs/worker/status when no worker is initialized."""
        response = await client.get("/api/jobs/worker/status")

        assert response.status_code == 200
        data = response.json()

        assert data["running"] is False
        assert data["active_jobs"] == 0
        assert data["max_concurrent_jobs"] == 0
        assert data["poll_interval_seconds"] == 0
        assert "Worker not initialized" in data["message"]

    async def test_get_worker_status_with_worker(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test GET /api/jobs/worker/status with initialized worker."""
        # Mock worker runner
        mock_worker = AsyncMock(spec=JobWorkerRunner)
        mock_worker.get_worker_status.return_value = {
            "running": True,
            "active_jobs": 2,
            "max_concurrent_jobs": 5,
            "poll_interval_seconds": 10,
        }

        # Set worker in API module
        with patch("kiremisu.api.jobs.get_worker_runner", return_value=mock_worker):
            response = await client.get("/api/jobs/worker/status")

            assert response.status_code == 200
            data = response.json()

            assert data["running"] is True
            assert data["active_jobs"] == 2
            assert data["max_concurrent_jobs"] == 5
            assert data["poll_interval_seconds"] == 10

    async def test_job_response_schema_validation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that job responses match expected schema."""
        # Create comprehensive test job
        job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": str(uuid4()), "library_path": "/test/path"},
            status="completed",
            priority=7,
            started_at=datetime.utcnow() - timedelta(minutes=10),
            completed_at=datetime.utcnow() - timedelta(minutes=5),
            error_message=None,
            retry_count=1,
            max_retries=3,
            scheduled_at=datetime.utcnow() - timedelta(minutes=15),
        )
        db_session.add(job)
        await db_session.commit()

        # Get job details
        response = await client.get(f"/api/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields are present and properly formatted
        required_fields = [
            "id",
            "job_type",
            "payload",
            "status",
            "priority",
            "started_at",
            "completed_at",
            "error_message",
            "retry_count",
            "max_retries",
            "scheduled_at",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify data types and values
        assert isinstance(data["payload"], dict)
        assert data["priority"] == 7
        assert data["status"] == "completed"
        assert data["retry_count"] == 1
        assert data["max_retries"] == 3

    async def test_schedule_download_job_api(self, client: AsyncClient, db_session: AsyncSession):
        """Test POST /api/jobs/schedule for download job."""
        request_data = {
            "job_type": "download",
            "manga_id": "test-manga-123",
            "download_type": "mangadx",
            "priority": 6,
        }

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "scheduled"
        assert "Download job scheduled" in data["message"]
        assert data["scheduled_count"] == 1
        assert "job_id" in data

        # Verify job was created in database
        from sqlalchemy import text

        jobs = await db_session.execute(text("SELECT * FROM job_queue WHERE job_type = 'download'"))
        job_list = jobs.fetchall()
        assert len(job_list) == 1

    async def test_schedule_download_job_with_series_id(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST /api/jobs/schedule for download job with series association."""
        from uuid import uuid4

        series_id = uuid4()
        request_data = {
            "job_type": "download",
            "manga_id": "test-manga-456",
            "download_type": "mangadx",
            "series_id": str(series_id),
            "priority": 8,
        }

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "scheduled"
        assert "test-manga-456" in data["message"]
        assert data["scheduled_count"] == 1

    async def test_schedule_download_job_missing_manga_id(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test POST /api/jobs/schedule for download job without manga_id."""
        request_data = {
            "job_type": "download",
            "download_type": "mangadx",
            "priority": 5,
            # Missing manga_id
        }

        response = await client.post("/api/jobs/schedule", json=request_data)

        assert response.status_code == 400
        assert "Download jobs require 'manga_id' field" in response.json()["detail"]

    async def test_schedule_download_job_validation_schema(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test download job validation in request schema."""
        # Test that download is a valid job type
        request_data = {
            "job_type": "download",
            "manga_id": "test-manga",
            "priority": 5,
        }

        # This should not fail validation
        response = await client.post("/api/jobs/schedule", json=request_data)
        assert response.status_code == 200

        # Test invalid job type still fails
        request_data["job_type"] = "invalid_type"
        response = await client.post("/api/jobs/schedule", json=request_data)
        assert response.status_code == 422  # Validation error