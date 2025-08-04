"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LibraryPathBase(BaseModel):
    """Base schema for library path."""

    path: str = Field(..., description="File system path to manga library")
    enabled: bool = Field(default=True, description="Whether this path is enabled for scanning")
    scan_interval_hours: int = Field(
        default=24, ge=1, le=168, description="Scan interval in hours (1-168)"
    )


class LibraryPathCreate(LibraryPathBase):
    """Schema for creating a library path."""

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """Validate path is not empty and properly formatted."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()


class LibraryPathUpdate(BaseModel):
    """Schema for updating a library path."""

    path: Optional[str] = Field(None, description="File system path to manga library")
    enabled: Optional[bool] = Field(None, description="Whether this path is enabled for scanning")
    scan_interval_hours: Optional[int] = Field(
        None, ge=1, le=168, description="Scan interval in hours (1-168)"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """Validate path is not empty and properly formatted."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Path cannot be empty")
        return v.strip() if v else v


class LibraryPathResponse(LibraryPathBase):
    """Schema for library path responses."""

    id: UUID = Field(..., description="Unique identifier")
    last_scan: Optional[datetime] = Field(None, description="Last scan timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class LibraryPathList(BaseModel):
    """Schema for list of library paths."""

    paths: list[LibraryPathResponse] = Field(..., description="List of library paths")
    total: int = Field(..., description="Total number of paths")


# Filesystem parser schemas for parsed series and chapter information
class ChapterInfo(BaseModel):
    """Schema for parsed chapter information from filesystem."""

    file_path: str = Field(..., description="Path to chapter file or directory")
    chapter_number: float = Field(..., description="Chapter number (supports fractional)")
    volume_number: Optional[int] = Field(None, description="Volume number if available")
    title: Optional[str] = Field(None, description="Chapter title if extracted")
    file_size: int = Field(0, description="File size in bytes")
    page_count: int = Field(0, description="Number of pages in chapter")
    source_metadata: Dict = Field(
        default_factory=dict, description="Additional metadata from parsing"
    )


class SeriesInfo(BaseModel):
    """Schema for parsed series information from filesystem."""

    title_primary: str = Field(..., description="Primary series title")
    file_path: str = Field(..., description="Path to series directory or file")
    chapters: List[ChapterInfo] = Field(default_factory=list, description="List of chapters")

    # Optional metadata
    title_alternative: Optional[str] = Field(None, description="Alternative series title")
    author: Optional[str] = Field(None, description="Series author")
    artist: Optional[str] = Field(None, description="Series artist")
    description: Optional[str] = Field(None, description="Series description")
    cover_image_path: Optional[str] = Field(None, description="Path to cover image")
    source_metadata: Dict = Field(
        default_factory=dict, description="Additional metadata from parsing"
    )

    @property
    def total_chapters(self) -> int:
        """Get total chapter count."""
        return len(self.chapters)


# Library scan schemas
class LibraryScanRequest(BaseModel):
    """Schema for library scan request."""

    library_path_id: Optional[UUID] = Field(
        None,
        description="Optional specific library path ID to scan. If not provided, scans all enabled paths",
    )


class LibraryScanStats(BaseModel):
    """Schema for library scan statistics."""

    series_found: int = Field(..., description="Total series found during scan")
    series_created: int = Field(..., description="Number of new series created")
    series_updated: int = Field(..., description="Number of existing series updated")
    chapters_found: int = Field(..., description="Total chapters found during scan")
    chapters_created: int = Field(..., description="Number of new chapters created")
    chapters_updated: int = Field(..., description="Number of existing chapters updated")
    errors: int = Field(..., description="Number of errors encountered during scan")


class LibraryScanResponse(BaseModel):
    """Schema for library scan response."""

    status: str = Field(..., description="Scan status (completed, failed)")
    message: str = Field(..., description="Human-readable status message")
    stats: LibraryScanStats = Field(..., description="Detailed scan statistics")


# Job queue schemas
class JobResponse(BaseModel):
    """Schema for job responses."""

    id: UUID = Field(..., description="Job unique identifier")
    job_type: str = Field(..., description="Type of job (e.g., library_scan)")
    payload: Dict = Field(..., description="Job payload data")
    status: str = Field(..., description="Job status (pending, running, completed, failed)")
    priority: int = Field(..., description="Job priority (higher = more urgent)")

    # Execution tracking
    started_at: Optional[datetime] = Field(None, description="When job started execution")
    completed_at: Optional[datetime] = Field(None, description="When job completed")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    retry_count: int = Field(..., description="Number of retry attempts")
    max_retries: int = Field(..., description="Maximum retry attempts")

    # Scheduling
    scheduled_at: datetime = Field(..., description="When job was scheduled to run")

    # Timestamps
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, job):
        """Create JobResponse from JobQueue model."""
        return cls(
            id=job.id,
            job_type=job.job_type,
            payload=job.payload,
            status=job.status,
            priority=job.priority,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            scheduled_at=job.scheduled_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class JobListResponse(BaseModel):
    """Schema for list of jobs."""

    jobs: List[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs returned")
    job_type_filter: Optional[str] = Field(None, description="Applied job type filter")


class JobScheduleRequest(BaseModel):
    """Schema for job scheduling requests."""

    job_type: str = Field(..., description="Type of job to schedule (library_scan, auto_schedule)")
    library_path_id: Optional[UUID] = Field(
        None, description="Optional specific library path ID for manual scans"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1=low, 10=high)")

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, v):
        """Validate job type is supported."""
        allowed_types = ["library_scan", "auto_schedule"]
        if v not in allowed_types:
            raise ValueError(f"Invalid job type. Must be one of: {allowed_types}")
        return v


class JobScheduleResponse(BaseModel):
    """Schema for job scheduling responses."""

    status: str = Field(..., description="Scheduling status (scheduled, completed)")
    message: str = Field(..., description="Human-readable status message")
    job_id: Optional[UUID] = Field(None, description="ID of scheduled job (for manual jobs)")
    scheduled_count: int = Field(default=0, description="Number of jobs scheduled")
    skipped_count: Optional[int] = Field(
        None, description="Number of paths skipped (for auto scheduling)"
    )
    total_paths: Optional[int] = Field(
        None, description="Total paths evaluated (for auto scheduling)"
    )


class JobStatsResponse(BaseModel):
    """Schema for job queue statistics."""

    queue_stats: Dict[str, int] = Field(..., description="Job queue statistics by status")
    worker_status: Optional[Dict[str, Any]] = Field(None, description="Worker status information")
    timestamp: datetime = Field(..., description="Statistics timestamp")


class WorkerStatusResponse(BaseModel):
    """Schema for worker status responses."""

    running: bool = Field(..., description="Whether worker is running")
    active_jobs: int = Field(..., description="Number of currently active jobs")
    max_concurrent_jobs: int = Field(..., description="Maximum concurrent jobs allowed")
    poll_interval_seconds: int = Field(..., description="Job polling interval in seconds")
    message: Optional[str] = Field(None, description="Additional status message")


# Series and Chapter schemas for API responses
class SeriesResponse(BaseModel):
    """Schema for series API responses."""

    id: UUID = Field(..., description="Series unique identifier")
    title_primary: str = Field(..., description="Primary series title")
    title_alternative: Optional[str] = Field(None, description="Alternative series title")
    description: Optional[str] = Field(None, description="Series description")
    author: Optional[str] = Field(None, description="Series author")
    artist: Optional[str] = Field(None, description="Series artist")
    genres: List[str] = Field(default_factory=list, description="Series genres")
    tags: List[str] = Field(default_factory=list, description="Series tags")
    publication_status: Optional[str] = Field(None, description="Publication status")
    content_rating: Optional[str] = Field(None, description="Content rating")
    language: str = Field(..., description="Series language")

    # File system information
    file_path: Optional[str] = Field(None, description="File system path")
    cover_image_path: Optional[str] = Field(None, description="Cover image path")

    # External source information
    mangadx_id: Optional[str] = Field(None, description="MangaDx ID")
    source_metadata: Dict = Field(default_factory=dict, description="Source metadata")

    # User customization
    user_metadata: Dict = Field(default_factory=dict, description="User metadata")
    custom_tags: List[str] = Field(default_factory=list, description="Custom user tags")

    # Statistics
    total_chapters: int = Field(..., description="Total chapter count")
    read_chapters: int = Field(..., description="Number of read chapters")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, series):
        """Create SeriesResponse from Series model."""
        return cls(
            id=series.id,
            title_primary=series.title_primary,
            title_alternative=series.title_alternative,
            description=series.description,
            author=series.author,
            artist=series.artist,
            genres=series.genres,
            tags=series.tags,
            publication_status=series.publication_status,
            content_rating=series.content_rating,
            language=series.language,
            file_path=series.file_path,
            cover_image_path=series.cover_image_path,
            mangadx_id=series.mangadx_id,
            source_metadata=series.source_metadata,
            user_metadata=series.user_metadata,
            custom_tags=series.custom_tags,
            total_chapters=series.total_chapters,
            read_chapters=series.read_chapters,
            created_at=series.created_at,
            updated_at=series.updated_at,
        )


