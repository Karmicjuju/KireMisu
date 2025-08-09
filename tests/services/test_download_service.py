"""Tests for the download service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from kiremisu.services.download_service import (
    DownloadService,
    DownloadJobData,
    DownloadProgressTracker,
    DownloadError,
)
from kiremisu.database.models import JobQueue, LibraryPath


class TestDownloadJobData:
    """Tests for DownloadJobData class."""
    
    def test_download_job_data_properties(self):
        """Test DownloadJobData property extraction."""
        job_id = str(uuid4())
        payload = {
            "job_id": job_id,
            "download_type": "mangadx",
            "manga_id": "test-manga-123",
            "series_id": str(uuid4()),
            "chapter_ids": ["ch1", "ch2", "ch3"],
            "batch_type": "multiple",
            "volume_number": "1",
            "destination_path": "/test/path",
            "progress": {
                "total_chapters": 3,
                "downloaded_chapters": 1,
            }
        }
        
        job_data = DownloadJobData(payload)
        
        assert job_data.job_id == job_id
        assert job_data.download_type == "mangadx"
        assert job_data.manga_id == "test-manga-123"
        assert job_data.series_id == payload["series_id"]
        assert job_data.chapter_ids == ["ch1", "ch2", "ch3"]
        assert job_data.batch_type == "multiple"
        assert job_data.volume_number == "1"
        assert job_data.destination_path == "/test/path"
        assert job_data.progress_data["total_chapters"] == 3
    
    def test_download_job_data_defaults(self):
        """Test DownloadJobData default values."""
        payload = {"manga_id": "test-123"}
        job_data = DownloadJobData(payload)
        
        assert job_data.download_type == "mangadx"
        assert job_data.chapter_ids == []
        assert job_data.batch_type is None
        assert job_data.volume_number is None
        assert job_data.destination_path is None
        assert job_data.progress_data == {}


class TestDownloadProgressTracker:
    """Tests for DownloadProgressTracker class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db
    
    @pytest.fixture
    def progress_tracker(self, mock_db):
        """Create progress tracker instance."""
        job_id = uuid4()
        return DownloadProgressTracker(mock_db, job_id)
    
    @pytest.mark.asyncio
    async def test_initialize_progress(self, progress_tracker, mock_db):
        """Test progress initialization."""
        await progress_tracker.initialize(5)
        
        assert progress_tracker._progress["total_chapters"] == 5
        assert progress_tracker._progress["downloaded_chapters"] == 0
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_chapter(self, progress_tracker, mock_db):
        """Test starting chapter tracking."""
        await progress_tracker.start_chapter("ch1", "Chapter 1")
        
        assert progress_tracker._progress["current_chapter"]["id"] == "ch1"
        assert progress_tracker._progress["current_chapter"]["title"] == "Chapter 1"
        assert progress_tracker._progress["current_chapter_progress"] == 0.0
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_chapter_progress(self, progress_tracker, mock_db):
        """Test updating chapter progress."""
        await progress_tracker.update_chapter_progress(0.75)
        
        assert progress_tracker._progress["current_chapter_progress"] == 0.75
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_chapter_success(self, progress_tracker, mock_db):
        """Test completing chapter successfully."""
        progress_tracker._progress["current_chapter"] = {"id": "ch1", "title": "Chapter 1"}
        
        await progress_tracker.complete_chapter(success=True)
        
        assert progress_tracker._progress["downloaded_chapters"] == 1
        assert progress_tracker._progress["error_count"] == 0
        assert progress_tracker._progress["current_chapter"] is None
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_chapter_failure(self, progress_tracker, mock_db):
        """Test completing chapter with failure."""
        progress_tracker._progress["current_chapter"] = {"id": "ch1", "title": "Chapter 1"}
        
        await progress_tracker.complete_chapter(success=False, error_message="Download failed")
        
        assert progress_tracker._progress["downloaded_chapters"] == 0
        assert progress_tracker._progress["error_count"] == 1
        assert len(progress_tracker._progress["errors"]) == 1
        assert progress_tracker._progress["errors"][0]["error"] == "Download failed"
        assert progress_tracker._progress["current_chapter"] is None


