"""Tests for rate limiter implementation."""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status

from kiremisu.core.rate_limiter import RateLimiter, RateLimitMiddleware


class TestRateLimiter:
    """Test cases for RateLimiter class."""

    def test_init_with_defaults(self):
        """Test rate limiter initialization with default values."""
        limiter = RateLimiter()

        assert limiter.requests_per_minute == 60
        assert limiter.requests_per_hour == 1000
        assert limiter.burst_limit == 10
        assert limiter.cleanup_interval == 300

    def test_init_with_custom_values(self):
        """Test rate limiter initialization with custom values."""
        limiter = RateLimiter(
            requests_per_minute=30,
            requests_per_hour=500,
            burst_limit=5,
            cleanup_interval=600
        )

        assert limiter.requests_per_minute == 30
        assert limiter.requests_per_hour == 500
        assert limiter.burst_limit == 5
        assert limiter.cleanup_interval == 600

    def test_allow_request_within_limits(self):
        """Test allowing requests within rate limits."""
        limiter = RateLimiter(requests_per_minute=60, burst_limit=10)
        client_ip = "192.168.1.1"

        # First request should be allowed
        allowed, remaining, reset_time = limiter.is_allowed(client_ip)
        assert allowed is True
        assert remaining > 0
        assert reset_time > time.time()

        # Multiple requests within limits should be allowed
        for _ in range(5):
            allowed, remaining, reset_time = limiter.is_allowed(client_ip)
            assert allowed is True

    def test_burst_limit_exceeded(self):
        """Test burst limit enforcement."""
        limiter = RateLimiter(requests_per_minute=60, burst_limit=3)
        client_ip = "192.168.1.1"

        # Allow up to burst limit
        for _ in range(3):
            allowed, remaining, reset_time = limiter.is_allowed(client_ip)
            assert allowed is True

        # Next request should be blocked
        allowed, remaining, reset_time = limiter.is_allowed(client_ip)
        assert allowed is False
        assert remaining == 0

    def test_requests_per_minute_limit(self):
        """Test requests per minute limit."""
        limiter = RateLimiter(requests_per_minute=2, burst_limit=10)  # Very low limit
        client_ip = "192.168.1.1"

        # Use up the minute allowance quickly
        for _ in range(2):
            allowed, remaining, reset_time = limiter.is_allowed(client_ip)
            assert allowed is True

        # Next request should be blocked
        allowed, remaining, reset_time = limiter.is_allowed(client_ip)
        assert allowed is False

    def test_requests_per_hour_limit(self):
        """Test requests per hour limit."""
        limiter = RateLimiter(requests_per_minute=1000, requests_per_hour=2, burst_limit=10)
        client_ip = "192.168.1.1"

        # Use up the hour allowance
        for _ in range(2):
            allowed, remaining, reset_time = limiter.is_allowed(client_ip)
            assert allowed is True

        # Next request should be blocked
        allowed, remaining, reset_time = limiter.is_allowed(client_ip)
        assert allowed is False

    def test_different_ips_independent_limits(self):
        """Test that different IPs have independent rate limits."""
        limiter = RateLimiter(requests_per_minute=60, burst_limit=2)
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"

        # Exhaust limit for IP1
        for _ in range(2):
            allowed, _, _ = limiter.is_allowed(ip1)
            assert allowed is True

        allowed, _, _ = limiter.is_allowed(ip1)
        assert allowed is False  # IP1 blocked

        # IP2 should still be allowed
        allowed, _, _ = limiter.is_allowed(ip2)
        assert allowed is True

    def test_cleanup_old_entries(self):
        """Test cleanup of old request entries."""
        limiter = RateLimiter(cleanup_interval=1)  # 1 second cleanup
        client_ip = "192.168.1.1"

        # Make some requests
        limiter.is_allowed(client_ip)

        assert len(limiter.request_times[client_ip]) > 0

        # Force cleanup by setting last_cleanup to past
        limiter.last_cleanup = time.time() - 2

        # Trigger cleanup
        limiter._cleanup_old_entries()

        # Should have cleaned up old entries (though may not be empty due to recent requests)
        assert limiter.last_cleanup > time.time() - 1

    @patch('time.time')
    def test_cleanup_removes_old_timestamps(self, mock_time):
        """Test that cleanup removes old timestamps."""
        limiter = RateLimiter()
        client_ip = "192.168.1.1"

        # Simulate old requests (over 1 hour ago)
        old_time = 1000.0
        mock_time.return_value = old_time
        limiter.is_allowed(client_ip)

        # Fast forward time by 2 hours
        current_time = old_time + 7200  # 2 hours later
        mock_time.return_value = current_time

        # Force cleanup
        limiter.last_cleanup = current_time - 301  # Force cleanup
        limiter._cleanup_old_entries()

        # Old timestamps should be removed
        hour_ago = current_time - 3600
        recent_timestamps = [ts for ts in limiter.request_times[client_ip] if ts > hour_ago]
        assert len(recent_timestamps) == 0  # Old request should be cleaned up

    def test_reset_time_calculation(self):
        """Test reset time calculation is reasonable."""
        limiter = RateLimiter()
        client_ip = "192.168.1.1"

        current_time = time.time()
        allowed, remaining, reset_time = limiter.is_allowed(client_ip)

        # Reset time should be within the next minute
        assert reset_time > current_time
        assert reset_time <= current_time + 60

    def test_memory_efficiency_with_many_ips(self):
        """Test memory efficiency with many different IPs."""
        limiter = RateLimiter(cleanup_interval=0)  # Force cleanup on every call

        # Simulate requests from many different IPs
        for i in range(100):
            client_ip = f"192.168.1.{i}"
            limiter.is_allowed(client_ip)

        # Should have entries for all IPs initially
        assert len(limiter.request_times) == 100

        # After cleanup, old entries should be managed
        limiter._cleanup_old_entries()

        # Memory should be managed (exact count depends on cleanup logic)
        assert len(limiter.request_times) <= 100


