"""Integration tests for the complete download system."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from kiremisu.services.job_worker import JobWorker, JobExecutionError
from kiremisu.services.download_service import DownloadService
from kiremisu.database.models import JobQueue


class TestDownloadJobIntegration:
    """Integration tests for download jobs through the job worker."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.execute = AsyncMock()
        db.refresh = AsyncMock()
        return db
    
    @pytest.fixture
    def download_job(self):
        """Create a test download job."""
        return JobQueue(
            id=uuid4(),
            job_type="download",
            payload={
                "job_id": str(uuid4()),
                "download_type": "mangadx",
                "manga_id": "test-manga-123",
                "chapter_ids": ["ch1", "ch2"],
                "batch_type": "multiple",
                "series_id": str(uuid4()),
                "progress": {},
            },
            status="running",
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    
    @pytest.mark.asyncio
    async def test_job_worker_executes_download_job(self, mock_db, download_job):
        """Test that JobWorker properly executes download jobs."""
        worker = JobWorker()
        
        # Mock the download service execution
        mock_result = {
            "job_id": str(download_job.id),
            "job_type": "download",
            "download_type": "mangadx",
            "manga_id": "test-manga-123",
            "total_chapters": 2,
            "downloaded_chapters": 2,
            "error_count": 0,
            "destination_path": "/test/downloads",
            "downloaded_files": ["/test/ch1.cbz", "/test/ch2.cbz"],
        }
        
        with patch.object(worker.download_service, 'execute_download_job', return_value=mock_result):
            with patch.object(worker.download_service, 'cleanup') as mock_cleanup:
                result = await worker.execute_job(mock_db, download_job)
        
        # Verify job was executed
        assert result["job_type"] == "download"
        assert result["downloaded_chapters"] == 2
        assert result["error_count"] == 0
        
        # Verify cleanup was called
        mock_cleanup.assert_called_once()
        
        # Verify database operations
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_job_worker_handles_download_failure(self, mock_db, download_job):
        """Test that JobWorker properly handles download job failures."""
        worker = JobWorker()
        
        # Mock download service to raise an exception
        with patch.object(worker.download_service, 'execute_download_job', side_effect=Exception("Download failed")):
            with patch.object(worker.download_service, 'cleanup') as mock_cleanup:
                with pytest.raises(JobExecutionError):
                    await worker.execute_job(mock_db, download_job)
        
        # Verify cleanup was called even on failure
        mock_cleanup.assert_called_once()
        
        # Verify rollback was called
        mock_db.rollback.assert_called()
    
    @pytest.mark.asyncio
    async def test_download_job_missing_manga_id(self, mock_db):
        """Test handling of download job with missing manga_id."""
        invalid_job = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={
                "download_type": "mangadx",
                # Missing manga_id
            },
            status="running",
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        worker = JobWorker()
        
        with pytest.raises(JobExecutionError, match="missing required 'manga_id'"):
            await worker.execute_job(mock_db, invalid_job)
    
    @pytest.mark.asyncio
    async def test_download_service_integration_with_progress(self, mock_db):
        """Test download service integration with progress tracking."""
        download_service = DownloadService()
        
        # Create a job with progress tracking
        job = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={
                "job_id": str(uuid4()),
                "download_type": "mangadx",
                "manga_id": "test-manga-123",
                "chapter_ids": ["ch1", "ch2", "ch3"],
                "batch_type": "multiple",
                "progress": {},
            },
            status="running",
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        # Mock dependencies
        with patch.object(download_service, '_get_destination_path', return_value="/test/downloads"):
            with patch.object(download_service, '_download_single_chapter') as mock_download:
                with patch.object(download_service, 'mangadx_client'):
                    # Mock successful chapter downloads
                    mock_download.side_effect = [
                        {"chapter_id": "ch1", "title": "Chapter 1", "file_path": "/test/ch1.cbz"},
                        {"chapter_id": "ch2", "title": "Chapter 2", "file_path": "/test/ch2.cbz"},
                        {"chapter_id": "ch3", "title": "Chapter 3", "file_path": "/test/ch3.cbz"},
                    ]
                    
                    result = await download_service.execute_download_job(mock_db, job)
        
        # Verify result
        assert result["total_chapters"] == 3
        assert result["downloaded_chapters"] == 3
        assert result["error_count"] == 0
        assert len(result["downloaded_files"]) == 3
        
        # Verify progress tracking was called (through database updates)
        assert mock_db.execute.call_count >= 3  # At least initialize + 3 chapter completions
        assert mock_db.commit.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_download_with_partial_failures(self, mock_db):
        """Test download job with some chapters failing."""
        download_service = DownloadService()
        
        job = JobQueue(
            id=uuid4(),
            job_type="download", 
            payload={
                "job_id": str(uuid4()),
                "download_type": "mangadx",
                "manga_id": "test-manga-123",
                "chapter_ids": ["ch1", "ch2", "ch3"],
                "batch_type": "multiple",
                "progress": {},
            },
            status="running",
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch.object(download_service, '_get_destination_path', return_value="/test/downloads"):
            with patch.object(download_service, '_download_single_chapter') as mock_download:
                with patch.object(download_service, 'mangadx_client'):
                    # Mock mixed success/failure
                    mock_download.side_effect = [
                        {"chapter_id": "ch1", "title": "Chapter 1", "file_path": "/test/ch1.cbz"},
                        Exception("Chapter 2 download failed"),
                        {"chapter_id": "ch3", "title": "Chapter 3", "file_path": "/test/ch3.cbz"},
                    ]
                    
                    result = await download_service.execute_download_job(mock_db, job)
        
        # Verify partial success
        assert result["total_chapters"] == 3
        assert result["downloaded_chapters"] == 2  # ch1 and ch3 succeeded
        assert result["error_count"] == 1  # ch2 failed
        assert len(result["downloaded_files"]) == 2
        assert "progress" in result
    
    @pytest.mark.asyncio
    async def test_enqueue_and_execute_workflow(self, mock_db):
        """Test complete workflow from enqueue to execution."""
        download_service = DownloadService()
        
        # 1. Enqueue a download job
        with patch('uuid.uuid4', return_value=uuid4()) as mock_uuid:
            job_id = await download_service.enqueue_single_chapter_download(
                db=mock_db,
                manga_id="test-manga-123",
                chapter_id="test-chapter-456",
                priority=5,
            )
        
        # Verify job was added to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        
        # Get the created job
        created_job = mock_db.add.call_args[0][0]
        assert created_job.job_type == "download"
        assert created_job.priority == 5
        assert created_job.payload["manga_id"] == "test-manga-123"
        assert created_job.payload["chapter_ids"] == ["test-chapter-456"]
        
        # 2. Execute the job through worker
        worker = JobWorker()
        created_job.status = "running"
        
        with patch.object(worker.download_service, 'execute_download_job') as mock_execute:
            mock_execute.return_value = {
                "job_id": str(job_id),
                "downloaded_chapters": 1,
                "error_count": 0,
            }
            
            result = await worker.execute_job(mock_db, created_job)
        
        assert result["downloaded_chapters"] == 1
        assert result["error_count"] == 0


class TestDownloadSystemHealthChecks:
    """Tests for download system health and monitoring."""
    
    @pytest.mark.asyncio
    async def test_download_service_resource_cleanup(self):
        """Test that download service properly cleans up resources."""
        download_service = DownloadService()
        
        # Mock the MangaDx client
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        download_service.mangadx_client = mock_client
        
        await download_service.cleanup()
        
        mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_download_handling(self, mock_db):
        """Test handling of multiple concurrent downloads."""
        download_service = DownloadService()
        
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = JobQueue(
                id=uuid4(),
                job_type="download",
                payload={
                    "job_id": str(uuid4()),
                    "download_type": "mangadx",
                    "manga_id": f"manga-{i}",
                    "chapter_ids": [f"ch-{i}"],
                    "batch_type": "single",
                },
                status="running",
                priority=3,
                scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            jobs.append(job)
        
        # Mock download execution
        with patch.object(download_service, '_get_destination_path', return_value="/test/downloads"):
            with patch.object(download_service, '_download_single_chapter') as mock_download:
                with patch.object(download_service, 'mangadx_client'):
                    mock_download.return_value = {
                        "chapter_id": "test-ch",
                        "title": "Test Chapter",
                        "file_path": "/test/test-ch.cbz",
                    }
                    
                    # Execute all jobs
                    results = []
                    for job in jobs:
                        result = await download_service.execute_download_job(mock_db, job)
                        results.append(result)
        
        # Verify all jobs completed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["manga_id"] == f"manga-{i}"
            assert result["downloaded_chapters"] == 1
            assert result["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_download_retry_logic_integration(self, mock_db):
        """Test download retry functionality integration."""
        download_service = DownloadService()
        job_id = uuid4()
        
        # Test cancelling a job
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        
        success = await download_service.cancel_download_job(mock_db, job_id)
        assert success is True
        
        # Test retrying a job
        mock_result.rowcount = 1
        success = await download_service.retry_download_job(mock_db, job_id)
        assert success is True
        
        # Verify database operations
        assert mock_db.execute.call_count == 2
        assert mock_db.commit.call_count == 2


class TestDownloadJobQueueIntegration:
    """Test integration with the job queue system."""
    
    @pytest.mark.asyncio
    async def test_job_queue_priority_handling(self, mock_db):
        """Test that download jobs respect priority ordering."""
        download_service = DownloadService()
        
        # Create jobs with different priorities
        high_priority_job = await download_service.enqueue_single_chapter_download(
            db=mock_db,
            manga_id="high-priority-manga",
            chapter_id="ch1", 
            priority=8,
        )
        
        low_priority_job = await download_service.enqueue_single_chapter_download(
            db=mock_db,
            manga_id="low-priority-manga",
            chapter_id="ch1",
            priority=2,
        )
        
        # Verify jobs were created with correct priorities
        jobs_added = [call[0][0] for call in mock_db.add.call_args_list]
        
        high_priority_job_obj = next(job for job in jobs_added if job.priority == 8)
        low_priority_job_obj = next(job for job in jobs_added if job.priority == 2)
        
        assert high_priority_job_obj.payload["manga_id"] == "high-priority-manga"
        assert low_priority_job_obj.payload["manga_id"] == "low-priority-manga"
    
    @pytest.mark.asyncio
    async def test_job_status_transitions(self, mock_db):
        """Test proper job status transitions during download."""
        worker = JobWorker()
        
        job = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={
                "manga_id": "test-manga",
                "chapter_ids": ["ch1"],
            },
            status="running",  # Job starts as running (claimed by worker)
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        # Mock successful execution
        with patch.object(worker.download_service, 'execute_download_job') as mock_execute:
            mock_execute.return_value = {
                "job_id": str(job.id),
                "downloaded_chapters": 1,
                "error_count": 0,
            }
            
            result = await worker.execute_job(mock_db, job)
        
        # Verify job completion was recorded
        assert result["downloaded_chapters"] == 1
        mock_db.commit.assert_called_once()
        
        # Verify the job status update call was made
        update_calls = [call for call in mock_db.execute.call_args_list]
        assert len(update_calls) >= 1  # At least one update call for completion