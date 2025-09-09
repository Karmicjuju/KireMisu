"""Pydantic schemas for manga reader functionality."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ReadingProgressBase(BaseModel):
    """Base schema for reading progress."""
    current_page: int = Field(..., ge=0, description="Current page number (0-indexed)")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    is_completed: bool = Field(default=False, description="Whether the chapter is completed")
    last_read: Optional[datetime] = Field(default=None, description="Last read timestamp")


class ReadingProgressResponse(ReadingProgressBase):
    """Response schema for reading progress."""
    chapter_id: int = Field(..., description="Chapter ID")
    
    model_config = ConfigDict(from_attributes=True)


class ReadingProgressUpdate(BaseModel):
    """Schema for updating reading progress."""
    page_number: int = Field(..., ge=0, description="Page number to update to (0-indexed)")
    
    model_config = ConfigDict(from_attributes=True)


class ChapterNavigation(BaseModel):
    """Schema for chapter navigation information."""
    id: int = Field(..., description="Chapter ID")
    number: str = Field(..., description="Chapter number")
    title: Optional[str] = Field(None, description="Chapter title")


class ChapterNavigationResponse(BaseModel):
    """Response schema for chapter navigation."""
    current_chapter: ChapterNavigation = Field(..., description="Current chapter info")
    previous_chapter: Optional[ChapterNavigation] = Field(None, description="Previous chapter info")
    next_chapter: Optional[ChapterNavigation] = Field(None, description="Next chapter info")
    total_chapters: int = Field(..., description="Total chapters in series")
    current_position: int = Field(..., description="Current position in series (1-indexed)")


class ChapterPagesResponse(BaseModel):
    """Response schema for chapter pages."""
    chapter_id: int = Field(..., description="Chapter ID")
    chapter_number: str = Field(..., description="Chapter number")
    chapter_title: Optional[str] = Field(None, description="Chapter title")
    series_title: str = Field(..., description="Series title")
    pages: List[str] = Field(..., description="List of page filenames")
    page_count: int = Field(..., description="Total number of pages")
    current_page: int = Field(..., description="Current page number")
    reading_progress: ReadingProgressResponse = Field(..., description="Reading progress information")


class PageImageRequest(BaseModel):
    """Request schema for page image."""
    max_width: Optional[int] = Field(None, ge=100, le=4000, description="Maximum width for resizing")


class ChapterInfoResponse(BaseModel):
    """Response schema for chapter information."""
    chapter_id: int = Field(..., description="Chapter ID")
    format: str = Field(..., description="File format")
    page_count: int = Field(..., description="Number of pages")
    file_size: int = Field(..., description="File size in bytes")
    pages: List[str] = Field(..., description="Preview of page filenames")
    is_valid: bool = Field(..., description="Whether the chapter file is valid")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ReaderSettingsBase(BaseModel):
    """Base schema for reader settings."""
    reading_direction: str = Field(default="ltr", description="Reading direction (ltr/rtl)")
    page_fit: str = Field(default="width", description="Page fit mode (width/height/screen)")
    zoom_level: float = Field(default=1.0, ge=0.1, le=5.0, description="Zoom level")
    preload_pages: int = Field(default=3, ge=1, le=10, description="Number of pages to preload")
    show_page_numbers: bool = Field(default=True, description="Show page numbers")
    fullscreen_mode: bool = Field(default=False, description="Fullscreen reading mode")


class ReaderSettingsUpdate(ReaderSettingsBase):
    """Schema for updating reader settings."""
    pass


class ReaderSettingsResponse(ReaderSettingsBase):
    """Response schema for reader settings."""
    user_id: int = Field(..., description="User ID")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class PageNavigationRequest(BaseModel):
    """Request schema for page navigation."""
    direction: str = Field(..., description="Navigation direction (next/prev/first/last)")
    current_page: int = Field(..., ge=0, description="Current page number")


class PageNavigationResponse(BaseModel):
    """Response schema for page navigation."""
    new_page: int = Field(..., description="New page number")
    page_filename: str = Field(..., description="Page filename")
    is_chapter_boundary: bool = Field(default=False, description="Whether navigation crosses chapter boundary")
    next_chapter_id: Optional[int] = Field(None, description="Next chapter ID if boundary crossed")
    message: Optional[str] = Field(None, description="Navigation message")


class ReaderStatsResponse(BaseModel):
    """Response schema for reader statistics."""
    total_chapters_read: int = Field(..., description="Total chapters read by user")
    total_pages_read: int = Field(..., description="Total pages read by user")
    reading_time_minutes: int = Field(..., description="Estimated reading time in minutes")
    favorite_series: List[str] = Field(..., description="Most read series")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent reading activity")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")