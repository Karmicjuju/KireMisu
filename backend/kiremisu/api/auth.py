"""Authentication API endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from kiremisu.core.auth import UserManager, create_jwt_token, get_current_user

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
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    logger.info(f"Login attempt for username: {request.username}")
    
    # Verify credentials
    user_data = UserManager.verify_user(request.username, request.password)
    if not user_data:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Create JWT token
    access_token = create_jwt_token(user_data)
    
    logger.info(f"Successful login for user: {request.username}")
    
    return LoginResponse(
        access_token=access_token,
        user=user_data
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email"),
        created_at=user["created_at"].isoformat() if user["created_at"] else None,
        is_active=user["is_active"]
    )


@router.post("/logout")
async def logout(user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user (client should discard token)."""
    logger.info(f"User logout: {user['username']}")
    
    # In a stateless JWT setup, logout is mainly handled client-side
    # In a production environment, you might maintain a token blacklist
    return {"message": "Successfully logged out"}


@router.get("/demo-users")
async def get_demo_users():
    """Get list of demo users for development purposes."""
    return {
        "demo_users": [
            {"username": "demo", "password": "demo123", "description": "Demo user account"},
            {"username": "admin", "password": "admin123", "description": "Admin demo account"}
        ],
        "note": "These are demo credentials for development only"
    }