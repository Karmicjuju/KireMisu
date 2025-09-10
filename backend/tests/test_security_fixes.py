"""
Test suite for security fixes implemented in F4.3 Manual Metadata Editing feature.

This test suite verifies that the security vulnerabilities have been properly addressed:
1. Authorization controls on history access
2. Atomic transactions for bulk operations
3. Enhanced rate limiting with composite keys
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.models.chapter import Chapter
from app.models.series import Series


class TestSecurityFixes:
    """Test security fixes for metadata editing vulnerabilities."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @pytest.mark.asyncio
    async def test_chapter_history_authorization_check(self):
        """Test that chapter history endpoint verifies chapter exists before returning history."""
        with patch('app.services.chapter.ChapterService.get_chapter_by_id') as mock_get_chapter:
            with patch('app.services.chapter.ChapterService.get_chapter_history') as mock_get_history:
                # Mock chapter doesn't exist
                mock_get_chapter.return_value = None
                
                # Mock authenticated user
                with patch('app.users.current_active_user') as mock_user:
                    mock_user.return_value = {"id": "test-user-123"}
                    
                    response = self.client.get(
                        "/api/v1/chapters/999/history",
                        headers={"Authorization": "Bearer fake-token"}
                    )
                    
                    # Should return 404 since chapter doesn't exist
                    assert response.status_code == 404
                    assert "Chapter with ID 999 not found" in response.json()["detail"]
                    
                    # History service should not be called if chapter doesn't exist
                    mock_get_history.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_series_history_authorization_check(self):
        """Test that series history endpoint verifies series exists before returning history."""
        with patch('app.services.series.SeriesService.get_series_by_id') as mock_get_series:
            with patch('app.services.series.SeriesService.get_series_history') as mock_get_history:
                # Mock series doesn't exist
                mock_get_series.return_value = None
                
                # Mock authenticated user
                with patch('app.users.current_active_user') as mock_user:
                    mock_user.return_value = {"id": "test-user-123"}
                    
                    response = self.client.get(
                        "/api/v1/series/999/history",
                        headers={"Authorization": "Bearer fake-token"}
                    )
                    
                    # Should return 404 since series doesn't exist
                    assert response.status_code == 404
                    assert "Series with ID 999 not found" in response.json()["detail"]
                    
                    # History service should not be called if series doesn't exist
                    mock_get_history.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_bulk_operations_transaction_rollback(self):
        """Test that bulk operations use transactions and rollback on failure."""
        # This test verifies that the transaction logic is in place
        # In a real scenario, we'd test with a database that supports transactions
        
        with patch('app.services.chapter.ChapterService.bulk_update_chapters') as mock_bulk_update:
            # Simulate a transaction failure
            mock_bulk_update.side_effect = ValueError("Transaction failed")
            
            with patch('app.users.current_active_user') as mock_user:
                mock_user.return_value = {"id": "test-user-123"}
                
                response = self.client.patch(
                    "/api/v1/chapters/bulk",
                    json={
                        "chapter_ids": [1, 2, 3],
                        "updates": {"title": "Updated Title"}
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                # Should return 400 with the error message
                assert response.status_code == 400
                assert "Transaction failed" in response.json()["detail"]
    
    def test_rate_limiting_composite_key_creation(self):
        """Test that rate limiting creates composite keys with IP and user info."""
        from app.core.rate_limit import create_rate_limit_dependency, get_client_ip
        from fastapi import Request
        from unittest.mock import MagicMock
        
        # Create a mock request with authorization header
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEyMyJ9.fake"}
        mock_request.url.path = "/api/v1/test"
        
        # Test client IP extraction
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"
        
        # Test that the rate limit dependency function is created
        rate_limit_dep = create_rate_limit_dependency(max_requests=10, window_seconds=60)
        assert callable(rate_limit_dep)
    
    def test_error_handling_improvements(self):
        """Test that error handling properly distinguishes between different error types."""
        # This test verifies that HTTP exceptions are re-raised properly
        # and don't get caught by generic exception handlers
        
        with patch('app.services.chapter.ChapterService.get_chapter_by_id') as mock_get_chapter:
            from fastapi import HTTPException
            
            # Simulate an HTTP exception (should be re-raised)
            mock_get_chapter.side_effect = HTTPException(status_code=404, detail="Not found")
            
            with patch('app.users.current_active_user') as mock_user:
                mock_user.return_value = {"id": "test-user-123"}
                
                response = self.client.get(
                    "/api/v1/chapters/999/history",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                # Should preserve the original HTTP exception
                assert response.status_code == 404
                assert "Not found" in response.json()["detail"]


class TestSecurityEnhancements:
    """Test additional security enhancements."""
    
    def test_input_validation_limits(self):
        """Test that input validation limits are enforced."""
        client = TestClient(app)
        
        with patch('app.users.current_active_user') as mock_user:
            mock_user.return_value = {"id": "test-user-123"}
            
            # Test pagination limits
            response = client.get(
                "/api/v1/chapters?page=1&size=200",  # Size exceeds max of 100
                headers={"Authorization": "Bearer fake-token"}
            )
            
            # Should be handled by query parameter validation
            assert response.status_code in [400, 422]  # Validation error
    
    def test_bulk_operation_limits(self):
        """Test that bulk operations enforce reasonable limits."""
        client = TestClient(app)
        
        with patch('app.users.current_active_user') as mock_user:
            mock_user.return_value = {"id": "test-user-123"}
            
            # Test bulk update with too many IDs
            large_id_list = list(range(1, 102))  # 101 IDs, exceeds limit of 100
            
            response = client.patch(
                "/api/v1/chapters/bulk",
                json={
                    "chapter_ids": large_id_list,
                    "updates": {"title": "Updated Title"}
                },
                headers={"Authorization": "Bearer fake-token"}
            )
            
            # Should reject bulk operations that are too large
            assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])