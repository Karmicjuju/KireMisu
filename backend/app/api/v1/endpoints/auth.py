"""Authentication routes using FastAPI-Users."""
from fastapi import APIRouter

from app.users import auth_backend, fastapi_users
from app.schemas.user import UserCreate, UserRead

router = APIRouter()

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