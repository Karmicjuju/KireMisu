"""Unified authentication dependency for both JWT and session-based auth."""

import logging
import os
from typing import Optional

from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.models import User
from kiremisu.core.auth import get_current_user as get_jwt_user
from kiremisu.core.session_auth import (
    get_current_user_from_session,
    TestAuthSession,
    is_test_mode
)

logger = logging.getLogger(__name__)


async def get_current_user_unified(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user using unified authentication.
    
    Supports multiple authentication methods based on environment:
    - Test mode: Simplified test authentication
    - Production: Secure session cookies
    - Legacy: JWT bearer tokens
    
    Args:
        request: FastAPI Request object
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_method = os.getenv('AUTH_METHOD', 'secure_cookies')
    
    # Test mode authentication
    if is_test_mode():
        user = await TestAuthSession.get_test_user(request, db)
        if user:
            return user
        # Fall through to other methods if test auth fails
    
    # Session-based authentication (production)
    if auth_method == 'secure_cookies':
        user = await get_current_user_from_session(request, db)
        if user:
            return user
    
    # JWT-based authentication (legacy/fallback)
    try:
        # Use the original JWT auth dependency
        from kiremisu.core.auth import security
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
        if credentials:
            # This will call the original get_current_user function
            user = await get_jwt_user(credentials, db)
            if user:
                return user
    except HTTPException:
        # JWT auth failed, continue to raise generic error
        pass
    except Exception as e:
        logger.warning(f"JWT authentication error: {e}")
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, or None if not.
    
    Same as get_current_user_unified but doesn't raise exceptions.
    Useful for endpoints that work with or without authentication.
    
    Args:
        request: FastAPI Request object
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    try:
        return await get_current_user_unified(request, db)
    except HTTPException:
        return None
    except Exception as e:
        logger.warning(f"Optional authentication error: {e}")
        return None


async def require_admin_unified(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Require admin privileges using unified authentication.
    
    Args:
        request: FastAPI Request object
        db: Database session
        
    Returns:
        User object if admin
        
    Raises:
        HTTPException: If user is not admin or not authenticated
    """
    user = await get_current_user_unified(request, db)
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user


async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated and active user.
    
    Args:
        request: FastAPI Request object
        db: Database session
        
    Returns:
        Active User object
        
    Raises:
        HTTPException: If user is inactive or not authenticated
    """
    user = await get_current_user_unified(request, db)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


# Convenience aliases for different use cases
get_current_user = get_current_user_unified
require_admin = require_admin_unified