class ChapterResponse(BaseModel):
    """Schema for chapter API responses."""

    id: UUID = Field(..., description="Chapter unique identifier")
    series_id: UUID = Field(..., description="Parent series ID")

    # Chapter identification
    chapter_number: float = Field(..., description="Chapter number")
    volume_number: Optional[int] = Field(None, description="Volume number")
    title: Optional[str] = Field(None, description="Chapter title")

    # File system information
    file_path: str = Field(..., description="File system path")
    file_size: int = Field(..., description="File size in bytes")
    page_count: int = Field(..., description="Number of pages")

    # External source information
    mangadx_id: Optional[str] = Field(None, description="MangaDx ID")
    source_metadata: Dict = Field(default_factory=dict, description="Source metadata")

    # Reading progress
    is_read: bool = Field(..., description="Whether chapter is marked as read")
    last_read_page: int = Field(..., description="Last read page number")
    read_at: Optional[datetime] = Field(None, description="When chapter was read")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional series information (when loaded with relationship)
    series: Optional[SeriesResponse] = Field(None, description="Parent series information")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, chapter, include_series: bool = False):
        """Create ChapterResponse from Chapter model."""
        data = {
            "id": chapter.id,
            "series_id": chapter.series_id,
            "chapter_number": chapter.chapter_number,
            "volume_number": chapter.volume_number,
            "title": chapter.title,
            "file_path": chapter.file_path,
            "file_size": chapter.file_size,
            "page_count": chapter.page_count,
            "mangadx_id": chapter.mangadx_id,
            "source_metadata": chapter.source_metadata,
            "is_read": chapter.is_read,
            "last_read_page": chapter.last_read_page,
            "read_at": chapter.read_at,
            "created_at": chapter.created_at,
            "updated_at": chapter.updated_at,
        }

        # Include series if available and requested
        if include_series and hasattr(chapter, "series") and chapter.series:
            data["series"] = SeriesResponse.from_model(chapter.series)

        return cls(**data)


class PageInfoResponse(BaseModel):
    """Schema for page information responses."""

    page_number: int = Field(..., description="Page number (1-indexed)")
    url: str = Field(..., description="URL to stream the page image")


class ChapterPagesInfoResponse(BaseModel):
    """Schema for chapter pages information response."""

    chapter_id: UUID = Field(..., description="Chapter unique identifier")
    total_pages: int = Field(..., description="Total number of pages")
    pages: List[PageInfoResponse] = Field(..., description="List of page information")