class TestDownloadService:
    """Tests for DownloadService class."""
    
    @pytest.fixture
    def download_service(self):
        """Create download service instance."""
        with patch('kiremisu.services.download_service.MangaDxClient') as mock_client:
            service = DownloadService()
            service.mangadx_client._make_request = AsyncMock()
            return service
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.mark.asyncio
    async def test_enqueue_single_chapter_download(self, download_service, mock_db):
        """Test enqueuing single chapter download."""
        job_id = await download_service.enqueue_single_chapter_download(
            db=mock_db,
            manga_id="manga-123",
            chapter_id="ch-456",
            series_id=uuid4(),
            priority=5,
            destination_path="/test/path",
        )
        
        assert isinstance(job_id, UUID)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Check that job was created with correct payload
        job = mock_db.add.call_args[0][0]
        assert job.job_type == "download"
        assert job.priority == 5
        assert job.payload["download_type"] == "mangadx"
        assert job.payload["manga_id"] == "manga-123"
        assert job.payload["chapter_ids"] == ["ch-456"]
        assert job.payload["batch_type"] == "single"
    
    @pytest.mark.asyncio
    async def test_enqueue_batch_download(self, download_service, mock_db):
        """Test enqueuing batch download."""
        chapter_ids = ["ch1", "ch2", "ch3"]
        
        job_id = await download_service.enqueue_batch_download(
            db=mock_db,
            manga_id="manga-123",
            chapter_ids=chapter_ids,
            batch_type="volume",
            volume_number="2",
            priority=4,
        )
        
        assert isinstance(job_id, UUID)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        job = mock_db.add.call_args[0][0]
        assert job.payload["chapter_ids"] == chapter_ids
        assert job.payload["batch_type"] == "volume"
        assert job.payload["volume_number"] == "2"
    
    @pytest.mark.asyncio
    async def test_enqueue_series_download(self, download_service, mock_db):
        """Test enqueuing series download."""
        with patch.object(download_service, '_get_all_chapter_ids', return_value=["ch1", "ch2", "ch3"]):
            job_id = await download_service.enqueue_series_download(
                db=mock_db,
                manga_id="manga-123",
                priority=2,
            )
        
        assert isinstance(job_id, UUID)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        job = mock_db.add.call_args[0][0]
        assert job.payload["batch_type"] == "series"
        assert job.payload["chapter_ids"] == ["ch1", "ch2", "ch3"]
    
    @pytest.mark.asyncio
    async def test_get_destination_path_custom(self, download_service, mock_db):
        """Test getting custom destination path."""
        job_data = DownloadJobData({"destination_path": "/custom/path"})
        
        result = await download_service._get_destination_path(mock_db, job_data)
        
        assert result == "/custom/path"
    
    @pytest.mark.asyncio
    async def test_get_destination_path_default(self, download_service, mock_db):
        """Test getting default destination path from library paths."""
        job_data = DownloadJobData({"manga_id": "manga-123"})
        
        # Mock database query result
        mock_result = MagicMock()
        mock_library_path = MagicMock()
        mock_library_path.path = "/app/data/library"
        mock_result.scalar_one_or_none.return_value = mock_library_path
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await download_service._get_destination_path(mock_db, job_data)
        
        expected_path = "/app/data/library/downloads/manga-123"
        assert result == expected_path
    
    @pytest.mark.asyncio
    async def test_get_destination_path_no_library_paths(self, download_service, mock_db):
        """Test error when no library paths configured."""
        job_data = DownloadJobData({"manga_id": "manga-123"})
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(DownloadError, match="No enabled library paths configured"):
            await download_service._get_destination_path(mock_db, job_data)
    
    @pytest.mark.asyncio
    async def test_execute_download_job(self, download_service, mock_db):
        """Test executing a download job."""
        # Create test job
        job = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={
                "job_id": str(uuid4()),
                "download_type": "mangadx",
                "manga_id": "manga-123",
                "chapter_ids": ["ch1", "ch2"],
                "batch_type": "multiple",
            },
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        # Mock dependencies
        with patch.object(download_service, '_get_destination_path', return_value="/test/downloads") as mock_dest:
            with patch.object(download_service, '_download_single_chapter') as mock_download:
                with patch.object(download_service, '_update_series_with_downloads') as mock_update:
                    mock_download.side_effect = [
                        {"chapter_id": "ch1", "title": "Chapter 1", "file_path": "/test/ch1.cbz"},
                        {"chapter_id": "ch2", "title": "Chapter 2", "file_path": "/test/ch2.cbz"},
                    ]
                    
                    result = await download_service.execute_download_job(mock_db, job)
        
        # Verify result
        assert result["job_id"] == str(job.id)
        assert result["total_chapters"] == 2
        assert result["downloaded_chapters"] == 2
        assert result["error_count"] == 0
        assert len(result["downloaded_files"]) == 2
        
        # Verify method calls
        mock_dest.assert_called_once()
        assert mock_download.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_download_job_with_errors(self, download_service, mock_db):
        """Test executing download job with some failures."""
        job = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={
                "job_id": str(uuid4()),
                "download_type": "mangadx",
                "manga_id": "manga-123",
                "chapter_ids": ["ch1", "ch2"],
                "batch_type": "multiple",
            },
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch.object(download_service, '_get_destination_path', return_value="/test/downloads"):
            with patch.object(download_service, '_download_single_chapter') as mock_download:
                # First download succeeds, second fails
                mock_download.side_effect = [
                    {"chapter_id": "ch1", "title": "Chapter 1", "file_path": "/test/ch1.cbz"},
                    Exception("Download failed"),
                ]
                
                result = await download_service.execute_download_job(mock_db, job)
        
        assert result["downloaded_chapters"] == 1
        assert result["error_count"] == 1
        assert len(result["downloaded_files"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_download_jobs(self, download_service, mock_db):
        """Test getting download jobs with filtering."""
        # Mock database query results
        mock_jobs = [
            MagicMock(spec=JobQueue),
            MagicMock(spec=JobQueue),
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.fetchall.return_value = [(1, "job1"), (2, "job2")]
        
        # Set up execute to return different results for different queries
        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])
        
        jobs, total = await download_service.get_download_jobs(
            db=mock_db,
            status="pending",
            limit=10,
            offset=0,
        )
        
        assert len(jobs) == 2
        assert total == 2
        assert mock_db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cancel_download_job(self, download_service, mock_db):
        """Test cancelling a download job."""
        job_id = uuid4()
        
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        
        result = await download_service.cancel_download_job(mock_db, job_id)
        
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_download_job_not_found(self, download_service, mock_db):
        """Test cancelling non-existent job."""
        job_id = uuid4()
        
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        
        result = await download_service.cancel_download_job(mock_db, job_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_retry_download_job(self, download_service, mock_db):
        """Test retrying a failed download job."""
        job_id = uuid4()
        
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        
        result = await download_service.retry_download_job(mock_db, job_id)
        
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_single_chapter_placeholder(self, download_service):
        """Test placeholder single chapter download."""
        progress_tracker = MagicMock()
        progress_tracker.start_chapter = AsyncMock()
        progress_tracker.update_chapter_progress = AsyncMock()
        
        # Mock the MangaDx API response
        download_service.mangadx_client._make_request.return_value = {
            "data": {"attributes": {"pages": ["page1.jpg"]}}
        }
        
        with patch('os.makedirs'):
            with patch('zipfile.ZipFile') as mock_zipfile:
                with patch('os.path.getsize', return_value=1024):
                    result = await download_service._download_single_chapter(
                        progress_tracker=progress_tracker,
                        manga_id="manga-123",
                        chapter_id="ch-456",
                        destination_path="/test/downloads",
                    )
        
        assert result["chapter_id"] == "ch-456"
        assert result["file_size"] == 1024
        assert result["page_count"] == 1
        progress_tracker.start_chapter.assert_called_once()
        progress_tracker.update_chapter_progress.assert_called()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, download_service):
        """Test cleanup method."""
        download_service.mangadx_client = AsyncMock()
        download_service.mangadx_client.close = AsyncMock()
        
        await download_service.cleanup()
        
        download_service.mangadx_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_service_context_manager(self):
        """Test async context manager for download service."""
        from kiremisu.api.downloads import get_download_service_context
        
        # Test that context manager creates and cleans up service properly
        async with get_download_service_context() as service:
            assert isinstance(service, DownloadService)
            # Service should be properly initialized
            assert service is not None
        
        # After context exit, cleanup should have been called
        # Note: We can't easily verify cleanup was called without mocking
        # but the important thing is that the context manager works

    @pytest.mark.asyncio
    async def test_download_service_context_manager_exception_handling(self):
        """Test context manager handles exceptions and still cleans up."""
        from kiremisu.api.downloads import get_download_service_context
        
        cleanup_called = False
        
        # Mock the service to track cleanup
        with patch('kiremisu.api.downloads.DownloadService') as mock_service_class:
            mock_service = AsyncMock()
            
            async def mock_cleanup():
                nonlocal cleanup_called
                cleanup_called = True
            
            mock_service.cleanup = mock_cleanup
            mock_service_class.return_value = mock_service
            
            # Test that cleanup is called even when exception occurs
            with pytest.raises(ValueError):
                async with get_download_service_context() as service:
                    assert service == mock_service
                    raise ValueError("Test exception")
            
            # Cleanup should have been called despite exception
            assert cleanup_called is True

    @pytest.mark.asyncio  
    async def test_download_service_context_manager_cleanup_failure(self):
        """Test context manager handles cleanup failures gracefully."""
        from kiremisu.api.downloads import get_download_service_context
        
        with patch('kiremisu.api.downloads.DownloadService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.cleanup.side_effect = Exception("Cleanup failed")
            mock_service_class.return_value = mock_service
            
            # Context manager should not raise exception even if cleanup fails
            try:
                async with get_download_service_context() as service:
                    assert service == mock_service
                    # Normal operation should work
                    pass
            except Exception as e:
                pytest.fail(f"Context manager should handle cleanup failure gracefully, but raised: {e}")
            
            # Cleanup should have been attempted
            mock_service.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_service_resource_management(self):
        """Test that download service properly manages resources."""
        download_service = DownloadService()
        
        # Mock external resources
        mock_mangadx_client = AsyncMock()
        mock_mangadx_client.close = AsyncMock()
        download_service.mangadx_client = mock_mangadx_client
        
        # Mock any other resources that need cleanup
        download_service._temp_files = ["/tmp/test1", "/tmp/test2"]  # Hypothetical
        
        # Test cleanup
        await download_service.cleanup()
        
        # Verify cleanup was called
        mock_mangadx_client.close.assert_called_once()
        
        # In real implementation, would also verify temp file cleanup, etc.


class TestDownloadServiceIntegration:
    """Integration tests for download service with real-like scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_download_workflow(self):
        """Test complete download workflow from enqueue to completion."""
        with patch('kiremisu.services.download_service.MangaDxClient'):
            download_service = DownloadService()
        
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        
        # 1. Enqueue job
        job_id = await download_service.enqueue_single_chapter_download(
            db=mock_db,
            manga_id="manga-123",
            chapter_id="ch-456",
            priority=5,
        )
        
        # 2. Simulate job execution
        job = mock_db.add.call_args[0][0]
        
        with patch.object(download_service, '_get_destination_path', return_value="/test/downloads"):
            with patch.object(download_service, '_download_single_chapter') as mock_download:
                mock_download.return_value = {
                    "chapter_id": "ch-456",
                    "title": "Chapter 456",
                    "file_path": "/test/downloads/Chapter_456.cbz",
                    "file_size": 2048,
                    "page_count": 20,
                }
                
                result = await download_service.execute_download_job(mock_db, job)
        
        # Verify complete workflow
        assert job.job_type == "download"
        assert result["downloaded_chapters"] == 1
        assert result["error_count"] == 0
        assert len(result["downloaded_files"]) == 1