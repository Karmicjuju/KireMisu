from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")


class UserCreate(UserBase):
    """Schema for user creation requests."""
    password: str = Field(..., min_length=8, max_length=255, description="User password")


class UserUpdate(BaseModel):
    """Schema for user update requests."""
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    is_active: Optional[bool] = Field(None, description="Whether user is active")


class UserResponse(UserBase):
    """Schema for user responses."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """Schema for user data with hashed password (internal use)."""
    hashed_password: str


class UserLogin(BaseModel):
    """Schema for user login requests."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class Token(BaseModel):
    """Schema for authentication token responses."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""
    username: Optional[str] = None