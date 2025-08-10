"""Basic authentication system for KireMisu API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from kiremisu.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Simple bearer token authentication
security = HTTPBearer(auto_error=False)


async def get_api_key(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate API key from Authorization header.
    
    For now, this is a simple implementation that validates against a configured API key.
    In a full implementation, this would validate JWT tokens or session tokens.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # For now, validate against a simple API key
    # In production, this should validate JWT tokens or use a proper auth service
    expected_key = settings.secret_key  # Using existing secret_key setting
    if not expected_key:
        logger.error("No authentication key configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured",
        )
    
    if token != expected_key:
        logger.warning(f"Invalid API key used from client")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


async def get_optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Optional authentication - returns None if not authenticated."""
    if not credentials:
        return None
    
    try:
        # Validate the token
        expected_key = settings.secret_key
        if credentials.credentials != expected_key:
            return None
        return credentials.credentials
    except Exception:
        return None


# Rate limiting storage (in-memory for simplicity)
_rate_limit_store = {}


def check_rate_limit(client_ip: str, endpoint: str, max_requests: int = 10, window_minutes: int = 5) -> bool:
    """Simple rate limiting implementation.
    
    Args:
        client_ip: Client IP address
        endpoint: API endpoint being accessed
        max_requests: Maximum requests allowed in window
        window_minutes: Time window in minutes
        
    Returns:
        True if request should be allowed, False if rate limited
    """
    now = datetime.utcnow()
    key = f"{client_ip}:{endpoint}"
    
    # Clean old entries
    if key in _rate_limit_store:
        _rate_limit_store[key] = [
            timestamp for timestamp in _rate_limit_store[key]
            if (now - timestamp).total_seconds() < (window_minutes * 60)
        ]
    else:
        _rate_limit_store[key] = []
    
    # Check if limit exceeded
    if len(_rate_limit_store[key]) >= max_requests:
        return False
    
    # Record this request
    _rate_limit_store[key].append(now)
    return True