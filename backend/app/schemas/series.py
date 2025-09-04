from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import os
from pydantic import BaseModel, Field, field_validator


class SeriesBase(BaseModel):
    """Base series schema with common fields."""
    title: str = Field(..., min_length=1, max_length=500, description="Series title")
    description: Optional[str] = Field(None, max_length=2000, description="Series description")
    author: Optional[str] = Field(None, max_length=255, description="Series author")
    artist: Optional[str] = Field(None, max_length=255, description="Series artist")
    status: Optional[str] = Field(None, max_length=50, description="Series status (ongoing, completed, hiatus, etc.)")


class SeriesCreate(SeriesBase):
    """Schema for series creation requests."""
    cover_path: Optional[str] = Field(None, max_length=1000, description="Path to cover image")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")
    
    @field_validator('cover_path')
    @classmethod
    def validate_cover_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate cover path to prevent path traversal attacks."""
        if v is None:
            return v
        
        # Basic validation - path should not be empty or just whitespace
        path_str = v.strip()
        if not path_str:
            raise ValueError("Cover path cannot be empty")
        
        # Check for path traversal attempts
        if '..' in v:
            raise ValueError("Path traversal detected: '..' not allowed")
        
        # Check for absolute path indicators
        if v.startswith('/') or (len(v) > 1 and v[1] == ':'):
            raise ValueError("Absolute paths not allowed")
        
        # Check for dangerous characters and patterns  
        dangerous_chars = ['\\', '<', '>', '|', '*', '?', '"']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Path contains invalid characters")
        
        # Check for valid file extension
        path = Path(v)
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
        if path.suffix.lower() not in allowed_extensions:
            raise ValueError("Must have a valid image extension (.jpg, .jpeg, .png, .webp, .gif, .bmp)")
        
        # Ensure path doesn't start with dangerous patterns
        if v.startswith(('http://', 'https://', 'ftp://', 'file://')):
            raise ValueError("URL schemes not allowed")
        
        return v


class SeriesUpdate(BaseModel):
    """Schema for series update requests."""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Series title")
    description: Optional[str] = Field(None, max_length=2000, description="Series description")
    author: Optional[str] = Field(None, max_length=255, description="Series author")
    artist: Optional[str] = Field(None, max_length=255, description="Series artist")
    status: Optional[str] = Field(None, max_length=50, description="Series status")
    cover_path: Optional[str] = Field(None, max_length=1000, description="Path to cover image")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")
    
    @field_validator('cover_path')
    @classmethod
    def validate_cover_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate cover path to prevent path traversal attacks."""
        if v is None:
            return v
        
        # Basic validation - path should not be empty or just whitespace
        path_str = v.strip()
        if not path_str:
            raise ValueError("Cover path cannot be empty")
        
        # Check for path traversal attempts
        if '..' in v:
            raise ValueError("Path traversal detected: '..' not allowed")
        
        # Check for absolute path indicators
        if v.startswith('/') or (len(v) > 1 and v[1] == ':'):
            raise ValueError("Absolute paths not allowed")
        
        # Check for dangerous characters and patterns  
        dangerous_chars = ['\\', '<', '>', '|', '*', '?', '"']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Path contains invalid characters")
        
        # Check for valid file extension
        path = Path(v)
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
        if path.suffix.lower() not in allowed_extensions:
            raise ValueError("Must have a valid image extension (.jpg, .jpeg, .png, .webp, .gif, .bmp)")
        
        # Ensure path doesn't start with dangerous patterns
        if v.startswith(('http://', 'https://', 'ftp://', 'file://')):
            raise ValueError("URL schemes not allowed")
        
        return v


class SeriesResponse(SeriesBase):
    """Schema for series responses."""
    id: int
    cover_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeriesListResponse(BaseModel):
    """Schema for paginated series list responses."""
    items: List[SeriesResponse]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True


class SeriesWithChaptersResponse(SeriesResponse):
    """Schema for series response with chapters included."""
    chapters: List[Any] = []  # Will be replaced with ChapterResponse when chapter schemas exist

    class Config:
        from_attributes = True