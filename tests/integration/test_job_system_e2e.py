"""End-to-end integration test for the complete job system."""

import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath, JobQueue
from kiremisu.services.job_scheduler import JobScheduler
from kiremisu.services.job_worker import JobWorker, JobWorkerRunner


@pytest.mark.integration
class TestJobSystemE2E:
    """End-to-end integration tests for the complete job system."""

    async def test_complete_job_lifecycle(self, db_session: AsyncSession):
        """Test the complete job lifecycle from scheduling to execution."""

        # Create a test library path that's due for scanning
        test_path = LibraryPath(
            path="/tmp/test-manga-e2e",
            enabled=True,
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2),  # Due for scan
        )
        db_session.add(test_path)
        await db_session.commit()

        try:
            # Step 1: Schedule automatic library scans
            scheduler_result = await JobScheduler.schedule_library_scans(db_session)
            assert scheduler_result["scheduled"] >= 1, "Should schedule at least one job"

            # Step 2: Verify job was created in database
            from sqlalchemy import select

            result = await db_session.execute(
                select(JobQueue).where(JobQueue.job_type == "library_scan")
            )
            scheduled_job = result.scalars().first()
            assert scheduled_job is not None, "Job should be created in database"
            assert scheduled_job.status == "pending"
            assert scheduled_job.payload.get("library_path_id") == str(test_path.id)

            # Step 3: Execute job using worker
            worker = JobWorker()

            # Mock the importer service to avoid actual file system operations
            class MockImporter:
                async def scan_library_paths(self, db, library_path_id=None):
                    return {
                        "series_found": 1,
                        "series_created": 1,
                        "chapters_found": 5,
                        "chapters_created": 5,
                    }

            worker.importer = MockImporter()

            # Execute the job
            job_result = await worker.execute_job(db_session, scheduled_job)

            # Step 4: Verify job execution results
            assert job_result["job_type"] == "library_scan"
            assert job_result["library_path_id"] == str(test_path.id)
            assert "series_found" in job_result["stats"]

            # Step 5: Verify job status was updated
            await db_session.refresh(scheduled_job)
            assert scheduled_job.status == "completed"
            assert scheduled_job.started_at is not None
            assert scheduled_job.completed_at is not None
            assert scheduled_job.error_message is None

            # Step 6: Verify library path last_scan was updated
            await db_session.refresh(test_path)
            assert test_path.last_scan is not None
            # Should be updated within the last minute
            time_diff = datetime.utcnow() - test_path.last_scan
            assert time_diff.total_seconds() < 60, "Last scan should be recent"

        finally:
            # Cleanup
            await db_session.delete(test_path)
            if scheduled_job:
                await db_session.delete(scheduled_job)
            await db_session.commit()

    async def test_job_worker_runner_integration(self, db_session: AsyncSession):
        """Test the job worker runner can find and execute jobs."""

        # Create a test job directly
        test_job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": None},  # Scan all paths
            status="pending",
            priority=1,
            scheduled_at=datetime.utcnow(),
        )
        db_session.add(test_job)
        await db_session.commit()

        try:
            # Create session factory
            async def mock_session_factory():
                return db_session

            # Create worker runner with minimal config
            worker_runner = JobWorkerRunner(
                db_session_factory=mock_session_factory, max_concurrent_jobs=1
            )

            # Mock the worker's importer
            class MockImporter:
                async def scan_library_paths(self, db, library_path_id=None):
                    return {"series_found": 0, "chapters_found": 0}

            worker_runner.worker.importer = MockImporter()

            # Process available jobs (should find and execute our test job)
            await worker_runner._process_available_jobs()

            # Verify job was processed
            await db_session.refresh(test_job)
            assert test_job.status in ["completed", "running"], (
                f"Job should be processed, got: {test_job.status}"
            )

        finally:
            # Cleanup
            await db_session.delete(test_job)
            await db_session.commit()

    async def test_job_retry_mechanism(self, db_session: AsyncSession):
        """Test that failed jobs are retried correctly."""

        # Create a test job
        test_job = JobQueue(
            job_type="library_scan",
            payload={"library_path_id": None},
            status="pending",
            priority=1,
            retry_count=0,
            max_retries=2,
            scheduled_at=datetime.utcnow(),
        )
        db_session.add(test_job)
        await db_session.commit()

        try:
            # Create worker that will fail
            worker = JobWorker()

            class FailingImporter:
                async def scan_library_paths(self, db, library_path_id=None):
                    raise Exception("Simulated failure")

            worker.importer = FailingImporter()

            # First execution should fail and mark for retry
            with pytest.raises(Exception):
                await worker.execute_job(db_session, test_job)

            # Verify job was marked for retry
            await db_session.refresh(test_job)
            assert test_job.status == "pending", "Job should be marked for retry"
            assert test_job.retry_count == 1, "Retry count should be incremented"
            assert "Simulated failure" in test_job.error_message

            # Second execution should also fail
            with pytest.raises(Exception):
                await worker.execute_job(db_session, test_job)

            await db_session.refresh(test_job)
            assert test_job.retry_count == 2

            # Third execution should fail permanently
            with pytest.raises(Exception):
                await worker.execute_job(db_session, test_job)

            await db_session.refresh(test_job)
            assert test_job.status == "failed", "Job should be marked as permanently failed"
            assert test_job.retry_count == 2, "Retry count should not exceed max"
            assert test_job.completed_at is not None

        finally:
            # Cleanup
            await db_session.delete(test_job)
            await db_session.commit()

    async def test_manual_vs_automatic_job_priority(self, db_session: AsyncSession):
        """Test that manual jobs have higher priority than automatic ones."""

        # Create test library path
        test_path = LibraryPath(
            path="/tmp/test-priority",
            enabled=True,
            scan_interval_hours=1,
            last_scan=datetime.utcnow() - timedelta(hours=2),
        )
        db_session.add(test_path)
        await db_session.commit()

        try:
            # Schedule automatic scan (lower priority)
            auto_result = await JobScheduler.schedule_library_scans(db_session)
            assert auto_result["scheduled"] >= 1

            # Schedule manual scan (higher priority)
            manual_job_id = await JobScheduler.schedule_manual_scan(
                db_session,
                library_path_id=test_path.id,
                priority=10,  # High priority
            )

            # Get jobs ordered by priority
            from sqlalchemy import select, desc

            result = await db_session.execute(
                select(JobQueue)
                .where(JobQueue.status == "pending")
                .order_by(desc(JobQueue.priority))
            )
            jobs = result.scalars().all()

            # Manual job should be first (highest priority)
            assert len(jobs) >= 2, "Should have both automatic and manual jobs"
            assert jobs[0].id == manual_job_id, "Manual job should have highest priority"
            assert jobs[0].priority > jobs[1].priority, "Manual job priority should be higher"

        finally:
            # Cleanup
            await db_session.delete(test_path)
            # Clean up jobs
            from sqlalchemy import delete

            await db_session.execute(delete(JobQueue).where(JobQueue.job_type == "library_scan"))
            await db_session.commit()
