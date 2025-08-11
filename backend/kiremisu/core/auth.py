"""Authentication system for KireMisu API endpoints."""

import logging
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from passlib.context import CryptContext

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

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# User management functions
class UserManager:
    """Simple user management for demonstration purposes.
    
    In a production environment, this would integrate with your existing
    user authentication system (e.g., OAuth, LDAP, database users, etc.)
    """
    
    # Simple in-memory user store for demo purposes
    # In production, this would be backed by a database
    _users: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_user(cls, username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user with hashed password."""
        if username in cls._users:
            raise ValueError(f"User {username} already exists")
            
        # Hash password with bcrypt
        password_hash = pwd_context.hash(password)
        
        user_id = f"user_{secrets.token_hex(8)}"
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        cls._users[username] = user_data
        logger.info(f"Created user: {username}")
        return {k: v for k, v in user_data.items() if k not in ['password_hash']}
    
    @classmethod
    def verify_user(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user data if valid."""
        user_data = cls._users.get(username)
        if not user_data or not user_data.get('is_active'):
            return None
            
        # Check password with bcrypt
        if pwd_context.verify(password, user_data['password_hash']):
            return {k: v for k, v in user_data.items() if k not in ['password_hash']}
        return None
    
    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        for user_data in cls._users.values():
            if user_data['id'] == user_id:
                return {k: v for k, v in user_data.items() if k not in ['password_hash']}
        return None

# Initialize default users from environment
def initialize_default_users():
    """Initialize default users from environment variables."""
    import os
    
    # Create default admin user from environment
    default_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    default_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    default_email = os.getenv("DEFAULT_ADMIN_EMAIL", f"{default_username}@kiremisu.local")
    
    if default_password:
        try:
            UserManager.create_user(default_username, default_password, default_email)
            logger.info(f"Created default admin user: {default_username}")
        except ValueError as e:
            if "already exists" in str(e):
                logger.debug(f"Default admin user already exists: {default_username}")
            else:
                logger.error(f"Failed to create default admin user: {e}")
    else:
        logger.warning("No DEFAULT_ADMIN_PASSWORD environment variable set - no default admin user created")
    
    # Demo users removed for security - no hardcoded test credentials

# Initialize default users on module load
initialize_default_users()


# Database-backed user management functions
async def create_user_db(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    is_admin: bool = False
) -> User:
    """Create a new user in the database."""
    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == email)
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("User with this username or email already exists")
    
    # Create new user
    user = User(
        username=username,
        email=email,
        password_hash=pwd_context.hash(password),
        is_admin=is_admin,
        is_active=True,
        email_verified=False,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Created user in database: {username}")
    return user


async def verify_user_db(
    db: AsyncSession,
    username_or_email: str,
    password: str
) -> Optional[User]:
    """Verify user credentials against database."""
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        return None
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        logger.warning(f"Login attempt for locked account: {username_or_email}")
        return None
    
    # Verify password
    if not pwd_context.verify(password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            logger.warning(f"Account locked due to failed login attempts: {username_or_email}")
        
        await db.commit()
        return None
    
    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    user.locked_until = None
    await db.commit()
    
    return user


async def get_user_by_id_db(db: AsyncSession, user_id: str) -> Optional[User]:
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
    """Update user password."""
    user.password_hash = pwd_context.hash(new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"Password updated for user: {user.username}")


async def initialize_admin_user(db: AsyncSession) -> None:
    """Initialize admin user from environment variables."""
    import os
    
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", f"{admin_username}@kiremisu.local")
    
    if not admin_password:
        logger.warning("No DEFAULT_ADMIN_PASSWORD set - skipping admin user creation")
        return
    
    try:
        # Check if admin already exists
        result = await db.execute(
            select(User).where(
                (User.username == admin_username) | (User.email == admin_email)
            )
        )
        if result.scalar_one_or_none():
            logger.debug(f"Admin user already exists: {admin_username}")
            return
        
        # Create admin user
        await create_user_db(
            db=db,
            username=admin_username,
            email=admin_email,
            password=admin_password,
            is_admin=True
        )
        logger.info(f"Created admin user: {admin_username}")
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")

def create_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create a JWT token for the user."""
    # Handle both dict and User model
    if hasattr(user_data, 'id'):
        # User model
        payload = {
            "user_id": str(user_data.id),
            "username": user_data.username,
            "email": user_data.email,
            "is_admin": user_data.is_admin,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
        }
    else:
        # Dict (legacy support)
        payload = {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "email": user_data.get("email"),
            "is_admin": user_data.get("is_admin", False),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
        }
    
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_api_key(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate JWT token from Authorization header."""
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
    
    # Verify JWT token
    payload = verify_jwt_token(token)
    
    # Verify user still exists and is active
    user_data = UserManager.get_user_by_id(payload["user_id"])
    if not user_data or not user_data.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from database."""
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
    
    # Verify JWT token
    payload = verify_jwt_token(token)
    
    # Get user from database
    user = await get_user_by_id_db(db, payload["user_id"])
    if not user or not user.is_active:
        # Fallback to in-memory user manager for backwards compatibility
        user_data = UserManager.get_user_by_id(payload["user_id"])
        if user_data and user_data.get("is_active"):
            # Return a mock User object for compatibility
            from uuid import uuid4
            mock_user = User(
                id=uuid4(),
                username=user_data["username"],
                email=user_data.get("email", f"{user_data['username']}@kiremisu.local"),
                password_hash="",
                is_active=True,
                is_admin=False
            )
            return mock_user
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked due to failed login attempts",
        )
    
    return user


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
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
    """Require the current user to be an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


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