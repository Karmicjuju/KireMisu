"""Secure authentication API endpoints."""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field, field_validator, validator
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.core.auth import (
    create_jwt_token, 
    get_current_user,
    verify_user_db,
    create_user_db,
    get_user_by_id_db,
    initialize_admin_user,
    check_auth_rate_limit,
    validate_password_complexity,
    extract_bearer_token,
    logout_user,
    cleanup_auth_attempts,
    require_admin,
    update_user_password,
    pwd_context,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""
    username_or_email: str = Field(
        ..., 
        min_length=3, 
        max_length=255, 
        description="Username or email address"
    )
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="Password"
    )
    
    @field_validator("username_or_email")
    @classmethod
    def validate_username_or_email(cls, v):
        """Validate username or email format."""
        v = v.strip()
        if not v:
            raise ValueError("Username or email cannot be empty")
        return v.lower()


class UserRegistrationRequest(BaseModel):
    """User registration request model."""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, underscore, hyphen only)"
    )
    email: str = Field(..., description="Email address")
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="Password (must meet complexity requirements)"
    )
    confirm_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="Password confirmation"
    )
    display_name: Optional[str] = Field(
        None, 
        max_length=100, 
        description="Display name (optional)"
    )
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        v = v.strip().lower()
        if not v:
            raise ValueError("Username cannot be empty")
        return v
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("confirm_password")
    @classmethod  
    def passwords_match(cls, v, info):
        """Validate password confirmation matches."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=24 * 60 * 60, description="Token expiration in seconds")
    user: Dict[str, Any] = Field(..., description="User information")


class UserResponse(BaseModel):
    """User information response."""
    id: str = Field(..., description="User unique identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    display_name: Optional[str] = Field(None, description="Display name")
    is_admin: bool = Field(..., description="Whether user has admin privileges")
    is_active: bool = Field(..., description="Whether user account is active")
    email_verified: bool = Field(..., description="Whether email is verified")
    created_at: str = Field(..., description="Account creation timestamp")
    last_login: Optional[str] = Field(None, description="Last login timestamp")


class UserRegistrationResponse(BaseModel):
    """User registration response."""
    success: bool = Field(default=True, description="Registration success status")
    message: str = Field(..., description="Success message")
    user: UserResponse = Field(..., description="Created user information")


class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    current_password: str = Field(..., min_length=8, max_length=128, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="New password confirmation"
    )
    
    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v, info):
        """Validate new password confirmation matches."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class PasswordValidationRequest(BaseModel):
    """Password validation request."""
    password: str = Field(..., min_length=1, max_length=128, description="Password to validate")

class PasswordValidationResponse(BaseModel):
    """Password validation response."""
    is_valid: bool = Field(..., description="Whether password meets complexity requirements")
    errors: list[str] = Field(default_factory=list, description="Validation error messages")


# Utility Functions
def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded IP headers (common in reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


# API Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest, 
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token.
    
    Implements secure login with:
    - Rate limiting per IP
    - Account lockout after failed attempts  
    - Secure password verification
    - JWT token generation
    """
    client_ip = _get_client_ip(http_request)
    
    logger.info(f"Login attempt for: {request.username_or_email} from IP: {client_ip}")
    
    # Verify user credentials with rate limiting
    user = await verify_user_db(db, request.username_or_email, request.password, client_ip)
    
    if not user:
        # Generic error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Generate secure JWT token
    try:
        access_token = create_jwt_token(user)
    except ValueError as e:
        logger.error(f"JWT token creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable",
        )
    
    # Return user information (excluding sensitive data)
    user_dict = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
    
    logger.info(f"Successful login: {user.username}")
    
    return LoginResponse(
        access_token=access_token,
        user=user_dict
    )


@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account.
    
    Creates a new user with:
    - Password complexity validation
    - Rate limiting per IP
    - Unique username and email validation
    """
    client_ip = _get_client_ip(http_request)
    
    # Check rate limiting for registration attempts
    if not check_auth_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )
    
    logger.info(f"Registration attempt for username: {request.username} from IP: {client_ip}")
    
    try:
        # Create user in database (this validates password complexity)
        user = await create_user_db(
            db=db,
            username=request.username,
            email=str(request.email),
            password=request.password,
            is_admin=False  # New users are never admin by default
        )
        
        # Set display name if provided
        if request.display_name:
            user.display_name = request.display_name.strip()
            await db.commit()
            await db.refresh(user)
        
        # Prepare response
        user_response = UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_admin=user.is_admin,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat(),
            last_login=None
        )
        
        logger.info(f"User registered successfully: {user.username}")
        
        return UserRegistrationResponse(
            message="User account created successfully",
            user=user_response
        )
        
    except ValueError as e:
        logger.warning(f"Registration failed for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Registration error for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service temporarily unavailable",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@router.post("/logout")
async def logout(request: Request, user = Depends(get_current_user)):
    """Logout user by blacklisting their JWT token."""
    # Extract token for blacklisting
    authorization = request.headers.get("authorization")
    if authorization:
        try:
            token = extract_bearer_token(authorization)
            await logout_user(token)
            logger.info(f"User logged out: {user.username}")
        except Exception as e:
            logger.warning(f"Error during logout for {user.username}: {e}")
    
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not pwd_context.verify(request.current_password, user.password_hash):
        logger.warning(f"Invalid current password for password change: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Validate new password complexity
    password_errors = validate_password_complexity(request.new_password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password validation failed: " + "; ".join(password_errors),
        )
    
    # Ensure new password is different from current
    if pwd_context.verify(request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )
    
    try:
        # Update password
        await update_user_password(db, user, request.new_password)
        logger.info(f"Password changed for user: {user.username}")
        
        return {"message": "Password changed successfully"}
        
    except Exception as e:
        logger.error(f"Password change error for {user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change service temporarily unavailable",
        )


@router.post("/validate-password", response_model=PasswordValidationResponse)
async def validate_password(request: PasswordValidationRequest):
    """Validate password complexity requirements."""
    errors = validate_password_complexity(request.password)
    return PasswordValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors
    )


@router.post("/cleanup")
async def cleanup_auth_data(user = Depends(require_admin)):
    """Clean up old authentication data (admin only)."""
    try:
        cleanup_auth_attempts()
        logger.info(f"Authentication data cleanup performed by: {user.username}")
        return {"message": "Authentication data cleaned up successfully"}
    except Exception as e:
        logger.error(f"Auth cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cleanup service temporarily unavailable",
        )