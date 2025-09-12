"""Authentication routes using FastAPI-Users."""
import secrets
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.users import auth_backend, fastapi_users
from app.schemas.user import UserCreate, UserRead

router = APIRouter()

# CSRF Token endpoint
@router.get("/auth/csrf-token")
async def get_csrf_token(response: Response) -> dict:
    """Generate and return a CSRF token."""
    # Generate a secure random token
    csrf_token = secrets.token_hex(32)
    
    # Set the token as a secure cookie
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=3600,  # 1 hour
        httponly=False,  # Allow JavaScript access for header
        secure=False,  # Set to True in production with HTTPS
        samesite="strict",
        path="/"
    )
    
    return {"csrf_token": csrf_token}

# Include auth routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/auth", 
    tags=["auth"]
)

# Include registration routes (optional - can be disabled for single user)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"]
)

# Include user management routes
router.include_router(
    fastapi_users.get_users_router(UserRead, UserCreate),
    prefix="/users",
    tags=["users"]
)