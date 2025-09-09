"""Pydantic schemas for reading progress and history."""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ReadingStatus(str, Enum):
    """Reading status enumeration."""
    UNREAD = "unread"
    READING = "reading"
    COMPLETED = "completed"


class ReadingEventType(str, Enum):
    """Reading event type enumeration."""
    STARTED = "started"
    PROGRESS_UPDATE = "progress_update"
    RESUMED = "resumed"
    COMPLETED = "completed"
    MARKED_READ = "marked_read"
    MARKED_UNREAD = "marked_unread"
    SESSION_END = "session_end"


# Request schemas
class ProgressUpdateRequest(BaseModel):
    """Request schema for updating reading progress."""
    current_page: int = Field(ge=0, description="Current page number (0-indexed)")
    total_pages: int = Field(gt=0, description="Total number of pages")
    session_duration_seconds: Optional[int] = Field(None, ge=0, description="Session duration in seconds")
    device_info: Optional[str] = Field(None, max_length=255, description="Device information")
    
    @field_validator('current_page')
    @classmethod
    def validate_current_page(cls, v, info):
        if 'total_pages' in info.data and v >= info.data['total_pages']:
            raise ValueError('current_page must be less than total_pages')
        return v


class BulkMarkRequest(BaseModel):
    """Request schema for bulk marking chapters."""
    chapter_ids: List[int] = Field(min_length=1, max_length=100, description="List of chapter IDs")
    device_info: Optional[str] = Field(None, max_length=255, description="Device information")


class ReadingHistoryFilter(BaseModel):
    """Filter parameters for reading history queries."""
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of records to return")
    offset: int = Field(default=0, ge=0, description="Number of records to skip")
    series_id: Optional[int] = Field(None, gt=0, description="Filter by series ID")
    event_type: Optional[ReadingEventType] = Field(None, description="Filter by event type")


class ReadingStatisticsFilter(BaseModel):
    """Filter parameters for reading statistics."""
    days: int = Field(default=30, ge=1, le=365, description="Number of days to include in statistics")


# Response schemas
class ChapterProgressResponse(BaseModel):
    """Response schema for individual chapter progress."""
    model_config = ConfigDict(from_attributes=True)
    
    chapter_id: int
    chapter_number: str
    chapter_title: Optional[str]
    status: ReadingStatus
    current_page: int
    total_pages: int
    progress_percentage: float = Field(ge=0.0, le=1.0)
    last_read_at: Optional[datetime]
    reading_time_seconds: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ReadingProgressResponse(BaseModel):
    """Response schema for reading progress."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: uuid.UUID
    chapter_id: int
    current_page: int
    total_pages: int
    status: ReadingStatus
    progress_percentage: float = Field(ge=0.0, le=1.0)
    is_completed: bool
    reading_time_seconds: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_read_at: datetime
    created_at: datetime
    updated_at: datetime


class SeriesProgressResponse(BaseModel):
    """Response schema for series reading progress."""
    series_id: int
    total_chapters: int
    read_chapters: int
    reading_chapters: int
    unread_chapters: int
    completion_percentage: float = Field(ge=0.0, le=100.0)
    total_reading_time_seconds: int
    chapters: List[ChapterProgressResponse]


class ReadingHistoryResponse(BaseModel):
    """Response schema for reading history entry."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    event_type: ReadingEventType
    series_title: Optional[str]
    chapter_number: Optional[str]
    chapter_title: Optional[str]
    page_number: Optional[int]
    total_pages: Optional[int]
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    session_duration_seconds: Optional[int]
    reading_speed_pages_per_minute: Optional[int]
    event_timestamp: datetime
    notes: Optional[str]


class ActivitySummary(BaseModel):
    """Summary of reading activity."""
    chapters_per_day: float = Field(ge=0.0)
    minutes_per_day: float = Field(ge=0.0)


class ReadingStatisticsResponse(BaseModel):
    """Response schema for reading statistics."""
    period_days: int
    total_reading_time_seconds: int = Field(ge=0)
    total_chapters_completed: int = Field(ge=0)
    recent_reading_time_seconds: int = Field(ge=0)
    recent_chapters_completed: int = Field(ge=0)
    current_reading_streak_days: int = Field(ge=0)
    average_reading_speed_pages_per_minute: float = Field(ge=0.0)
    activity_summary: ActivitySummary


class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations."""
    total_requested: int = Field(ge=0)
    successful: int = Field(ge=0)
    failed: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    
    @field_validator('success_rate', mode='before')
    @classmethod
    def calculate_success_rate(cls, v, info):
        if 'total_requested' in info.data and info.data['total_requested'] > 0:
            return info.data.get('successful', 0) / info.data['total_requested']
        return 0.0


class ResumeReadingResponse(BaseModel):
    """Response schema for resume reading functionality."""
    has_in_progress: bool
    recommended_chapter_id: Optional[int]
    recommended_series_id: Optional[int]
    last_read_chapter: Optional[ChapterProgressResponse]
    continue_reading_suggestions: List[ChapterProgressResponse] = Field(max_length=5)


# Error schemas
class ProgressError(BaseModel):
    """Error response schema for progress-related errors."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Utility schemas for dashboard/widgets
class ReadingProgressSummary(BaseModel):
    """Summary for dashboard widgets."""
    total_series: int = Field(ge=0)
    series_in_progress: int = Field(ge=0)
    series_completed: int = Field(ge=0)
    chapters_read_today: int = Field(ge=0)
    reading_time_today_minutes: int = Field(ge=0)
    current_streak_days: int = Field(ge=0)


class RecentActivity(BaseModel):
    """Recent reading activity for dashboard."""
    recent_chapters: List[ReadingHistoryResponse] = Field(max_length=10)
    active_series: List[SeriesProgressResponse] = Field(max_length=5)
    reading_goals: Optional[Dict[str, Any]] = None  # For future goal tracking


# Export all schemas
__all__ = [
    # Enums
    "ReadingStatus",
    "ReadingEventType",
    
    # Request schemas
    "ProgressUpdateRequest",
    "BulkMarkRequest", 
    "ReadingHistoryFilter",
    "ReadingStatisticsFilter",
    
    # Response schemas
    "ChapterProgressResponse",
    "ReadingProgressResponse",
    "SeriesProgressResponse",
    "ReadingHistoryResponse",
    "ReadingStatisticsResponse",
    "BulkOperationResponse",
    "ResumeReadingResponse",
    "ActivitySummary",
    
    # Utility schemas
    "ReadingProgressSummary",
    "RecentActivity",
    
    # Error schemas
    "ProgressError"
]