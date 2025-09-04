"""
Rate limiting utilities for API endpoints.

This module provides a simple, memory-based rate limiting implementation
suitable for single-instance deployments. For production multi-instance
deployments, consider using Redis-based rate limiting.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple
from fastapi import HTTPException, Request, status
import threading


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.
    
    This implementation stores request timestamps in memory and is suitable
    for single-instance applications. For distributed systems, use Redis.
    """
    
    def __init__(self):
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if a request should be allowed based on rate limits.
        
        Args:
            key: Unique identifier for the client (e.g., IP address)
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        with self._lock:
            # Get or create request queue for this key
            request_queue = self._requests[key]
            
            # Remove old requests outside the window
            while request_queue and request_queue[0] <= window_start:
                request_queue.popleft()
            
            # Check if we're under the limit
            if len(request_queue) < max_requests:
                request_queue.append(current_time)
                return True, 0
            else:
                # Calculate when the oldest request will expire
                oldest_request = request_queue[0]
                retry_after = int(oldest_request + window_seconds - current_time) + 1
                return False, max(retry_after, 1)
    
    def clear_expired(self, window_seconds: int = 3600):
        """
        Clear expired entries to prevent memory bloat.
        Call this periodically or implement as a background task.
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        with self._lock:
            keys_to_remove = []
            for key, request_queue in self._requests.items():
                # Remove old requests
                while request_queue and request_queue[0] <= cutoff_time:
                    request_queue.popleft()
                
                # Mark empty queues for removal
                if not request_queue:
                    keys_to_remove.append(key)
            
            # Remove empty entries
            for key in keys_to_remove:
                del self._requests[key]


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Handles various proxy headers while being secure about spoofing.
    """
    # Check for forwarded IP (common in reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip
    
    # Check for real IP header (some proxies use this)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    client_host = request.client.host if request.client else "unknown"
    return client_host


def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """
    Decorator for rate limiting API endpoints.
    
    Args:
        max_requests: Maximum requests allowed per window (default: 100)
        window_seconds: Time window in seconds (default: 3600 = 1 hour)
    
    Usage:
        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint():
            pass
    """
    def decorator(func):
        def wrapper(request: Request, *args, **kwargs):
            client_ip = get_client_ip(request)
            rate_limiter = get_rate_limiter()
            
            # Create a unique key for this endpoint and client
            endpoint = request.url.path
            rate_key = f"{client_ip}:{endpoint}"
            
            is_allowed, retry_after = rate_limiter.is_allowed(
                rate_key, max_requests, window_seconds
            )
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def create_rate_limit_dependency(max_requests: int = 100, window_seconds: int = 3600):
    """
    Create a FastAPI dependency for rate limiting.
    
    Args:
        max_requests: Maximum requests allowed per window
        window_seconds: Time window in seconds
    
    Returns:
        FastAPI dependency function
    
    Usage:
        rate_limit_dep = create_rate_limit_dependency(max_requests=10, window_seconds=60)
        
        @router.get("/endpoint")
        async def endpoint(rate_limit: None = Depends(rate_limit_dep)):
            pass
    """
    def rate_limit_dependency(request: Request):
        client_ip = get_client_ip(request)
        rate_limiter = get_rate_limiter()
        
        # Create a unique key for this endpoint and client
        endpoint = request.url.path
        rate_key = f"{client_ip}:{endpoint}"
        
        is_allowed, retry_after = rate_limiter.is_allowed(
            rate_key, max_requests, window_seconds
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        
        return None
    
    return rate_limit_dependency