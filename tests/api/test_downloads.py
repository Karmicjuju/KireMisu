"""Tests for the downloads API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from kiremisu.database.models import JobQueue
from kiremisu.database.schemas import (
    DownloadJobRequest,
    DownloadJobResponse,
    DownloadJobListResponse,
    DownloadJobActionRequest,
)


@pytest.fixture
def mock_download_service():
    """Mock download service."""
    with patch('kiremisu.api.downloads.get_download_service') as mock:
        service = AsyncMock()
        service.cleanup = AsyncMock()
        mock.return_value = service
        yield service


class TestDownloadsAPI:
    """Tests for downloads API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_single_download_job(self, client: TestClient, mock_download_service):
        """Test creating a single chapter download job."""
        # Mock download service
        job_id = uuid4()
        mock_download_service.enqueue_single_chapter_download.return_value = job_id
        
        # Mock database query for job retrieval
        with patch('kiremisu.api.downloads.select') as mock_select:
            mock_job = JobQueue(
                id=job_id,
                job_type="download",
                payload={
                    "job_id": str(job_id),
                    "download_type": "mangadx",
                    "manga_id": "manga-123",
                    "chapter_ids": ["ch-456"],
                    "batch_type": "single",
                },
                priority=3,
                status="pending",
                scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            
            with patch('kiremisu.api.downloads.get_db') as mock_db:
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = mock_job
                mock_session.execute.return_value = mock_result
                mock_db.return_value = mock_session
                
                # Make request
                request_data = {
                    "download_type": "single",
                    "manga_id": "manga-123",
                    "chapter_ids": ["ch-456"],
                    "priority": 3,
                }
                
                response = client.post("/api/downloads/", json=request_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == str(job_id)
        assert data["download_type"] == "mangadx"
        assert data["manga_id"] == "manga-123"
        assert data["status"] == "pending"
        
        # Verify service call
        mock_download_service.enqueue_single_chapter_download.assert_called_once()
        call_args = mock_download_service.enqueue_single_chapter_download.call_args
        assert call_args[1]["manga_id"] == "manga-123"
        assert call_args[1]["chapter_id"] == "ch-456"
        assert call_args[1]["priority"] == 3
    
    @pytest.mark.asyncio
    async def test_create_batch_download_job(self, client: TestClient, mock_download_service):
        """Test creating a batch download job."""
        job_id = uuid4()
        mock_download_service.enqueue_batch_download.return_value = job_id
        
        mock_job = JobQueue(
            id=job_id,
            job_type="download",
            payload={
                "job_id": str(job_id),
                "download_type": "mangadx",
                "manga_id": "manga-123",
                "chapter_ids": ["ch1", "ch2", "ch3"],
                "batch_type": "multiple",
            },
            priority=4,
            status="pending",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_job
            mock_session.execute.return_value = mock_result
            mock_db.return_value = mock_session
            
            request_data = {
                "download_type": "batch",
                "manga_id": "manga-123",
                "chapter_ids": ["ch1", "ch2", "ch3"],
                "priority": 4,
            }
            
            response = client.post("/api/downloads/", json=request_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["progress"]["total_chapters"]) == 0  # No progress data yet
        
        mock_download_service.enqueue_batch_download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_series_download_job(self, client: TestClient, mock_download_service):
        """Test creating a series download job."""
        job_id = uuid4()
        mock_download_service.enqueue_series_download.return_value = job_id
        
        mock_job = JobQueue(
            id=job_id,
            job_type="download",
            payload={
                "job_id": str(job_id),
                "download_type": "mangadx",
                "manga_id": "manga-123",
                "batch_type": "series",
            },
            priority=2,
            status="pending",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_job
            mock_session.execute.return_value = mock_result
            mock_db.return_value = mock_session
            
            request_data = {
                "download_type": "series",
                "manga_id": "manga-123",
                "priority": 2,
            }
            
            response = client.post("/api/downloads/", json=request_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        mock_download_service.enqueue_series_download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_download_job_validation_errors(self, client: TestClient):
        """Test download job creation with validation errors."""
        # Test single download without chapter_ids
        request_data = {
            "download_type": "single",
            "manga_id": "manga-123",
        }
        
        response = client.post("/api/downloads/", json=request_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test single download with multiple chapter_ids
        request_data = {
            "download_type": "single",
            "manga_id": "manga-123",
            "chapter_ids": ["ch1", "ch2"],
        }
        
        response = client.post("/api/downloads/", json=request_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test batch download without chapter_ids
        request_data = {
            "download_type": "batch",
            "manga_id": "manga-123",
        }
        
        response = client.post("/api/downloads/", json=request_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_list_download_jobs(self, client: TestClient, mock_download_service):
        """Test listing download jobs."""
        # Mock jobs
        job1 = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={"manga_id": "manga-1"},
            status="pending",
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        job2 = JobQueue(
            id=uuid4(),
            job_type="download",
            payload={"manga_id": "manga-2"},
            status="running",
            priority=5,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        mock_download_service.get_download_jobs.return_value = ([job1, job2], 2)
        
        # Mock status counts query
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = [("pending", 1), ("running", 1)]
            mock_session.execute.return_value = mock_result
            mock_db.return_value = mock_session
            
            response = client.get("/api/downloads/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 2
        assert data["pending_downloads"] == 1
        assert data["active_downloads"] == 1
        assert "pagination" in data
        
        mock_download_service.get_download_jobs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_download_job(self, client: TestClient):
        """Test getting a specific download job."""
        job_id = uuid4()
        job = JobQueue(
            id=job_id,
            job_type="download",
            payload={
                "manga_id": "manga-123",
                "progress": {
                    "total_chapters": 5,
                    "downloaded_chapters": 3,
                    "current_chapter": {"id": "ch4", "title": "Chapter 4"},
                    "current_chapter_progress": 0.6,
                }
            },
            status="running",
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = job
            mock_session.execute.return_value = mock_result
            mock_db.return_value = mock_session
            
            response = client.get(f"/api/downloads/{job_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(job_id)
        assert data["status"] == "running"
        assert data["progress"]["total_chapters"] == 5
        assert data["progress"]["downloaded_chapters"] == 3
    
    @pytest.mark.asyncio
    async def test_get_download_job_not_found(self, client: TestClient):
        """Test getting non-existent download job."""
        job_id = uuid4()
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result
            mock_db.return_value = mock_session
            
            response = client.get(f"/api/downloads/{job_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_cancel_download_job(self, client: TestClient, mock_download_service):
        """Test cancelling a download job."""
        job_id = uuid4()
        mock_download_service.cancel_download_job.return_value = True
        
        action_data = {
            "action": "cancel",
            "reason": "User requested cancellation"
        }
        
        response = client.post(f"/api/downloads/{job_id}/actions", json=action_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_id"] == str(job_id)
        assert data["action"] == "cancel"
        assert data["success"] is True
        assert data["new_status"] == "failed"
        
        mock_download_service.cancel_download_job.assert_called_once_with(
            mock_download_service.cancel_download_job.call_args[0][0], job_id
        )
    
    @pytest.mark.asyncio
    async def test_retry_download_job(self, client: TestClient, mock_download_service):
        """Test retrying a failed download job."""
        job_id = uuid4()
        mock_download_service.retry_download_job.return_value = True
        
        action_data = {
            "action": "retry"
        }
        
        response = client.post(f"/api/downloads/{job_id}/actions", json=action_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["action"] == "retry"
        assert data["success"] is True
        assert data["new_status"] == "pending"
        
        mock_download_service.retry_download_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unsupported_job_action(self, client: TestClient):
        """Test unsupported job action."""
        job_id = uuid4()
        
        action_data = {
            "action": "pause"
        }
        
        response = client.post(f"/api/downloads/{job_id}/actions", json=action_data)
        
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    
    @pytest.mark.asyncio
    async def test_create_bulk_downloads(self, client: TestClient, mock_download_service):
        """Test creating bulk downloads."""
        # Mock successful job creation
        job_ids = [uuid4(), uuid4(), uuid4()]
        mock_download_service.enqueue_single_chapter_download.side_effect = job_ids
        
        request_data = {
            "downloads": [
                {
                    "download_type": "single",
                    "manga_id": "manga-1",
                    "chapter_ids": ["ch1"],
                },
                {
                    "download_type": "single", 
                    "manga_id": "manga-2",
                    "chapter_ids": ["ch2"],
                },
                {
                    "download_type": "single",
                    "manga_id": "manga-3", 
                    "chapter_ids": ["ch3"],
                }
            ],
            "global_priority": 5,
            "stagger_delay_seconds": 0,  # No delay for testing
        }
        
        response = client.post("/api/downloads/bulk", json=request_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "scheduled"
        assert data["total_requested"] == 3
        assert data["successfully_queued"] == 3
        assert data["failed_to_queue"] == 0
        assert len(data["job_ids"]) == 3
        assert len(data["errors"]) == 0
        
        # Verify all jobs were created
        assert mock_download_service.enqueue_single_chapter_download.call_count == 3
    
    @pytest.mark.asyncio
    async def test_bulk_downloads_partial_failure(self, client: TestClient, mock_download_service):
        """Test bulk downloads with some failures."""
        # Mock partial failure
        job_id = uuid4()
        mock_download_service.enqueue_single_chapter_download.side_effect = [
            job_id,  # First succeeds
            Exception("Failed to create job"),  # Second fails
        ]
        
        request_data = {
            "downloads": [
                {
                    "download_type": "single",
                    "manga_id": "manga-1",
                    "chapter_ids": ["ch1"],
                },
                {
                    "download_type": "single",
                    "manga_id": "manga-2", 
                    "chapter_ids": ["ch2"],
                }
            ]
        }
        
        response = client.post("/api/downloads/bulk", json=request_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "partial"
        assert data["successfully_queued"] == 1
        assert data["failed_to_queue"] == 1
        assert len(data["errors"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_download_stats(self, client: TestClient):
        """Test getting download system statistics."""
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            
            # Mock status counts query
            status_result = AsyncMock()
            status_result.fetchall.return_value = [("pending", 5), ("running", 2), ("completed", 10), ("failed", 1)]
            
            # Mock today's activity queries
            created_result = AsyncMock()
            created_result.scalar.return_value = 8
            
            completed_result = AsyncMock()
            completed_result.scalar.return_value = 6
            
            # Mock average duration query
            duration_result = AsyncMock()
            duration_result.scalar.return_value = 180.0  # 3 minutes in seconds
            
            # Set up execute to return different results for different queries
            mock_session.execute.side_effect = [
                status_result,
                created_result,
                completed_result,
                duration_result,
            ]
            mock_db.return_value = mock_session
            
            response = client.get("/api/downloads/stats/overview")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_jobs"] == 18  # 5+2+10+1
        assert data["pending_jobs"] == 5
        assert data["active_jobs"] == 2
        assert data["completed_jobs"] == 10
        assert data["failed_jobs"] == 1
        assert data["jobs_created_today"] == 8
        assert data["jobs_completed_today"] == 6
        assert data["average_job_duration_minutes"] == 3.0  # 180 seconds = 3 minutes
        assert data["success_rate_percentage"] == (10/18*100)  # 10 completed out of 18 total
        assert "stats_generated_at" in data
    
    @pytest.mark.asyncio
    async def test_delete_download_job(self, client: TestClient):
        """Test deleting a download job."""
        job_id = uuid4()
        job = JobQueue(
            id=job_id,
            job_type="download",
            status="failed",
            payload={"manga_id": "manga-123"},
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = job
            mock_session.execute.return_value = mock_result
            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_db.return_value = mock_session
            
            response = client.delete(f"/api/downloads/{job_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        mock_session.delete.assert_called_once_with(job)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_running_job_without_force(self, client: TestClient):
        """Test deleting running job without force flag."""
        job_id = uuid4()
        job = JobQueue(
            id=job_id,
            job_type="download",
            status="running",
            payload={"manga_id": "manga-123"},
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = job
            mock_session.execute.return_value = mock_result
            mock_db.return_value = mock_session
            
            response = client.delete(f"/api/downloads/{job_id}")
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Cannot delete running job" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_running_job_with_force(self, client: TestClient):
        """Test deleting running job with force flag."""
        job_id = uuid4()
        job = JobQueue(
            id=job_id,
            job_type="download",
            status="running",
            payload={"manga_id": "manga-123"},
            priority=3,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = job
            mock_session.execute.return_value = mock_result
            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_db.return_value = mock_session
            
            response = client.delete(f"/api/downloads/{job_id}?force=true")
        
        assert response.status_code == status.HTTP_200_OK
        mock_session.delete.assert_called_once_with(job)


class TestDownloadAPIErrorHandling:
    """Tests for download API error handling."""
    
    @pytest.mark.asyncio
    async def test_download_service_error(self, client: TestClient):
        """Test handling download service errors."""
        with patch('kiremisu.api.downloads.get_download_service') as mock_get_service:
            service = AsyncMock()
            service.enqueue_single_chapter_download.side_effect = Exception("Service error")
            service.cleanup = AsyncMock()
            mock_get_service.return_value = service
            
            request_data = {
                "download_type": "single",
                "manga_id": "manga-123",
                "chapter_ids": ["ch-456"],
            }
            
            response = client.post("/api/downloads/", json=request_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create download job" in response.json()["detail"]
        
        # Verify cleanup was called
        service.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_error(self, client: TestClient, mock_download_service):
        """Test handling database errors."""
        job_id = uuid4()
        mock_download_service.enqueue_single_chapter_download.return_value = job_id
        
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_db.return_value = mock_session
            
            request_data = {
                "download_type": "single",
                "manga_id": "manga-123", 
                "chapter_ids": ["ch-456"],
            }
            
            response = client.post("/api/downloads/", json=request_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_download_service.cleanup.assert_called_once()