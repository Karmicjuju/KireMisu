"""Secure authentication API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.auth import (
    check_auth_rate_limit,
    cleanup_auth_attempts,
    clear_auth_rate_limits,
    create_jwt_token,
    create_user_db,
    extract_bearer_token,
    logout_user,
    pwd_context,
    update_user_password,
    validate_password_complexity,
    verify_user_db,
)
from kiremisu.core.session_auth import (
    TestAuthSession,
    clear_session_cookie,
    create_csrf_token,
    create_session,
    destroy_session,
    is_test_mode,
    set_session_cookie,
)
from kiremisu.core.unified_auth import (
    get_current_user,
    require_admin,
)
from kiremisu.database.connection import get_db

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
    display_name: str | None = Field(
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
    access_token: str | None = Field(None, description="JWT access token (legacy mode)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=24 * 60 * 60, description="Token expiration in seconds")
    user: dict[str, Any] = Field(..., description="User information")
    auth_method: str = Field(..., description="Authentication method used")
    csrf_token: str | None = Field(None, description="CSRF token for cookie auth")


class UserResponse(BaseModel):
    """User information response."""
    id: str = Field(..., description="User unique identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    display_name: str | None = Field(None, description="Display name")
    is_admin: bool = Field(..., description="Whether user has admin privileges")
    is_active: bool = Field(..., description="Whether user account is active")
    email_verified: bool = Field(..., description="Whether email is verified")
    created_at: str = Field(..., description="Account creation timestamp")
    last_login: str | None = Field(None, description="Last login timestamp")


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
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with environment-based auth method.

    Implements secure login with:
    - Rate limiting per IP
    - Account lockout after failed attempts
    - Secure password verification
    - Environment-based authentication (cookies vs JWT)
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

    # Determine authentication method based on environment
    import os
    auth_method = os.getenv('AUTH_METHOD', 'secure_cookies')

    if is_test_mode():
        # Test mode - simplified authentication
        TestAuthSession.create_test_session(user, response)
        logger.info(f"Test login successful: {user.username}")

        return LoginResponse(
            access_token=None,
            auth_method="test_bypass",
            csrf_token=None,
            user=user_dict
        )

    elif auth_method == 'secure_cookies':
        # Production mode - secure session cookies
        session_id, session_data = create_session(user)
        csrf_token = create_csrf_token(session_id)

        # Set secure HttpOnly cookie
        is_secure = os.getenv('NODE_ENV') == 'production'
        set_session_cookie(response, session_id, secure=is_secure)

        logger.info(f"Cookie-based login successful: {user.username}")

        return LoginResponse(
            access_token=None,
            auth_method="secure_cookies",
            csrf_token=csrf_token,
            user=user_dict
        )

    else:
        # Legacy mode - JWT tokens (for backward compatibility)
        try:
            access_token = create_jwt_token(user)
        except ValueError as e:
            logger.error(f"JWT token creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service temporarily unavailable",
            )

        logger.info(f"JWT login successful: {user.username}")

        return LoginResponse(
            access_token=access_token,
            auth_method="jwt_bearer",
            csrf_token=None,
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
async def get_current_user_info(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user information."""
    user = await get_current_user(request, db)
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
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Logout user using environment-appropriate method."""
    import os
    auth_method = os.getenv('AUTH_METHOD', 'secure_cookies')

    # Get current user first
    try:
        user = await get_current_user(request, db)
        username = user.username if user else 'unknown'
    except Exception:
        username = 'unknown'

    if is_test_mode():
        # Test mode - clear test cookie
        response.delete_cookie("test_session", path="/")
        logger.info(f"Test logout: {username}")

    elif auth_method == 'secure_cookies':
        # Cookie-based auth - destroy session and clear cookies
        from kiremisu.core.session_auth import get_session_from_request
        session_id = get_session_from_request(request)
        if session_id:
            destroy_session(session_id)
            clear_session_cookie(response)
        logger.info(f"Cookie logout: {username}")

    else:
        # JWT-based auth - blacklist token
        authorization = request.headers.get("authorization")
        if authorization:
            try:
                token = extract_bearer_token(authorization)
                await logout_user(token)
                logger.info(f"JWT logout: {username}")
            except Exception as e:
                logger.warning(f"Error during JWT logout for {username}: {e}")

    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    change_request: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    user = await get_current_user(request, db)

    # Verify current password
    if not pwd_context.verify(change_request.current_password, user.password_hash):
        logger.warning(f"Invalid current password for password change: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password complexity
    password_errors = validate_password_complexity(change_request.new_password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password validation failed: " + "; ".join(password_errors),
        )

    # Ensure new password is different from current
    if pwd_context.verify(change_request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    try:
        # Update password
        await update_user_password(db, user, change_request.new_password)
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
async def cleanup_auth_data(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Clean up old authentication data (admin only)."""
    try:
        user = await require_admin(request, db)
        cleanup_auth_attempts()
        logger.info(f"Authentication data cleanup performed by: {user.username}")
        return {"message": "Authentication data cleaned up successfully"}
    except Exception as e:
        logger.error(f"Auth cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cleanup service temporarily unavailable",
        )


@router.post("/clear-rate-limits")
async def clear_rate_limits(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client_ip: str | None = None
):
    """Clear authentication rate limits (admin only, for development/testing)."""
    try:
        user = await require_admin(request, db)
        clear_auth_rate_limits(client_ip)
        if client_ip:
            message = f"Rate limits cleared for IP: {client_ip}"
        else:
            message = "All rate limits cleared"

        logger.info(f"Rate limits cleared by admin: {user.username} - {message}")
        return {"message": message}
    except Exception as e:
        logger.error(f"Rate limit clear error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rate limit service temporarily unavailable",
        )
