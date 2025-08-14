"""Secure session-based authentication with HttpOnly cookies."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.config import get_settings
from kiremisu.database.models import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Session settings
SESSION_COOKIE_NAME = "kiremisu_session"
SESSION_EXPIRATION_HOURS = 24
CSRF_TOKEN_NAME = "kiremisu_csrf"

# Secure session store - in production this should be Redis
_session_store: dict[str, dict[str, Any]] = {}

# CSRF token store
_csrf_tokens: dict[str, str] = {}


class SessionData:
    """Session data structure."""

    def __init__(self, user_id: str, username: str, created_at: datetime, expires_at: datetime):
        self.user_id = user_id
        self.username = username
        self.created_at = created_at
        self.expires_at = expires_at
        self.last_activity = datetime.utcnow()


def generate_session_id() -> str:
    """Generate a cryptographically secure session ID."""
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def create_session(user: User) -> tuple[str, SessionData]:
    """Create a new session for the user.

    Args:
        user: User object

    Returns:
        Tuple of (session_id, session_data)
    """
    session_id = generate_session_id()
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=SESSION_EXPIRATION_HOURS)

    session_data = SessionData(
        user_id=str(user.id),
        username=user.username,
        created_at=now,
        expires_at=expires_at
    )

    _session_store[session_id] = {
        'user_id': session_data.user_id,
        'username': session_data.username,
        'created_at': session_data.created_at,
        'expires_at': session_data.expires_at,
        'last_activity': session_data.last_activity
    }

    logger.info(f"Created session for user: {user.username}")
    return session_id, session_data


def get_session(session_id: str) -> SessionData | None:
    """Get session data by session ID.

    Args:
        session_id: Session identifier

    Returns:
        SessionData if valid, None if expired or not found
    """
    if session_id not in _session_store:
        return None

    session_dict = _session_store[session_id]
    now = datetime.utcnow()

    # Check if session is expired
    if session_dict['expires_at'] < now:
        del _session_store[session_id]
        return None

    # Update last activity
    session_dict['last_activity'] = now

    return SessionData(
        user_id=session_dict['user_id'],
        username=session_dict['username'],
        created_at=session_dict['created_at'],
        expires_at=session_dict['expires_at']
    )


def destroy_session(session_id: str) -> bool:
    """Destroy a session.

    Args:
        session_id: Session identifier

    Returns:
        True if session was destroyed, False if not found
    """
    if session_id in _session_store:
        username = _session_store[session_id].get('username', 'unknown')
        del _session_store[session_id]
        logger.info(f"Destroyed session for user: {username}")
        return True
    return False


def cleanup_expired_sessions() -> int:
    """Clean up expired sessions.

    Returns:
        Number of sessions cleaned up
    """
    now = datetime.utcnow()
    expired_sessions = [
        session_id for session_id, session_dict in _session_store.items()
        if session_dict['expires_at'] < now
    ]

    for session_id in expired_sessions:
        del _session_store[session_id]

    if expired_sessions:
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    return len(expired_sessions)


def set_session_cookie(response: Response, session_id: str, secure: bool = True) -> None:
    """Set session cookie on response.

    Args:
        response: FastAPI Response object
        session_id: Session identifier
        secure: Whether to set secure flag (HTTPS only)
    """
    max_age = SESSION_EXPIRATION_HOURS * 3600  # Convert to seconds

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=max_age,
        httponly=True,  # Prevent XSS
        secure=secure,  # HTTPS only in production
        samesite="lax",  # CSRF protection
        path="/"
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response.

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )


def get_session_from_request(request: Request) -> str | None:
    """Extract session ID from request cookies.

    Args:
        request: FastAPI Request object

    Returns:
        Session ID if found, None otherwise
    """
    return request.cookies.get(SESSION_COOKIE_NAME)


async def get_current_user_from_session(
    request: Request,
    db: AsyncSession
) -> User | None:
    """Get current user from session cookie.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    session_id = get_session_from_request(request)
    if not session_id:
        return None

    session_data = get_session(session_id)
    if not session_data:
        return None

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == session_data.user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        # User doesn't exist or is inactive, destroy session
        destroy_session(session_id)
        return None

    return user


def create_csrf_token(session_id: str) -> str:
    """Create CSRF token for session.

    Args:
        session_id: Session identifier

    Returns:
        CSRF token
    """
    csrf_token = generate_csrf_token()
    _csrf_tokens[session_id] = csrf_token
    return csrf_token


def verify_csrf_token(session_id: str, token: str) -> bool:
    """Verify CSRF token for session.

    Args:
        session_id: Session identifier
        token: CSRF token to verify

    Returns:
        True if valid, False otherwise
    """
    return _csrf_tokens.get(session_id) == token


def get_csrf_token(session_id: str) -> str | None:
    """Get CSRF token for session.

    Args:
        session_id: Session identifier

    Returns:
        CSRF token if found, None otherwise
    """
    return _csrf_tokens.get(session_id)


def clear_csrf_token(session_id: str) -> None:
    """Clear CSRF token for session.

    Args:
        session_id: Session identifier
    """
    _csrf_tokens.pop(session_id, None)


# Test mode helpers
def is_test_mode() -> bool:
    """Check if we're in test mode."""
    import os
    return os.getenv('NODE_ENV') == 'test' or os.getenv('AUTH_BYPASS_ENABLED') == 'true'


class TestAuthSession:
    """Test mode authentication session."""

    @staticmethod
    def create_test_session(user: User, response: Response) -> str:
        """Create a test session with simplified authentication.

        Args:
            user: User object
            response: FastAPI Response object

        Returns:
            Test session identifier
        """
        if not is_test_mode():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test authentication only available in test mode"
            )

        test_session_id = f"test_{user.id}_{uuid4().hex[:8]}"

        # Set a simple test cookie
        response.set_cookie(
            key="test_session",
            value=test_session_id,
            httponly=True,
            secure=False,  # Allow HTTP in tests
            samesite="lax",
            path="/"
        )

        logger.info(f"Created test session for user: {user.username}")
        return test_session_id

    @staticmethod
    async def get_test_user(request: Request, db: AsyncSession) -> User | None:
        """Get user from test session.

        Args:
            request: FastAPI Request object
            db: Database session

        Returns:
            User object if test session is valid, None otherwise
        """
        if not is_test_mode():
            return None

        test_session = request.cookies.get("test_session")
        if not test_session or not test_session.startswith("test_"):
            return None

        try:
            # Extract user ID from test session
            parts = test_session.split("_")
            if len(parts) >= 2:
                user_id = parts[1]

                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()

                if user and user.is_active:
                    return user
        except Exception as e:
            logger.warning(f"Invalid test session format: {e}")

        return None


# Production session stats
def get_session_stats() -> dict[str, Any]:
    """Get session statistics.

    Returns:
        Dictionary with session stats
    """
    now = datetime.utcnow()
    active_sessions = 0
    expired_sessions = 0

    for session_dict in _session_store.values():
        if session_dict['expires_at'] > now:
            active_sessions += 1
        else:
            expired_sessions += 1

    return {
        'active_sessions': active_sessions,
        'expired_sessions': expired_sessions,
        'total_sessions': len(_session_store),
        'csrf_tokens': len(_csrf_tokens)
    }