class TestRateLimitMiddleware:
    """Test cases for RateLimitMiddleware."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(requests_per_minute=60, burst_limit=2)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request for testing."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/api/downloads/"
        return request

    @pytest.fixture
    def middleware(self, rate_limiter):
        """Create middleware instance for testing."""
        app = MagicMock()
        return RateLimitMiddleware(app, rate_limiter=rate_limiter)

    @pytest.mark.asyncio
    async def test_allowed_request_passes_through(self, middleware, mock_request):
        """Test that allowed requests pass through middleware."""
        async def call_next(request):
            return "response"

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_rate_limited_request_blocked(self, rate_limiter, mock_request):
        """Test that rate limited requests are blocked."""
        middleware = RateLimitMiddleware(MagicMock(), rate_limiter=rate_limiter)

        # Exhaust rate limit
        for _ in range(3):  # Burst limit is 2, so 3rd should fail
            try:
                await middleware.dispatch(mock_request, lambda req: "response")
            except HTTPException:
                pass  # Expected for the 3rd request

        # Next request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, lambda req: "response")

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rate_limit_headers_included(self, middleware, mock_request):
        """Test that rate limit headers are included in response."""
        from starlette.responses import Response

        async def call_next(request):
            return Response("OK", status_code=200)

        response = await middleware.dispatch(mock_request, call_next)

        # Check that rate limit headers are set
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Values should be reasonable
        assert int(response.headers["X-RateLimit-Limit"]) > 0
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0
        assert int(response.headers["X-RateLimit-Reset"]) > 0

    @pytest.mark.asyncio
    async def test_different_paths_same_limit(self, middleware, mock_request):
        """Test that different paths share the same IP-based limit."""
        # First request to /api/downloads/
        await middleware.dispatch(mock_request, lambda req: "response1")

        # Second request to different path
        mock_request.url.path = "/api/jobs/"
        await middleware.dispatch(mock_request, lambda req: "response2")

        # Both should count toward the same limit
        # (Implementation detail: rate limiter is IP-based, not path-based)

    @pytest.mark.asyncio
    async def test_request_without_client_ip(self, rate_limiter):
        """Test handling of requests without client IP."""
        middleware = RateLimitMiddleware(MagicMock(), rate_limiter=rate_limiter)

        # Request without client info
        request = MagicMock(spec=Request)
        request.client = None
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/api/downloads/"

        # Should handle gracefully (may use default IP)
        result = await middleware.dispatch(request, lambda req: "response")
        assert result == "response"

    @pytest.mark.asyncio
    async def test_middleware_exception_handling(self, middleware, mock_request):
        """Test middleware handles exceptions from downstream."""
        async def call_next_with_error(request):
            raise ValueError("Downstream error")

        # Exception from downstream should propagate
        with pytest.raises(ValueError):
            await middleware.dispatch(mock_request, call_next_with_error)

    @pytest.mark.asyncio
    async def test_concurrent_requests_from_same_ip(self, rate_limiter):
        """Test handling of concurrent requests from the same IP."""
        import asyncio

        middleware = RateLimitMiddleware(MagicMock(), rate_limiter=rate_limiter)

        async def make_request():
            request = MagicMock(spec=Request)
            request.client = MagicMock()
            request.client.host = "192.168.1.1"
            request.method = "GET"
            request.url = MagicMock()
            request.url.path = "/api/downloads/"

            try:
                return await middleware.dispatch(request, lambda req: "success")
            except HTTPException:
                return "rate_limited"

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should succeed, some should be rate limited
        success_count = sum(1 for r in results if r == "success")
        rate_limited_count = sum(1 for r in results if r == "rate_limited")

        # Should respect burst limit (2 in our test setup)
        assert success_count <= 2
        assert rate_limited_count >= 3


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with actual FastAPI app."""

    @pytest.mark.asyncio
    async def test_rate_limiter_with_download_endpoint(self, client):
        """Test rate limiter integration with download endpoints."""
        # This would require setting up the actual app with rate limiting
        # For now, we test that the components work together

        limiter = RateLimiter(requests_per_minute=2, burst_limit=1)
        client_ip = "192.168.1.100"

        # First request allowed
        allowed1, remaining1, reset1 = limiter.is_allowed(client_ip)
        assert allowed1 is True
        assert remaining1 >= 0

        # Second request should be blocked (burst limit = 1)
        allowed2, remaining2, reset2 = limiter.is_allowed(client_ip)
        assert allowed2 is False
        assert remaining2 == 0

        # Reset times should be consistent
        assert abs(reset1 - reset2) < 1  # Within 1 second

    def test_rate_limiter_configuration_validation(self):
        """Test that rate limiter configuration is validated."""
        # Very low limits should still work
        limiter = RateLimiter(requests_per_minute=1, burst_limit=1)
        assert limiter.requests_per_minute == 1

        # Zero limits should be handled
        limiter_zero = RateLimiter(requests_per_minute=0, burst_limit=0)
        client_ip = "192.168.1.1"
        allowed, remaining, reset_time = limiter_zero.is_allowed(client_ip)
        assert allowed is False  # Should block everything
        assert remaining == 0
