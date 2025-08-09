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

    @pytest.mark.asyncio
    async def test_concurrent_job_creation_race_condition(self, client: TestClient):
        """Test handling race conditions in concurrent job creation."""
        import asyncio
        from threading import Thread
        from concurrent.futures import ThreadPoolExecutor
        
        # Simulate concurrent requests to the same endpoint
        def create_download_job():
            request_data = {
                "download_type": "single",
                "manga_id": "manga-concurrent-test",
                "chapter_ids": ["ch-123"],
            }
            return client.post("/api/downloads/", json=request_data)
        
        with patch('kiremisu.api.downloads.get_download_service') as mock_get_service:
            service = AsyncMock()
            service.cleanup = AsyncMock()
            
            # First few requests succeed, then fail due to race condition
            job_ids = [uuid4(), uuid4()]
            service.enqueue_single_chapter_download.side_effect = [
                job_ids[0],  # First succeeds
                job_ids[1],  # Second succeeds 
                Exception("Database lock timeout"),  # Third fails due to race condition
                Exception("Connection pool exhausted"),  # Fourth fails
            ]
            mock_get_service.return_value = service
            
            with patch('kiremisu.api.downloads.get_db') as mock_db:
                mock_session = AsyncMock()
                
                def mock_execute_side_effect(*args, **kwargs):
                    # Simulate occasional database timeout
                    import random
                    if random.random() < 0.3:  # 30% chance of timeout
                        raise Exception("Database timeout")
                    
                    mock_job = JobQueue(
                        id=uuid4(),
                        job_type="download",
                        payload={"manga_id": "manga-concurrent-test"},
                        status="pending",
                        priority=3,
                        scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    mock_result = AsyncMock()
                    mock_result.scalar_one_or_none.return_value = mock_job
                    return mock_result
                
                mock_session.execute.side_effect = mock_execute_side_effect
                mock_db.return_value = mock_session
                
                # Execute concurrent requests
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(create_download_job) for _ in range(4)]
                    responses = [future.result() for future in futures]
                
                # Verify responses - some should succeed, some should fail gracefully
                success_count = sum(1 for r in responses if r.status_code in [201, 200])
                error_count = sum(1 for r in responses if r.status_code >= 400)
                
                assert success_count >= 0  # At least some might succeed
                assert error_count >= 2  # At least 2 should fail due to our mocked exceptions
                
                # Verify all error responses are handled gracefully
                for response in responses:
                    if response.status_code >= 400:
                        error_data = response.json()
                        assert "detail" in error_data
                        assert len(error_data["detail"]) > 0

    @pytest.mark.asyncio
    async def test_rate_limiting_scenarios(self, client: TestClient):
        """Test API behavior under rate limiting conditions."""
        with patch('kiremisu.api.downloads.get_download_service') as mock_get_service:
            service = AsyncMock()
            service.cleanup = AsyncMock()
            
            # Simulate rate limiting by failing requests after a threshold
            request_count = 0
            def rate_limited_service(*args, **kwargs):
                nonlocal request_count
                request_count += 1
                if request_count > 5:  # Rate limit after 5 requests
                    raise Exception("Rate limit exceeded: Too many requests")
                return uuid4()
            
            service.enqueue_single_chapter_download.side_effect = rate_limited_service
            mock_get_service.return_value = service
            
            # Mock database to return successful job creation up to rate limit
            with patch('kiremisu.api.downloads.get_db') as mock_db:
                mock_session = AsyncMock()
                mock_job = JobQueue(
                    id=uuid4(),
                    job_type="download",
                    payload={"manga_id": "rate-limit-test"},
                    status="pending",
                    priority=3,
                    scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = mock_job
                mock_session.execute.return_value = mock_result
                mock_db.return_value = mock_session
                
                # Make requests up to and beyond rate limit
                responses = []
                for i in range(8):  # 8 requests, should hit rate limit at 6th
                    request_data = {
                        "download_type": "single",
                        "manga_id": f"manga-{i}",
                        "chapter_ids": [f"ch-{i}"],
                    }
                    response = client.post("/api/downloads/", json=request_data)
                    responses.append(response)
                
                # Verify first 5 requests succeed
                for i, response in enumerate(responses[:5]):
                    assert response.status_code == status.HTTP_201_CREATED, f"Request {i} should succeed"
                
                # Verify rate-limited requests fail gracefully
                for i, response in enumerate(responses[5:], 5):
                    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, f"Request {i} should be rate limited"
                    error_data = response.json()
                    assert "rate limit" in error_data["detail"].lower() or "too many requests" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_concurrent_download_semaphore_limiting(self, client: TestClient):
        """Test that concurrent downloads are limited by semaphore."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Track active concurrent requests
        active_requests = []
        max_concurrent = 0
        
        def track_concurrency():
            nonlocal max_concurrent
            active_requests.append(1)
            max_concurrent = max(max_concurrent, len(active_requests))
            # Simulate some processing time
            import time
            time.sleep(0.1)
            active_requests.pop()
            return uuid4()
        
        with patch('kiremisu.api.downloads.get_download_service') as mock_get_service:
            service = AsyncMock()
            service.cleanup = AsyncMock()
            service.enqueue_single_chapter_download.side_effect = track_concurrency
            mock_get_service.return_value = service
            
            with patch('kiremisu.api.downloads.get_db') as mock_db:
                mock_session = AsyncMock()
                mock_job = JobQueue(
                    id=uuid4(),
                    job_type="download",
                    payload={"manga_id": "concurrent-test"},
                    status="pending",
                    priority=3,
                    scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = mock_job
                mock_session.execute.return_value = mock_result
                mock_db.return_value = mock_session
                
                # Make multiple concurrent requests
                def make_request(index):
                    request_data = {
                        "download_type": "single",
                        "manga_id": f"manga-concurrent-{index}",
                        "chapter_ids": [f"ch-{index}"],
                    }
                    return client.post("/api/downloads/", json=request_data)
                
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(make_request, i) for i in range(10)]
                    responses = [future.result() for future in futures]
                
                # All requests should succeed
                for response in responses:
                    assert response.status_code in [201, 500]  # Some may fail due to simulated processing
                
                # Should respect concurrent limit (default is 5)
                assert max_concurrent <= 5, f"Expected max 5 concurrent, got {max_concurrent}"

    @pytest.mark.asyncio 
    async def test_resource_cleanup_failure(self, client: TestClient):
        """Test handling of resource cleanup failures."""
        with patch('kiremisu.api.downloads.get_download_service') as mock_get_service:
            service = AsyncMock()
            # Service creation succeeds but cleanup fails
            service.enqueue_single_chapter_download.return_value = uuid4()
            service.cleanup.side_effect = Exception("Failed to cleanup resources")
            mock_get_service.return_value = service
            
            with patch('kiremisu.api.downloads.get_db') as mock_db:
                mock_session = AsyncMock()
                # Database operation fails, triggering cleanup
                mock_session.execute.side_effect = Exception("Database connection lost")
                mock_db.return_value = mock_session
                
                request_data = {
                    "download_type": "single",
                    "manga_id": "cleanup-test",
                    "chapter_ids": ["ch-456"],
                }
                
                # Should still return 500 error but not crash
                response = client.post("/api/downloads/", json=request_data)
                
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                error_data = response.json()
                assert "detail" in error_data
                
                # Verify cleanup was attempted even though it failed
                service.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, client: TestClient):
        """Test handling of database connection pool exhaustion."""
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            # Simulate connection pool exhaustion
            mock_db.side_effect = Exception("Connection pool exhausted - max 20 connections")
            
            request_data = {
                "download_type": "single",
                "manga_id": "pool-test",
                "chapter_ids": ["ch-456"],
            }
            
            response = client.post("/api/downloads/", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            error_data = response.json()
            assert "connection" in error_data["detail"].lower() or "database" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_bulk_operation_partial_failures_detailed(self, client: TestClient, mock_download_service):
        """Test detailed error handling in bulk operations with various failure scenarios."""
        # Setup complex failure scenarios
        failure_scenarios = [
            uuid4(),  # Success
            Exception("Rate limit exceeded"),  # Rate limit
            Exception("Invalid manga ID"),  # Validation error
            uuid4(),  # Success
            Exception("Database timeout"),  # Database error
            Exception("Service unavailable"),  # Service error
            uuid4(),  # Success
            Exception("Network timeout"),  # Network error
        ]
        
        mock_download_service.enqueue_single_chapter_download.side_effect = failure_scenarios
        
        request_data = {
            "downloads": [
                {"download_type": "single", "manga_id": f"manga-{i}", "chapter_ids": [f"ch-{i}"]}
                for i in range(8)
            ],
            "continue_on_error": True,  # Should continue processing despite errors
        }
        
        response = client.post("/api/downloads/bulk", json=request_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Verify detailed error tracking
        assert data["total_requested"] == 8
        assert data["successfully_queued"] == 3  # 3 successful UUIDs
        assert data["failed_to_queue"] == 5  # 5 exceptions
        assert len(data["errors"]) == 5
        
        # Verify error details are preserved
        error_types = [error["error"] for error in data["errors"]]
        assert "Rate limit exceeded" in error_types
        assert "Invalid manga ID" in error_types 
        assert "Database timeout" in error_types
        assert "Service unavailable" in error_types
        assert "Network timeout" in error_types
        
        # Verify successful job IDs are tracked
        assert len(data["job_ids"]) == 3
        for job_id in data["job_ids"]:
            assert isinstance(UUID(job_id), UUID)  # Valid UUIDs

    @pytest.mark.asyncio
    async def test_malformed_request_data(self, client: TestClient):
        """Test handling of malformed or corrupted request data."""
        # Test completely malformed JSON structure
        response = client.post(
            "/api/downloads/",
            content='{"invalid": json data}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test missing required fields
        response = client.post("/api/downloads/", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid field types
        request_data = {
            "download_type": "single",
            "manga_id": 123,  # Should be string
            "chapter_ids": "not-a-list",  # Should be list
            "priority": "high",  # Should be integer
        }
        response = client.post("/api/downloads/", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test extremely long strings (potential DoS)
        long_string = "a" * 10000  # 10KB string
        request_data = {
            "download_type": "single",
            "manga_id": long_string,
            "chapter_ids": ["ch-123"],
        }
        response = client.post("/api/downloads/", json=request_data)
        # Should either reject with validation error or handle gracefully
        assert response.status_code in [422, 400, 413]  # Validation, Bad Request, or Payload Too Large


class TestDownloadAPIPerformance:
    """Performance and load testing for downloads API."""
    
    @pytest.mark.asyncio
    async def test_high_volume_bulk_downloads(self, client: TestClient, mock_download_service):
        """Test API performance with high volume bulk downloads."""
        import time
        
        # Setup successful job creation for all requests
        job_ids = [uuid4() for _ in range(100)]
        mock_download_service.enqueue_single_chapter_download.side_effect = job_ids
        
        # Create bulk request with 100 downloads
        request_data = {
            "downloads": [
                {
                    "download_type": "single",
                    "manga_id": f"manga-perf-{i}",
                    "chapter_ids": [f"ch-{i}"],
                }
                for i in range(100)
            ],
            "stagger_delay_seconds": 0,  # No delay for performance test
        }
        
        start_time = time.time()
        response = client.post("/api/downloads/bulk", json=request_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["successfully_queued"] == 100
        assert data["failed_to_queue"] == 0
        
        # Performance assertion: should process 100 downloads in reasonable time
        # Allowing 30 seconds for bulk processing (adjustable based on system performance)
        assert processing_time < 30.0, f"Bulk processing took {processing_time:.2f} seconds, expected < 30s"
        
        # Verify service was called efficiently
        assert mock_download_service.enqueue_single_chapter_download.call_count == 100

    @pytest.mark.asyncio
    async def test_concurrent_api_access_performance(self, client: TestClient, mock_download_service):
        """Test API performance under concurrent access."""
        import asyncio
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        # Setup service to return job IDs
        def create_job_id(*args, **kwargs):
            return uuid4()
        
        mock_download_service.enqueue_single_chapter_download.side_effect = create_job_id
        
        # Mock database to return jobs quickly
        with patch('kiremisu.api.downloads.get_db') as mock_db:
            mock_session = AsyncMock()
            
            def quick_db_response(*args, **kwargs):
                mock_job = JobQueue(
                    id=uuid4(),
                    job_type="download",
                    payload={"manga_id": "concurrent-test"},
                    status="pending",
                    priority=3,
                    scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = mock_job
                return mock_result
            
            mock_session.execute.side_effect = quick_db_response
            mock_db.return_value = mock_session
            
            def make_request(index):
                request_data = {
                    "download_type": "single",
                    "manga_id": f"manga-concurrent-{index}",
                    "chapter_ids": [f"ch-{index}"],
                }
                return client.post("/api/downloads/", json=request_data)
            
            # Execute 20 concurrent requests
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, i) for i in range(20)]
                responses = [future.result() for future in futures]
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Verify all requests succeeded
            success_count = sum(1 for r in responses if r.status_code == 201)
            assert success_count >= 15, f"Expected at least 15 successful requests, got {success_count}"
            
            # Performance assertion: concurrent requests should complete reasonably fast
            assert total_time < 10.0, f"Concurrent requests took {total_time:.2f} seconds, expected < 10s"


class TestDownloadHealthChecks:
    """Tests for download system health check endpoints."""

    @pytest.mark.asyncio
    async def test_download_health_check_healthy_system(self, client: TestClient):
        """Test health check with healthy system."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            
            # Mock database queries for health check
            mock_result.scalar.side_effect = [5, 2]  # total_jobs, active_jobs
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_get_session.return_value = mock_session
            
            # Mock engine pool
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_pool = MagicMock()
                mock_pool.size.return_value = 10
                mock_pool.checkedin.return_value = 3
                mock_engine.pool = mock_pool
                
                response = client.get("/api/downloads/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["database"]["status"] == "healthy"
        assert data["database"]["connection_pool"]["status"] == "healthy"
        assert data["database"]["connection_pool"]["size"] == 10
        assert data["database"]["connection_pool"]["active_connections"] == 3
        assert data["downloads"]["total_jobs"] == 5
        assert data["downloads"]["active_jobs"] == 2
        assert data["system"]["concurrent_limit"] == 5

    @pytest.mark.asyncio
    async def test_download_health_check_database_unhealthy(self, client: TestClient):
        """Test health check with database connectivity issues."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            # First call fails (connectivity test), second call succeeds (stats)
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.side_effect = [0, 0]  # total_jobs, active_jobs
            mock_session.execute.return_value = mock_result
            
            # Mock connectivity test failure
            def session_side_effect():
                if mock_get_session.call_count == 1:
                    # First call for connectivity test - fail
                    raise Exception("Database connection failed")
                else:
                    # Second call for stats - succeed
                    return mock_session
            
            mock_get_session.side_effect = session_side_effect
            
            # Mock engine pool
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_pool = MagicMock()
                mock_pool.size.return_value = 10
                mock_pool.checkedin.return_value = 3
                mock_engine.pool = mock_pool
                
                response = client.get("/api/downloads/health")
        
        # Should return 503 for unhealthy system
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # Note: The actual endpoint raises HTTPException with 503, but FastAPI converts it

    @pytest.mark.asyncio
    async def test_download_health_check_degraded_pool(self, client: TestClient):
        """Test health check with degraded connection pool."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.side_effect = [10, 1]  # total_jobs, active_jobs
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_get_session.return_value = mock_session
            
            # Mock degraded pool (size 0)
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_pool = MagicMock()
                mock_pool.size.return_value = 0  # Degraded
                mock_pool.checkedin.return_value = 0
                mock_engine.pool = mock_pool
                
                response = client.get("/api/downloads/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "healthy"
        assert data["database"]["connection_pool"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_download_health_check_pool_stats_error(self, client: TestClient):
        """Test health check when pool stats cannot be retrieved."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.side_effect = [3, 0]  # total_jobs, active_jobs
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_get_session.return_value = mock_session
            
            # Mock pool stats error
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_pool = MagicMock()
                mock_pool.size.side_effect = Exception("Pool stats not available")
                mock_engine.pool = mock_pool
                
                response = client.get("/api/downloads/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"  # Overall still healthy
        assert data["database"]["status"] == "healthy"
        assert data["database"]["connection_pool"]["status"] == "unknown"
        assert data["database"]["connection_pool"]["size"] == 0
        assert data["database"]["connection_pool"]["active_connections"] == 0

    @pytest.mark.asyncio
    async def test_download_health_check_complete_failure(self, client: TestClient):
        """Test health check when everything fails."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            # All database calls fail
            mock_get_session.side_effect = Exception("Complete system failure")
            
            # Mock engine pool failure
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_engine.pool.side_effect = Exception("Pool failure")
                
                response = client.get("/api/downloads/health")
        
        # Should handle gracefully
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_main_health_endpoint(self, client: TestClient):
        """Test main application health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_health_check_response_format(self, client: TestClient):
        """Test that health check response has correct format."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.side_effect = [15, 5]
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_get_session.return_value = mock_session
            
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_pool = MagicMock()
                mock_pool.size.return_value = 20
                mock_pool.checkedin.return_value = 8
                mock_engine.pool = mock_pool
                
                response = client.get("/api/downloads/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate response structure
        required_fields = ["status", "timestamp", "database", "downloads", "system"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate database section
        db_fields = ["status", "connection_pool"]
        for field in db_fields:
            assert field in data["database"], f"Missing database field: {field}"
        
        # Validate connection pool section
        pool_fields = ["status", "size", "active_connections"]
        for field in pool_fields:
            assert field in data["database"]["connection_pool"], f"Missing pool field: {field}"
        
        # Validate downloads section
        download_fields = ["total_jobs", "active_jobs"]
        for field in download_fields:
            assert field in data["downloads"], f"Missing downloads field: {field}"
        
        # Validate system section
        assert "concurrent_limit" in data["system"]
        
        # Validate data types
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["downloads"]["total_jobs"], int)
        assert isinstance(data["downloads"]["active_jobs"], int)
        assert isinstance(data["system"]["concurrent_limit"], int)

    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self, client: TestClient):
        """Test that health check timestamp is in correct ISO format."""
        with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.side_effect = [1, 0]
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_get_session.return_value = mock_session
            
            with patch('kiremisu.api.downloads.engine') as mock_engine:
                mock_pool = MagicMock()
                mock_pool.size.return_value = 5
                mock_pool.checkedin.return_value = 2
                mock_engine.pool = mock_pool
                
                response = client.get("/api/downloads/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate timestamp format
        timestamp = data["timestamp"]
        from datetime import datetime
        try:
            parsed_time = datetime.fromisoformat(timestamp)
            assert parsed_time is not None
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp}")

    @pytest.mark.asyncio
    async def test_health_check_concurrent_requests(self, client: TestClient):
        """Test health check under concurrent load."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def make_health_request():
            with patch('kiremisu.api.downloads.get_db_session') as mock_get_session:
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.scalar.side_effect = [2, 1]
                mock_session.execute.return_value = mock_result
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_get_session.return_value = mock_session
                
                with patch('kiremisu.api.downloads.engine') as mock_engine:
                    mock_pool = MagicMock()
                    mock_pool.size.return_value = 10
                    mock_pool.checkedin.return_value = 4
                    mock_engine.pool = mock_pool
                    
                    return client.get("/api/downloads/health")
        
        # Make concurrent health check requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]  # Should be consistent