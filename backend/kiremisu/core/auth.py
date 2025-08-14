"""Authentication system for KireMisu API endpoints."""

import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.config import get_settings
from kiremisu.database.connection import get_db
from kiremisu.database.models import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Bearer token authentication
security = HTTPBearer(auto_error=False)

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Password hashing - Use bcrypt with cost factor 12 for security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Token blacklist for secure logout
_token_blacklist: set = set()

# Password validation patterns
PASSWORD_MIN_LENGTH = 8
PASSWORD_PATTERNS = {
    "uppercase": re.compile(r"[A-Z]"),
    "lowercase": re.compile(r"[a-z]"),
    "digit": re.compile(r"[0-9]"),
    "special": re.compile(r"[!@#$%^&*(),.?\":{}|<>]"),
}

# Rate limiting for authentication
_auth_attempts: dict[str, list[datetime]] = {}


def validate_password_complexity(password: str) -> list[str]:
    """Validate password complexity requirements.

    Returns:
        List of validation error messages. Empty list if password is valid.
    """
    errors = []

    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")

    if not PASSWORD_PATTERNS["uppercase"].search(password):
        errors.append("Password must contain at least one uppercase letter")

    if not PASSWORD_PATTERNS["lowercase"].search(password):
        errors.append("Password must contain at least one lowercase letter")

    if not PASSWORD_PATTERNS["digit"].search(password):
        errors.append("Password must contain at least one digit")

    if not PASSWORD_PATTERNS["special"].search(password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")

    # Check for common weak patterns
    lower_password = password.lower()
    weak_patterns = ["password", "123456", "qwerty", "admin", "letmein", "welcome"]
    for pattern in weak_patterns:
        if pattern in lower_password:
            errors.append("Password contains common weak patterns")
            break

    return errors

def clear_auth_rate_limits(client_ip: str | None = None) -> None:
    """Clear authentication rate limit data for testing/development.

    Args:
        client_ip: Specific IP to clear, or None to clear all
    """
    if client_ip:
        _auth_attempts.pop(client_ip, None)
        logger.info(f"Cleared auth rate limits for IP: {client_ip}")
    else:
        _auth_attempts.clear()
        logger.info("Cleared all auth rate limits")

def check_auth_rate_limit(client_ip: str) -> bool:
    """Check if authentication attempts are within rate limits.

    Args:
        client_ip: Client IP address

    Returns:
        True if within limits, False if rate limited
    """
    now = datetime.utcnow()
    cutoff_time = now - timedelta(minutes=settings.auth_rate_limit_window_minutes)

    # Clean old attempts
    if client_ip in _auth_attempts:
        _auth_attempts[client_ip] = [
            attempt_time for attempt_time in _auth_attempts[client_ip]
            if attempt_time > cutoff_time
        ]
    else:
        _auth_attempts[client_ip] = []

    # Check if limit exceeded
    if len(_auth_attempts[client_ip]) >= settings.auth_rate_limit_attempts:
        logger.warning(f"Authentication rate limit exceeded for IP: {client_ip}")
        return False

    # Record this attempt
    _auth_attempts[client_ip].append(now)
    return True

def blacklist_token(token: str) -> None:
    """Add token to blacklist for secure logout."""
    _token_blacklist.add(token)
    # In production, this should be stored in Redis or database
    # and cleaned up periodically

def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    return token in _token_blacklist


# Database-backed user management functions
async def create_user_db(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    is_admin: bool = False
) -> User:
    """Create a new user in the database.

    Args:
        db: Database session
        username: Username (must be unique)
        email: Email address (must be unique and valid)
        password: Password (must meet complexity requirements)
        is_admin: Whether user should have admin privileges

    Returns:
        Created user

    Raises:
        ValueError: If validation fails or user already exists
    """
    # Validate inputs
    if not username or len(username.strip()) < 3:
        raise ValueError("Username must be at least 3 characters long")

    if not email or "@" not in email:
        raise ValueError("Valid email address is required")

    # Validate password complexity
    password_errors = validate_password_complexity(password)
    if password_errors:
        raise ValueError("Password validation failed: " + "; ".join(password_errors))

    # Normalize inputs
    username = username.strip().lower()
    email = email.strip().lower()

    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == email)
        )
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        if existing_user.username == username:
            raise ValueError("Username is already taken")
        else:
            raise ValueError("Email address is already registered")

    # Create new user with secure password hash
    user = User(
        username=username,
        email=email,
        password_hash=pwd_context.hash(password),
        is_admin=is_admin,
        is_active=True,
        email_verified=False,
        failed_login_attempts=0,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Created user: {username} (admin={is_admin})")
    return user


async def verify_user_db(
    db: AsyncSession,
    username_or_email: str,
    password: str,
    client_ip: str | None = None
) -> User | None:
    """Verify user credentials against database.

    Args:
        db: Database session
        username_or_email: Username or email address
        password: Password to verify
        client_ip: Client IP for rate limiting (optional)

    Returns:
        User if authentication successful, None otherwise
    """
    # Check rate limiting if IP provided
    if client_ip and not check_auth_rate_limit(client_ip):
        logger.warning(f"Authentication rate limit exceeded for IP: {client_ip}")
        return None

    # Normalize input
    username_or_email = username_or_email.strip().lower()

    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        # Log attempt but don't specify what was wrong
        logger.warning(f"Authentication attempt for non-existent user: {username_or_email}")
        return None

    if not user.is_active:
        logger.warning(f"Authentication attempt for inactive user: {user.username}")
        return None

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining_minutes = (user.locked_until - datetime.utcnow()).seconds // 60
        logger.warning(f"Authentication attempt for locked account: {user.username} ({remaining_minutes}m remaining)")
        return None

    # Verify password
    if not pwd_context.verify(password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()

        # Lock account after 5 failed attempts for 30 minutes
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            logger.warning(f"Account locked due to {user.failed_login_attempts} failed attempts: {user.username}")
        else:
            logger.warning(f"Failed login attempt {user.failed_login_attempts}/5 for user: {user.username}")

        await db.commit()
        return None

    # Successful authentication - reset security counters
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    user.locked_until = None
    await db.commit()

    logger.info(f"Successful authentication: {user.username}")
    return user


async def get_user_by_id_db(db: AsyncSession, user_id: str) -> User | None:
    """Get user by ID from database."""
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        return None

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    return result.scalar_one_or_none()


async def update_user_password(
    db: AsyncSession,
    user: User,
    new_password: str
) -> None:
    """Update user password with secure hashing.

    Args:
        db: Database session
        user: User to update
        new_password: New password (already validated)
    """
    user.password_hash = pwd_context.hash(new_password)
    user.updated_at = datetime.utcnow()

    # Reset any security flags
    user.failed_login_attempts = 0
    user.locked_until = None

    await db.commit()
    logger.info(f"Password updated for user: {user.username}")


async def initialize_admin_user(db: AsyncSession) -> None:
    """Initialize admin user from environment variables.

    Only creates admin user if none exist and password meets complexity requirements.
    """
    import os

    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", f"{admin_username}@kiremisu.local")

    if not admin_password:
        logger.warning("No DEFAULT_ADMIN_PASSWORD set - admin user creation skipped")
        logger.warning("Set DEFAULT_ADMIN_PASSWORD environment variable to create initial admin user")
        return

    # Validate admin password complexity
    password_errors = validate_password_complexity(admin_password)
    if password_errors:
        logger.error("Admin password does not meet complexity requirements:")
        for error in password_errors:
            logger.error(f"  - {error}")
        logger.error("Please set a stronger DEFAULT_ADMIN_PASSWORD")
        return

    try:
        # Check if any admin users exist
        result = await db.execute(select(User).where(User.is_admin))
        if result.scalar_one_or_none():
            logger.debug("Admin user already exists - skipping creation")
            return

        # Check if username/email already exist
        result = await db.execute(
            select(User).where(
                (User.username == admin_username) | (User.email == admin_email)
            )
        )
        if result.scalar_one_or_none():
            logger.error(f"User with username '{admin_username}' or email '{admin_email}' already exists")
            return

        # Create admin user
        await create_user_db(
            db=db,
            username=admin_username,
            email=admin_email,
            password=admin_password,
            is_admin=True
        )
        logger.info(f"Created initial admin user: {admin_username}")
        logger.info("IMPORTANT: Change the admin password after first login")

    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")

def create_jwt_token(user: User) -> str:
    """Create a JWT token for the user.

    Args:
        user: User model instance

    Returns:
        JWT token string
    """
    now = datetime.utcnow()

    # Create secure payload with only necessary information
    payload = {
        "user_id": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": now,
        "jti": secrets.token_hex(16),  # JWT ID for token blacklisting
    }

    # Ensure we have a secure secret key
    if not settings.secret_key or len(settings.secret_key) < 32:
        raise ValueError("JWT secret key must be at least 32 characters long")

    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict[str, Any]:
    """Verify a JWT token and return the payload.

    Args:
        token: JWT token string

    Returns:
        Token payload dictionary

    Raises:
        HTTPException: If token is invalid, expired, or blacklisted
    """
    try:
        # Check if token is blacklisted first
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify and decode token
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])

        # Validate required fields
        required_fields = ["user_id", "username", "exp", "iat", "jti"]
        for field in required_fields:
            if field not in payload:
                raise jwt.InvalidTokenError(f"Missing required field: {field}")

        return payload
    except jwt.ExpiredSignatureError:
        logger.info("Expired JWT token attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def extract_bearer_token(authorization: str) -> str:
    """Extract token from Bearer authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        JWT token string

    Raises:
        HTTPException: If header format is invalid
    """
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
        return token.strip()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from database.

    Args:
        authorization: Authorization header value
        db: Database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract and verify token
    token = extract_bearer_token(authorization)
    payload = verify_jwt_token(token)

    # Get user from database
    user = await get_user_by_id_db(db, payload["user_id"])
    if not user:
        logger.warning(f"Token contains invalid user_id: {payload['user_id']}")
        # Blacklist the token since user doesn't exist
        blacklist_token(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.username}")
        blacklist_token(token)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining_time = user.locked_until - datetime.utcnow()
        logger.warning(f"Locked user attempted access: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked for {remaining_time.seconds // 60} more minutes",
        )

    return user


async def get_current_user_optional(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """Get the current authenticated user if available, otherwise return None."""
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require the current user to be an admin.

    Args:
        current_user: Currently authenticated user

    Returns:
        User if they have admin privileges

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user


async def logout_user(token: str) -> None:
    """Logout user by blacklisting their token.

    Args:
        token: JWT token to blacklist
    """
    blacklist_token(token)
    logger.info("User logged out successfully")


# Clean up old auth attempts periodically
def cleanup_auth_attempts() -> None:
    """Clean up old authentication attempts to prevent memory leaks."""
    cutoff_time = datetime.utcnow() - timedelta(minutes=AUTH_WINDOW_MINUTES * 2)

    for client_ip in list(_auth_attempts.keys()):
        _auth_attempts[client_ip] = [
            attempt_time for attempt_time in _auth_attempts[client_ip]
            if attempt_time > cutoff_time
        ]

        # Remove empty entries
        if not _auth_attempts[client_ip]:
            del _auth_attempts[client_ip]

def generate_secure_secret_key() -> str:
    """Generate a secure secret key for JWT tokens.

    Returns:
        Base64 encoded secure random string
    """
    import base64
    return base64.b64encode(secrets.token_bytes(64)).decode('utf-8')
