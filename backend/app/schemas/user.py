import uuid
from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, Field, field_validator
from fastapi_users import schemas

# Password validation constants
SPECIAL_CHARACTERS = r'[!@#$%^&*(),.?":{}|<>]'


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    created_at: datetime
    updated_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """Schema for user creation requests with custom validation."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        if not re.search(SPECIAL_CHARACTERS, v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for user update requests with custom fields."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")


# Legacy schemas for backward compatibility during migration
class UserResponse(UserRead):
    """Legacy schema for user responses (backward compatibility)."""
    pass


class Token(BaseModel):
    """Schema for authentication token responses."""
    access_token: str
    token_type: str = "bearer"