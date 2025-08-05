"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, validator

# Generic type for paginated responses
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page (1-100)")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.per_page


class PaginationMeta(BaseModel):
    """Schema for pagination metadata."""

    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_prev: bool = Field(..., description="Whether there's a previous page")
    has_next: bool = Field(..., description="Whether there's a next page")
    prev_page: Optional[int] = Field(None, description="Previous page number")
    next_page: Optional[int] = Field(None, description="Next page number")

    @classmethod
    def create(cls, page: int, per_page: int, total_items: int) -> "PaginationMeta":
        """Create pagination metadata from parameters."""
        total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

        return cls(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages,
            prev_page=page - 1 if page > 1 else None,
            next_page=page + 1 if page < total_pages else None,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated API responses."""

    items: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


# Tag schemas
class TagBase(BaseModel):
    """Base schema for tag."""

    name: str = Field(..., max_length=100, description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field(None, description="Tag color (hex format #RRGGBB)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate tag name is not empty and properly formatted."""
        if not v or not v.strip():
            raise ValueError("Tag name cannot be empty")
        # Remove extra whitespace and convert to lowercase for consistency
        return v.strip().lower()

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        """Validate color is in proper hex format."""
        if v is None:
            return v
        v = v.strip()
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in hex format #RRGGBB")
        try:
            int(v[1:], 16)  # Validate hex digits
        except ValueError:
            raise ValueError("Color must contain valid hex digits")
        return v.upper()


class TagCreate(TagBase):
    """Schema for creating a tag."""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: Optional[str] = Field(None, max_length=100, description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field(None, description="Tag color (hex format #RRGGBB)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate tag name is not empty and properly formatted."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Tag name cannot be empty")
        return v.strip().lower() if v else v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        """Validate color is in proper hex format."""
        if v is None:
            return v
        v = v.strip()
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in hex format #RRGGBB")
        try:
            int(v[1:], 16)  # Validate hex digits
        except ValueError:
            raise ValueError("Color must contain valid hex digits")
        return v.upper()


class TagResponse(TagBase):
    """Schema for tag responses."""

    id: UUID = Field(..., description="Tag unique identifier")
    usage_count: int = Field(..., description="Number of series using this tag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, tag):
        """Create TagResponse from Tag model."""
        return cls(
            id=tag.id,
            name=tag.name,
            description=tag.description,
            color=tag.color,
            usage_count=tag.usage_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )


class TagListResponse(BaseModel):
    """Schema for list of tags."""

    tags: List[TagResponse] = Field(..., description="List of tags")
    total: int = Field(..., description="Total number of tags")


class SeriesTagAssignment(BaseModel):
    """Schema for assigning/removing tags to/from series."""

    tag_ids: List[UUID] = Field(..., description="List of tag IDs to assign")

    @field_validator("tag_ids")
    @classmethod
    def validate_tag_ids(cls, v):
        """Validate tag IDs list is not empty and contains unique values."""
        if not v:
            raise ValueError("Tag IDs list cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("Tag IDs must be unique")
        return v


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

    job_type: str = Field(
        ..., description="Type of job to schedule (library_scan, auto_schedule, download)"
    )
    library_path_id: Optional[UUID] = Field(
        None, description="Optional specific library path ID for manual scans"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1=low, 10=high)")

    # Download job specific fields
    manga_id: Optional[str] = Field(None, description="External manga ID for download jobs")
    download_type: Optional[str] = Field(default="mangadx", description="Download source type")
    series_id: Optional[UUID] = Field(
        None, description="Optional local series ID to associate with"
    )

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, v):
        """Validate job type is supported."""
        allowed_types = ["library_scan", "auto_schedule", "download"]
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
    user_tags: List[TagResponse] = Field(default_factory=list, description="User-assigned tags")

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
        # Handle user_tags relationship
        user_tags = []
        if hasattr(series, 'user_tags') and series.user_tags:
            user_tags = [TagResponse.from_model(tag) for tag in series.user_tags]
        
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
            user_tags=user_tags,
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


# Reader-specific schemas
class ChapterProgressUpdate(BaseModel):
    """Schema for updating chapter reading progress."""

    last_read_page: int = Field(..., ge=0, description="Last read page number (0-indexed)")
    is_read: Optional[bool] = Field(None, description="Whether chapter is marked as read")

    @field_validator("last_read_page")
    @classmethod
    def validate_page_number(cls, v):
        """Validate page number is non-negative."""
        if v < 0:
            raise ValueError("Page number must be non-negative")
        return v


class ChapterProgressResponse(ChapterResponse):
    """Schema for chapter progress update responses."""

    pass


class ChapterInfoResponse(BaseModel):
    """Schema for reader chapter info responses."""

    id: UUID = Field(..., description="Chapter unique identifier")
    series_id: UUID = Field(..., description="Parent series ID")
    series_title: str = Field(..., description="Parent series title")

    # Chapter identification
    chapter_number: float = Field(..., description="Chapter number")
    volume_number: Optional[int] = Field(None, description="Volume number")
    title: Optional[str] = Field(None, description="Chapter title")

    # File system information
    file_size: int = Field(..., description="File size in bytes")
    page_count: int = Field(..., description="Number of pages")

    # Reading progress
    is_read: bool = Field(..., description="Whether chapter is marked as read")
    last_read_page: int = Field(..., description="Last read page number")
    read_at: Optional[datetime] = Field(None, description="When chapter was read")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class SeriesChaptersResponse(BaseModel):
    """Schema for series chapters response."""

    series: SeriesResponse = Field(..., description="Series information")
    chapters: List[ChapterResponse] = Field(..., description="List of chapters in order")


# Mark-read and progress schemas
class ChapterMarkReadResponse(BaseModel):
    """Schema for mark-read toggle response."""

    id: UUID = Field(..., description="Chapter unique identifier")
    is_read: bool = Field(..., description="Updated read status")
    read_at: Optional[datetime] = Field(None, description="When chapter was marked as read")
    series_read_chapters: int = Field(..., description="Updated series read chapter count")

    model_config = ConfigDict(from_attributes=True)


class SeriesProgressResponse(BaseModel):
    """Schema for series progress information."""

    series_id: UUID = Field(..., description="Series unique identifier")
    total_chapters: int = Field(..., description="Total number of chapters")
    read_chapters: int = Field(..., description="Number of read chapters")
    progress_percentage: float = Field(..., description="Progress percentage (0-100)")
    recent_chapters: List[ChapterResponse] = Field(
        default_factory=list, description="Recently read chapters (up to 5)"
    )
    last_read_at: Optional[datetime] = Field(None, description="Most recent read timestamp")

    model_config = ConfigDict(from_attributes=True)


class DashboardStatsResponse(BaseModel):
    """Schema for dashboard statistics."""

    total_series: int = Field(..., description="Total number of series in library")
    total_chapters: int = Field(..., description="Total number of chapters in library")
    read_chapters: int = Field(..., description="Total number of read chapters")
    reading_progress_percentage: float = Field(
        ..., description="Overall reading progress percentage (0-100)"
    )
    recent_activity: List[ChapterResponse] = Field(
        default_factory=list, description="Recently read chapters (up to 10)"
    )
    series_by_status: dict = Field(
        default_factory=dict, description="Series counts by reading status"
    )
    last_updated: datetime = Field(..., description="Statistics calculation timestamp")

    model_config = ConfigDict(from_attributes=True)
