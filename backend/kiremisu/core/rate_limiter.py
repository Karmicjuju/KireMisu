"""Rate limiting middleware for the KireMisu API."""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with per-IP tracking.

    Implements sliding window rate limiting with configurable limits.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        cleanup_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute per IP
            requests_per_hour: Max requests per hour per IP
            burst_limit: Max burst requests (short term)
            cleanup_interval: How often to clean up old entries (seconds)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.cleanup_interval = cleanup_interval

        # Track requests per IP: {ip: deque of timestamps}
        self.request_times: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()

    def _cleanup_old_entries(self) -> None:
        """Remove old entries to prevent memory leaks."""
        current_time = time.time()

        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        cutoff_time = current_time - 3600  # Keep 1 hour of data

        for ip, timestamps in list(self.request_times.items()):
            # Remove timestamps older than 1 hour
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()

            # Remove empty entries
            if not timestamps:
                del self.request_times[ip]

        self.last_cleanup = current_time
        logger.debug(f"Rate limiter cleanup completed. Tracking {len(self.request_times)} IPs")

    def is_allowed(self, client_ip: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is allowed for given IP.

        Args:
            client_ip: Client IP address

        Returns:
            Tuple of (is_allowed, error_message)
        """
        current_time = time.time()
        self._cleanup_old_entries()

        timestamps = self.request_times[client_ip]

        # Remove timestamps older than 1 hour
        while timestamps and timestamps[0] < current_time - 3600:
            timestamps.popleft()

        # Check hourly limit
        if len(timestamps) >= self.requests_per_hour:
            return False, f"Hourly rate limit exceeded ({self.requests_per_hour} requests/hour)"

        # Remove timestamps older than 1 minute
        minute_timestamps = deque()
        for ts in reversed(timestamps):
            if ts >= current_time - 60:
                minute_timestamps.appendleft(ts)
            else:
                break

        # Check per-minute limit
        if len(minute_timestamps) >= self.requests_per_minute:
            return False, f"Rate limit exceeded ({self.requests_per_minute} requests/minute)"

        # Check burst limit (last 10 seconds)
        burst_timestamps = deque()
        for ts in reversed(timestamps):
            if ts >= current_time - 10:
                burst_timestamps.appendleft(ts)
            else:
                break

        if len(burst_timestamps) >= self.burst_limit:
            return False, f"Burst limit exceeded ({self.burst_limit} requests per 10 seconds)"

        # Request is allowed, record it
        timestamps.append(current_time)
        return True, None

    def get_rate_limit_headers(self, client_ip: str) -> Dict[str, str]:
        """
        Get rate limit headers for response.

        Args:
            client_ip: Client IP address

        Returns:
            Dictionary of headers to include in response
        """
        current_time = time.time()
        timestamps = self.request_times.get(client_ip, deque())

        # Count requests in last minute
        minute_count = sum(1 for ts in timestamps if ts >= current_time - 60)

        # Count requests in last hour
        hour_count = len(timestamps)

        headers = {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(max(0, self.requests_per_minute - minute_count)),
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Hour": str(max(0, self.requests_per_hour - hour_count)),
        }

        # Add reset time (next minute boundary)
        next_minute = datetime.fromtimestamp(current_time + 60).replace(second=0, microsecond=0)
        headers["X-RateLimit-Reset"] = str(int(next_minute.timestamp()))

        return headers


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check common proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"

    def _should_rate_limit(self, request: Request) -> bool:
        """Determine if request should be rate limited."""
        # Skip rate limiting for health checks and static assets
        path = request.url.path

        exempt_paths = [
            "/health",
            "/",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        ]

        # Skip rate limiting for certain paths
        if path in exempt_paths:
            return False

        # Skip rate limiting for static assets
        if path.startswith("/static/") or path.endswith((".css", ".js", ".ico", ".png", ".jpg")):
            return False

        return True

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""

        # Check if this request should be rate limited
        if not self._should_rate_limit(request):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Check rate limit
        is_allowed, error_message = self.rate_limiter.is_allowed(client_ip)

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {error_message}")

            # Return rate limit error
            headers = self.rate_limiter.get_rate_limit_headers(client_ip)

            return Response(
                content=f'{{"error": true, "message": "{error_message}"}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
                media_type="application/json",
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        headers = self.rate_limiter.get_rate_limit_headers(client_ip)
        for key, value in headers.items():
            response.headers[key] = value

        return response
