from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """Repository layer for user data access operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate, hashed_password: str) -> User:
        """Create a new user in the database."""
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
        )
        
        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except IntegrityError as e:
            self.db.rollback()
            # Check which constraint failed based on error message
            error_msg = str(e.orig)
            if "username" in error_msg or "uq_users_username" in error_msg:
                raise ValueError(f"Username '{user_data.username}' already exists")
            elif "email" in error_msg or "uq_users_email" in error_msg:
                raise ValueError(f"Email '{user_data.email}' already exists")
            else:
                raise ValueError("User creation failed due to constraint violation")
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.db.query(User).filter(User.email == email).first()
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        try:
            for field, value in update_data.items():
                setattr(db_user, field, value)
            
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig)
            if "email" in error_msg or "uq_users_email" in error_msg:
                raise ValueError(f"Email '{user_data.email}' already exists")
            else:
                raise ValueError("User update failed due to constraint violation")
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user by ID."""
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        return True
    
    def is_username_taken(self, username: str) -> bool:
        """Check if username is already taken."""
        return self.db.query(User).filter(User.username == username).first() is not None
    
    def is_email_taken(self, email: str) -> bool:
        """Check if email is already taken."""
        return self.db.query(User).filter(User.email == email).first() is not None
    
    def get_active_users_count(self) -> int:
        """Get count of active users."""
        return self.db.query(User).filter(User.is_active == True).count()
    
    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user account."""
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            return None
        
        db_user.is_active = True
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user account."""
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            return None
        
        db_user.is_active = False
        self.db.commit()
        self.db.refresh(db_user)
        return db_user