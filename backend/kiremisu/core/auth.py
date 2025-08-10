"""Authentication system for KireMisu API endpoints."""

import logging
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from kiremisu.core.config import get_settings
from kiremisu.database.connection import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

# Bearer token authentication
security = HTTPBearer(auto_error=False)

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


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
            
        # Hash password with salt
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        user_id = f"user_{secrets.token_hex(8)}"
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "salt": salt,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        cls._users[username] = user_data
        logger.info(f"Created user: {username}")
        return {k: v for k, v in user_data.items() if k not in ['password_hash', 'salt']}
    
    @classmethod
    def verify_user(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user data if valid."""
        user_data = cls._users.get(username)
        if not user_data or not user_data.get('is_active'):
            return None
            
        # Check password
        salt = user_data['salt']
        expected_hash = user_data['password_hash']
        provided_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        if expected_hash == provided_hash:
            return {k: v for k, v in user_data.items() if k not in ['password_hash', 'salt']}
        return None
    
    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        for user_data in cls._users.values():
            if user_data['id'] == user_id:
                return {k: v for k, v in user_data.items() if k not in ['password_hash', 'salt']}
        return None

# Initialize demo users
def initialize_demo_users():
    """Initialize demo users for development."""
    try:
        UserManager.create_user("demo", "demo123", "demo@kiremisu.local")
        UserManager.create_user("admin", "admin123", "admin@kiremisu.local")
    except ValueError:
        # Users already exist
        pass

# Initialize demo users on module load
initialize_demo_users()

def create_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create a JWT token for the user."""
    payload = {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "email": user_data.get("email"),
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

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Get the current authenticated user."""
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
    
    # Get user data
    user_data = UserManager.get_user_by_id(payload["user_id"])
    if not user_data or not user_data.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data


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