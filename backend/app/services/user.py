from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


class UserService:
    """Service layer for user authentication and management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = self.user_repo.get_user_by_username(username)
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
            
        # Only return active users
        if not user.is_active:
            return None
            
        return user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.user_repo.get_user_by_username(username)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.user_repo.get_user_by_id(user_id)
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password."""
        hashed_password = self.get_password_hash(user_data.password)
        return self.user_repo.create_user(user_data, hashed_password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a plain password."""
        return self.pwd_context.hash(password)
    
    def create_admin_user(self, username: str, password: str, email: str, full_name: str = None) -> User:
        """Create an admin user with superuser privileges."""
        user_data = UserCreate(
            username=username,
            password=password,
            email=email,
            full_name=full_name or "Administrator"
        )
        
        # Create user with hashed password
        hashed_password = self.get_password_hash(password)
        user = self.user_repo.create_user(user_data, hashed_password)
        
        # Set as superuser
        user.is_superuser = True
        self.db.commit()
        self.db.refresh(user)
        
        return user