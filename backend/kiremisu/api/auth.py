"""Authentication API endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import time

from kiremisu.database.connection import get_db
from kiremisu.core.auth import (
    UserManager, 
    create_jwt_token, 
    get_current_user,
    verify_user_db,
    create_user_db,
    get_user_by_id_db,
    initialize_admin_user,
    check_rate_limit,
)
from kiremisu.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=255)


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 24 * 60 * 60  # 24 hours in seconds
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """User information response."""
    id: str
    username: str
    email: str = None
    created_at: str
    is_active: bool


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token."""
    logger.info(f"Login attempt for username: {request.username}")
    
    # Try database first, then fallback to in-memory for backwards compatibility
    user = await verify_user_db(db, request.username, request.password)
    
    if not user:
        # Fallback to in-memory user manager
        user_data = UserManager.verify_user(request.username, request.password)
        if not user_data:
            logger.warning(f"Failed login attempt for username: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        # Create JWT token for in-memory user
        access_token = create_jwt_token(user_data)
        
        logger.info(f"Successful login for in-memory user: {request.username}")
        
        return LoginResponse(
            access_token=access_token,
            user=user_data
        )
    
    # Database user login
    access_token = create_jwt_token(user)
    
    logger.info(f"Successful login for database user: {request.username}")
    
    user_dict = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
        "is_active": user.is_active,
        "is_admin": user.is_admin
    }
    
    return LoginResponse(
        access_token=access_token,
        user=user_dict
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user = Depends(get_current_user)):
    """Get current user information."""
    # Handle both User model and dict (for backwards compatibility)
    if hasattr(user, 'id'):
        # User model
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else None,
            is_active=user.is_active
        )
    else:
        # Dict (legacy)
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user.get("email"),
            created_at=user["created_at"].isoformat() if user["created_at"] else None,
            is_active=user["is_active"]
        )


@router.post("/logout")
async def logout(user = Depends(get_current_user)):
    """Logout user (client should discard token)."""
    username = user.username if hasattr(user, 'username') else user.get('username')
    logger.info(f"User logout: {username}")
    
    # In a stateless JWT setup, logout is mainly handled client-side
    # In a production environment, you might maintain a token blacklist
    return {"message": "Successfully logged out"}


# Demo users endpoint removed for security - no test credentials should be exposed


# Admin user setup endpoint removed - handled automatically at startup