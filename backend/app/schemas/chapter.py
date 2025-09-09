from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class ChapterBase(BaseModel):
    """Base chapter schema with common fields."""
    number: Decimal = Field(..., ge=0, description="Chapter number")
    title: Optional[str] = Field(None, max_length=500, description="Chapter title")
    volume: Optional[Decimal] = Field(None, ge=0, description="Volume number")
    description: Optional[str] = Field(None, max_length=2000, description="Chapter description")
    release_date: Optional[datetime] = Field(None, description="Chapter release date")
    page_count: Optional[int] = Field(None, ge=1, description="Number of pages")


class ChapterCreate(ChapterBase):
    """Schema for chapter creation requests."""
    series_id: int = Field(..., gt=0, description="ID of the parent series")
    file_path: str = Field(..., min_length=1, max_length=1000, description="Path to chapter file")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path to prevent path traversal attacks."""
        # Basic validation - path should not be empty or just whitespace
        path_str = v.strip()
        if not path_str:
            raise ValueError("File path cannot be empty")
        
        # Check for path traversal attempts
        if '..' in v:
            raise ValueError("Path traversal detected: '..' not allowed")
        
        # Check for absolute path indicators
        if v.startswith('/') or (len(v) > 1 and v[1] == ':'):
            raise ValueError("Absolute paths not allowed")
        
        # Check for dangerous characters and patterns  
        dangerous_chars = ['<', '>', '|', '*', '?', '"']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Path contains invalid characters")
        
        # Check for valid archive extensions
        path = Path(v)
        allowed_extensions = {'.zip', '.rar', '.7z', '.cbz', '.cbr', '.cb7', '.tar', '.gz'}
        if path.suffix.lower() not in allowed_extensions:
            raise ValueError("Must have a valid archive extension (.zip, .rar, .7z, .cbz, .cbr, .cb7, .tar, .gz)")
        
        # Ensure path doesn't start with dangerous patterns
        if v.startswith(('http://', 'https://', 'ftp://', 'file://')):
            raise ValueError("URL schemes not allowed")
        
        return v


class ChapterUpdate(BaseModel):
    """Schema for chapter update requests."""
    number: Optional[Decimal] = Field(None, ge=0, description="Chapter number")
    title: Optional[str] = Field(None, max_length=500, description="Chapter title")
    volume: Optional[Decimal] = Field(None, ge=0, description="Volume number")
    description: Optional[str] = Field(None, max_length=2000, description="Chapter description")
    release_date: Optional[datetime] = Field(None, description="Chapter release date")
    page_count: Optional[int] = Field(None, ge=1, description="Number of pages")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    read_status: Optional[bool] = Field(None, description="Whether chapter has been read")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")


class ChapterResponse(ChapterBase):
    """Schema for chapter responses."""
    id: int
    series_id: int
    file_path: str
    read_status: bool
    file_size: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChapterWithSeriesResponse(ChapterResponse):
    """Schema for chapter responses with series information."""
    series: Optional[Dict[str, Any]] = None  # Will contain basic series info
    
    class Config:
        from_attributes = True


class ChapterListResponse(BaseModel):
    """Schema for paginated chapter list responses."""
    items: List[ChapterResponse]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        from_attributes = True


class BulkChapterUpdate(BaseModel):
    """Schema for bulk chapter updates."""
    chapter_ids: List[int] = Field(..., min_items=1, description="List of chapter IDs to update")
    updates: ChapterUpdate = Field(..., description="Updates to apply to all chapters")
    
    @field_validator('chapter_ids')
    @classmethod
    def validate_chapter_ids(cls, v: List[int]) -> List[int]:
        """Validate chapter IDs list."""
        if len(v) > 100:
            raise ValueError("Cannot update more than 100 chapters at once")
        
        if len(set(v)) != len(v):
            raise ValueError("Chapter IDs must be unique")
        
        return v