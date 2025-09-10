"""
Unit tests for security fixes implemented in F4.3 Manual Metadata Editing feature.

These tests verify the security fixes at the code level without requiring 
a full application setup or authentication.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, Request


class TestAuthorizationControls:
    """Test authorization control improvements."""
    
    @pytest.mark.asyncio
    async def test_chapter_history_checks_chapter_exists(self):
        """Test that chapter history endpoint verifies chapter existence."""
        from app.api.v1.endpoints.chapters import get_chapter_history
        from app.services.chapter import ChapterService
        
        # Mock dependencies
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_service = MagicMock(spec=ChapterService)
        
        # Mock chapter doesn't exist
        mock_service.get_chapter_by_id = AsyncMock(return_value=None)
        
        # Should raise HTTPException when chapter doesn't exist
        with pytest.raises(HTTPException) as exc_info:
            await get_chapter_history(
                request=mock_request,
                chapter_id=999,
                limit=50,
                offset=0,
                current_user=mock_user,
                chapter_service=mock_service,
                _rate_limit=None
            )
        
        assert exc_info.value.status_code == 404
        assert "Chapter with ID 999 not found" in str(exc_info.value.detail)
        
        # Verify chapter existence was checked
        mock_service.get_chapter_by_id.assert_called_once_with(999)
    
    @pytest.mark.asyncio
    async def test_series_history_checks_series_exists(self):
        """Test that series history endpoint verifies series existence."""
        from app.api.v1.endpoints.series import get_series_history
        from app.services.series import SeriesService
        
        # Mock dependencies
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_service = MagicMock(spec=SeriesService)
        
        # Mock series doesn't exist
        mock_service.get_series_by_id = AsyncMock(return_value=None)
        
        # Should raise HTTPException when series doesn't exist
        with pytest.raises(HTTPException) as exc_info:
            await get_series_history(
                request=mock_request,
                series_id=999,
                limit=50,
                offset=0,
                current_user=mock_user,
                series_service=mock_service,
                _rate_limit=None
            )
        
        assert exc_info.value.status_code == 404
        assert "Series with ID 999 not found" in str(exc_info.value.detail)
        
        # Verify series existence was checked
        mock_service.get_series_by_id.assert_called_once_with(999)


class TestTransactionSafety:
    """Test transaction safety improvements in bulk operations."""
    
    @pytest.mark.asyncio
    async def test_bulk_chapter_update_uses_transaction(self):
        """Test that bulk chapter update uses database transactions."""
        from app.services.chapter import ChapterService
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Mock database session with transaction support
        mock_db = MagicMock(spec=AsyncSession)
        mock_transaction = AsyncMock()
        mock_db.begin.return_value.__aenter__.return_value = mock_transaction
        mock_db.begin.return_value.__aexit__.return_value = None
        
        # Mock repository and other dependencies
        with patch('app.services.chapter.ChapterRepository') as mock_repo_class:
            with patch('app.services.chapter.MetadataHistoryService') as mock_history_class:
                mock_repo = MagicMock()
                mock_history = MagicMock()
                mock_repo_class.return_value = mock_repo
                mock_history_class.return_value = mock_history
                
                # Mock successful operations
                mock_repo.get_by_id.return_value = MagicMock(id=1, number=1, series_id=1)
                mock_repo.bulk_update.return_value = [MagicMock(id=1, number=1)]
                mock_history.record_change = AsyncMock()
                
                service = ChapterService(mock_db)
                
                # Test data
                from app.schemas.chapter import BulkChapterUpdate, ChapterUpdate
                bulk_data = BulkChapterUpdate(
                    chapter_ids=[1],
                    updates=ChapterUpdate(title="New Title")
                )
                
                # Execute bulk update
                result = await service.bulk_update_chapters(bulk_data, user_id="test-user")
                
                # Verify transaction was used
                mock_db.begin.assert_called_once()
                mock_transaction.commit.assert_called_once()
                assert len(result) == 1
    
    @pytest.mark.asyncio  
    async def test_bulk_series_update_uses_transaction(self):
        """Test that bulk series update uses database transactions."""
        from app.services.series import SeriesService
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Mock database session with transaction support
        mock_db = MagicMock(spec=AsyncSession)
        mock_transaction = AsyncMock()
        mock_db.begin.return_value.__aenter__.return_value = mock_transaction
        mock_db.begin.return_value.__aexit__.return_value = None
        
        # Mock repository and other dependencies
        with patch('app.services.series.AsyncSeriesRepository') as mock_repo_class:
            with patch('app.services.series.MetadataHistoryService') as mock_history_class:
                mock_repo = MagicMock()
                mock_history = MagicMock()
                mock_repo_class.return_value = mock_repo
                mock_history_class.return_value = mock_history
                
                # Mock successful operations
                mock_series = MagicMock(id=1, title="Test Series")
                mock_repo.get_series_by_id.return_value = mock_series
                mock_repo.get_series_by_title.return_value = None
                
                service = SeriesService(mock_db)
                
                # Mock the update_series method to return a series
                with patch.object(service, 'update_series', new_callable=AsyncMock) as mock_update:
                    mock_update.return_value = mock_series
                    
                    # Test data
                    from app.schemas.series import SeriesUpdate
                    update_data = SeriesUpdate(title="Updated Title")
                    
                    # Execute bulk update
                    result = await service.bulk_update_series([1], update_data, user_id="test-user")
                    
                    # Verify transaction was used
                    mock_db.begin.assert_called_once()
                    mock_transaction.commit.assert_called_once()
                    assert len(result) == 1


class TestRateLimitingEnhancements:
    """Test rate limiting security enhancements."""
    
    def test_composite_key_generation_with_user(self):
        """Test that rate limiting generates composite keys with user information."""
        from app.core.rate_limit import create_rate_limit_dependency
        import json
        import base64
        
        # Create a simple JWT token for testing
        payload = {"sub": "user-123"}
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        fake_token = f"header.{payload_b64}.signature"
        
        # Mock request with authorization
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {"Authorization": f"Bearer {fake_token}"}
        mock_request.url.path = "/api/v1/test"
        
        # Mock rate limiter
        with patch('app.core.rate_limit.get_rate_limiter') as mock_get_limiter:
            mock_limiter = MagicMock()
            mock_limiter.is_allowed.return_value = (True, 0)
            mock_get_limiter.return_value = mock_limiter
            
            # Create and test rate limit dependency
            rate_limit_dep = create_rate_limit_dependency(max_requests=10, window_seconds=60)
            rate_limit_dep(mock_request)
            
            # Verify composite key was used
            mock_limiter.is_allowed.assert_called_once()
            call_args = mock_limiter.is_allowed.call_args[0]
            rate_key = call_args[0]
            
            # Key should contain IP, user ID, and endpoint
            assert "192.168.1.100" in rate_key
            assert "user-123" in rate_key
            assert "/api/v1/test" in rate_key
    
    def test_composite_key_generation_anonymous(self):
        """Test rate limiting for unauthenticated requests."""
        from app.core.rate_limit import create_rate_limit_dependency
        
        # Mock request without authorization
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}
        mock_request.url.path = "/api/v1/public"
        
        # Mock rate limiter
        with patch('app.core.rate_limit.get_rate_limiter') as mock_get_limiter:
            mock_limiter = MagicMock()
            mock_limiter.is_allowed.return_value = (True, 0)
            mock_get_limiter.return_value = mock_limiter
            
            # Create and test rate limit dependency
            rate_limit_dep = create_rate_limit_dependency(max_requests=10, window_seconds=60)
            rate_limit_dep(mock_request)
            
            # Verify composite key was used with anonymous user
            mock_limiter.is_allowed.assert_called_once()
            call_args = mock_limiter.is_allowed.call_args[0]
            rate_key = call_args[0]
            
            # Key should contain IP, anonymous marker, and endpoint
            assert "192.168.1.100" in rate_key
            assert "anonymous" in rate_key
            assert "/api/v1/public" in rate_key
    
    def test_rate_limit_exceeded_response(self):
        """Test proper HTTP response when rate limit is exceeded."""
        from app.core.rate_limit import create_rate_limit_dependency
        
        # Mock request
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}
        mock_request.url.path = "/api/v1/test"
        
        # Mock rate limiter to indicate limit exceeded
        with patch('app.core.rate_limit.get_rate_limiter') as mock_get_limiter:
            mock_limiter = MagicMock()
            mock_limiter.is_allowed.return_value = (False, 60)  # Blocked, retry in 60 seconds
            mock_get_limiter.return_value = mock_limiter
            
            # Create rate limit dependency
            rate_limit_dep = create_rate_limit_dependency(max_requests=10, window_seconds=60)
            
            # Should raise HTTPException when rate limit exceeded
            with pytest.raises(HTTPException) as exc_info:
                rate_limit_dep(mock_request)
            
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value.detail)
            assert exc_info.value.headers["Retry-After"] == "60"


class TestErrorHandling:
    """Test improved error handling."""
    
    @pytest.mark.asyncio
    async def test_http_exceptions_preserved(self):
        """Test that HTTPExceptions are re-raised properly."""
        from app.api.v1.endpoints.chapters import get_chapter_history
        from app.services.chapter import ChapterService
        
        # Mock dependencies
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_service = MagicMock(spec=ChapterService)
        
        # Mock service to raise HTTPException
        mock_service.get_chapter_by_id = AsyncMock(
            side_effect=HTTPException(status_code=403, detail="Forbidden")
        )
        
        # HTTPException should be re-raised as-is
        with pytest.raises(HTTPException) as exc_info:
            await get_chapter_history(
                request=mock_request,
                chapter_id=1,
                limit=50,
                offset=0,
                current_user=mock_user,
                chapter_service=mock_service,
                _rate_limit=None
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Forbidden"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])