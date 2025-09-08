"""FastAPI-Users configuration for authentication."""
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select

from app.models.user import User
from app.db.database import get_user_db
from app.core.config import settings


class UserManager(BaseUserManager[User, uuid.UUID]):
    """Custom user manager for KireMisu."""
    
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    def parse_id(self, value: str) -> uuid.UUID:
        """Parse user ID from string to UUID."""
        try:
            return uuid.UUID(value)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {value}")

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    async def authenticate(self, credentials) -> Optional[User]:
        """Custom authentication that supports both email and username."""
        try:
            username_or_email = credentials.username
            password = credentials.password
            
            if not username_or_email or not password:
                return None
            
            # Try to find user by email first
            try:
                user = await self.get_by_email(username_or_email)
            except:
                user = None
            
            # If not found by email, try by username
            if not user:
                stmt = select(User).where(User.username == username_or_email)
                result = await self.user_db.session.execute(stmt)
                user = result.scalar_one_or_none()
            
            if user and self.password_helper.verify_and_update(password, user.hashed_password)[0]:
                return user
                
            return None
        except Exception as e:
            print(f"Authentication error: {e}")
            return None


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


# Authentication configuration
cookie_transport = CookieTransport(
    cookie_name="kiremisu_auth",
    cookie_max_age=3600 * 24 * 7,  # 1 week
    cookie_httponly=True,
    cookie_secure=settings.ENVIRONMENT == "production",
    cookie_samesite="lax",
    cookie_domain="localhost" if settings.ENVIRONMENT == "development" else None,
)

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600 * 24 * 7)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)