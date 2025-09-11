from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path
import os


class LibraryPathBase(BaseModel):
    """Base library path schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name for the library path")
    path: str = Field(..., min_length=1, max_length=1000, description="Absolute path to the library directory")
    is_active: bool = Field(default=True, description="Whether this path is currently active")
    priority: int = Field(default=0, description="Priority order (higher numbers have higher priority)")

    @validator('path')
    def validate_path(cls, v):
        """Validate that path is absolute and properly formatted."""
        if not v:
            raise ValueError("Path cannot be empty")
        
        # Normalize path separators for current OS
        normalized_path = os.path.normpath(v)
        
        # Check if path is absolute
        if not os.path.isabs(normalized_path):
            raise ValueError("Path must be absolute")
        
        return normalized_path

    @validator('name')
    def validate_name(cls, v):
        """Validate that name is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()


class LibraryPathCreate(LibraryPathBase):
    """Schema for library path creation requests."""
    pass


class LibraryPathUpdate(BaseModel):
    """Schema for library path update requests."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Display name for the library path")
    is_active: Optional[bool] = Field(None, description="Whether this path is currently active")
    priority: Optional[int] = Field(None, description="Priority order (higher numbers have higher priority)")

    @validator('name')
    def validate_name(cls, v):
        """Validate that name is not empty after stripping whitespace."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip() if v else v


class LibraryPathResponse(LibraryPathBase):
    """Schema for library path responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DirectoryItem(BaseModel):
    """Schema for directory browsing items."""
    name: str = Field(..., description="Name of the directory or file")
    path: str = Field(..., description="Full path to the item")
    is_directory: bool = Field(..., description="Whether this item is a directory")
    size: Optional[int] = Field(None, description="Size in bytes (for files only)")
    modified_at: Optional[datetime] = Field(None, description="Last modification time")


class DirectoryBrowseResponse(BaseModel):
    """Schema for directory browsing response."""
    current_path: str = Field(..., description="Current directory path")
    parent_path: Optional[str] = Field(None, description="Parent directory path")
    items: List[DirectoryItem] = Field(..., description="List of directory items")
    total_items: int = Field(..., description="Total number of items")


class PathValidationResult(BaseModel):
    """Schema for path validation results."""
    is_valid: bool = Field(..., description="Whether the path is valid and accessible")
    exists: bool = Field(..., description="Whether the path exists")
    is_directory: bool = Field(..., description="Whether the path is a directory")
    is_readable: bool = Field(..., description="Whether the path is readable")
    is_writable: bool = Field(..., description="Whether the path is writable")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    total_space: Optional[int] = Field(None, description="Total space in bytes (if accessible)")
    free_space: Optional[int] = Field(None, description="Free space in bytes (if accessible)")


class StorageInfo(BaseModel):
    """Schema for storage information."""
    total_space: int = Field(..., description="Total space in bytes")
    used_space: int = Field(..., description="Used space in bytes")
    free_space: int = Field(..., description="Free space in bytes")
    usage_percentage: float = Field(..., description="Usage percentage (0-100)")