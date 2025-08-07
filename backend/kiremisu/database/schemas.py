"""Pydantic schemas for API requests and responses."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Generic, TypeVar, Literal, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, validator

if TYPE_CHECKING:
    from kiremisu.database.models import JobQueue

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
        """Validate color is in proper hex format and prevent CSS injection."""
        if v is None:
            return v
        v = v.strip()
        
        # Strict validation: must be exactly #RRGGBB format
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in hex format #RRGGBB")
        
        # Only allow alphanumeric hex characters after #
        hex_part = v[1:]
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_part):
            raise ValueError("Color must contain valid hex digits only")
        
        try:
            int(hex_part, 16)  # Validate hex digits
        except ValueError:
            raise ValueError("Color must contain valid hex digits")
        
        # Additional security: prevent any special characters that could be used for injection
        if any(char in v for char in [';', '(', ')', '{', '}', '/', '\\', '<', '>', '"', "'"]):
            raise ValueError("Color contains invalid characters")
            
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
        """Validate color is in proper hex format and prevent CSS injection."""
        if v is None:
            return v
        v = v.strip()
        
        # Strict validation: must be exactly #RRGGBB format
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in hex format #RRGGBB")
        
        # Only allow alphanumeric hex characters after #
        hex_part = v[1:]
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_part):
            raise ValueError("Color must contain valid hex digits only")
        
        try:
            int(hex_part, 16)  # Validate hex digits
        except ValueError:
            raise ValueError("Color must contain valid hex digits")
        
        # Additional security: prevent any special characters that could be used for injection
        if any(char in v for char in [';', '(', ')', '{', '}', '/', '\\', '<', '>', '"', "'"]):
            raise ValueError("Color contains invalid characters")
            
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
    started_reading_at: Optional[datetime] = Field(None, description="When reading started")

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
            "started_reading_at": getattr(chapter, 'started_reading_at', None),
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
    started_reading_at: Optional[datetime] = Field(None, description="When reading started")

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


class ReadingProgressUpdateRequest(BaseModel):
    """Schema for updating reading progress."""

    current_page: int = Field(..., ge=0, description="Current page being read (0-indexed)")
    is_complete: Optional[bool] = Field(None, description="Mark as complete if specified")

    @field_validator("current_page")
    @classmethod
    def validate_current_page(cls, v):
        """Validate current page is non-negative."""
        if v < 0:
            raise ValueError("Current page must be non-negative")
        return v


class ReadingProgressResponse(BaseModel):
    """Schema for reading progress responses."""

    chapter_id: UUID = Field(..., description="Chapter unique identifier")
    series_id: UUID = Field(..., description="Series unique identifier")
    current_page: int = Field(..., description="Current page number (0-indexed)")
    total_pages: int = Field(..., description="Total pages in chapter")
    progress_percentage: float = Field(..., description="Reading progress as percentage (0-100)")
    is_read: bool = Field(..., description="Whether chapter is marked as read")
    started_at: Optional[datetime] = Field(None, description="When reading started")
    read_at: Optional[datetime] = Field(None, description="When chapter was completed")
    updated_at: datetime = Field(..., description="Last progress update")

    model_config = ConfigDict(from_attributes=True)


class UserReadingStatsResponse(BaseModel):
    """Schema for user reading statistics."""

    total_series: int = Field(..., description="Total series in library")
    total_chapters: int = Field(..., description="Total chapters in library")
    read_chapters: int = Field(..., description="Number of read chapters")
    in_progress_chapters: int = Field(..., description="Chapters with partial progress")
    overall_progress_percentage: float = Field(..., description="Overall reading progress (0-100)")
    reading_streak_days: int = Field(..., description="Current reading streak in days")
    chapters_read_this_week: int = Field(..., description="Chapters read this week")
    chapters_read_this_month: int = Field(..., description="Chapters read this month")
    favorite_genres: List[str] = Field(default_factory=list, description="Most read genres")
    recent_activity: List[ChapterResponse] = Field(
        default_factory=list, description="Recent reading activity (up to 10)"
    )

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


# Annotation schemas
class AnnotationBase(BaseModel):
    """Base schema for annotation data."""

    content: str = Field(..., min_length=1, max_length=2000, description="Annotation content")
    page_number: Optional[int] = Field(None, ge=1, description="Page number (1-indexed)")
    annotation_type: str = Field(
        default="note", 
        description="Type of annotation (note, bookmark, highlight)"
    )
    position_x: Optional[float] = Field(
        None, ge=0, le=1, description="X position on page (0-1 normalized)"
    )
    position_y: Optional[float] = Field(
        None, ge=0, le=1, description="Y position on page (0-1 normalized)"
    )
    color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Annotation color in hex format"
    )

    @field_validator("annotation_type")
    @classmethod
    def validate_annotation_type(cls, v):
        """Validate annotation type is supported."""
        allowed_types = ["note", "bookmark", "highlight"]
        if v not in allowed_types:
            raise ValueError(f"Invalid annotation type. Must be one of: {allowed_types}")
        return v


class AnnotationCreate(AnnotationBase):
    """Schema for creating annotations."""

    chapter_id: UUID = Field(..., description="Chapter ID to annotate")


class AnnotationUpdate(BaseModel):
    """Schema for updating annotations."""

    content: Optional[str] = Field(
        None, min_length=1, max_length=2000, description="Annotation content"
    )
    page_number: Optional[int] = Field(None, ge=1, description="Page number (1-indexed)")
    annotation_type: Optional[str] = Field(
        None, description="Type of annotation (note, bookmark, highlight)"
    )
    position_x: Optional[float] = Field(
        None, ge=0, le=1, description="X position on page (0-1 normalized)"
    )
    position_y: Optional[float] = Field(
        None, ge=0, le=1, description="Y position on page (0-1 normalized)"
    )
    color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Annotation color in hex format"
    )

    @field_validator("annotation_type")
    @classmethod
    def validate_annotation_type(cls, v):
        """Validate annotation type is supported."""
        if v is not None:
            allowed_types = ["note", "bookmark", "highlight"]
            if v not in allowed_types:
                raise ValueError(f"Invalid annotation type. Must be one of: {allowed_types}")
        return v


class AnnotationResponse(AnnotationBase):
    """Schema for annotation responses."""

    id: UUID = Field(..., description="Annotation unique identifier")
    chapter_id: UUID = Field(..., description="Parent chapter ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional chapter information (when loaded with relationship)
    chapter: Optional[ChapterResponse] = Field(None, description="Parent chapter information")


# File Operation schemas
class FileOperationRequest(BaseModel):
    """Schema for file operation requests."""

    operation_type: str = Field(..., description="Type of operation (rename, delete, move)")
    source_path: str = Field(..., description="Source file/directory path")
    target_path: Optional[str] = Field(None, description="Target path (for rename/move operations)")
    
    # Safety options
    force: bool = Field(default=False, description="Force operation without confirmations")
    create_backup: bool = Field(default=True, description="Create backup before operation")
    
    # Validation options
    skip_validation: bool = Field(default=False, description="Skip pre-operation validation")
    validate_database_consistency: bool = Field(default=True, description="Validate database consistency")

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, v):
        """Validate operation type is supported."""
        allowed_types = ["rename", "delete", "move"]
        if v not in allowed_types:
            raise ValueError(f"Invalid operation type. Must be one of: {allowed_types}")
        return v

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, v):
        """Validate source path is not empty."""
        if not v or not v.strip():
            raise ValueError("Source path cannot be empty")
        return v.strip()

    @field_validator("target_path")
    @classmethod
    def validate_target_path(cls, v, info):
        """Validate target path for rename/move operations."""
        operation_type = info.data.get("operation_type")
        if operation_type in ["rename", "move"]:
            if not v or not v.strip():
                raise ValueError(f"Target path is required for {operation_type} operations")
            return v.strip()
        return v


class FileOperationResponse(BaseModel):
    """Schema for file operation responses."""

    id: UUID = Field(..., description="Operation ID")
    operation_type: str = Field(..., description="Type of operation")
    status: str = Field(..., description="Operation status")
    
    # File paths
    source_path: str = Field(..., description="Source path")
    target_path: Optional[str] = Field(None, description="Target path")
    backup_path: Optional[str] = Field(None, description="Backup path")
    
    # Affected records
    affected_series_ids: List[str] = Field(default_factory=list, description="Affected series IDs")
    affected_chapter_ids: List[str] = Field(default_factory=list, description="Affected chapter IDs")
    
    # Operation metadata
    operation_metadata: dict = Field(default_factory=dict, description="Operation metadata")
    validation_results: dict = Field(default_factory=dict, description="Validation results")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if operation failed")
    retry_count: int = Field(..., description="Number of retry attempts")
    max_retries: int = Field(..., description="Maximum retry attempts")
    
    # Timing
    started_at: Optional[datetime] = Field(None, description="Operation start time")
    completed_at: Optional[datetime] = Field(None, description="Operation completion time")
    validated_at: Optional[datetime] = Field(None, description="Validation completion time")
    
    # Timestamps
    created_at: datetime = Field(..., description="Operation creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, annotation, include_chapter: bool = False):
        """Create AnnotationResponse from Annotation model."""
        data = {
            "id": annotation.id,
            "chapter_id": annotation.chapter_id,
            "content": annotation.content,
            "page_number": annotation.page_number,
            "annotation_type": annotation.annotation_type,
            "position_x": getattr(annotation, "position_x", None),
            "position_y": getattr(annotation, "position_y", None),
            "color": getattr(annotation, "color", None),
            "created_at": annotation.created_at,
            "updated_at": annotation.updated_at,
        }

        # Include chapter if available and requested
        if include_chapter and hasattr(annotation, "chapter") and annotation.chapter:
            data["chapter"] = ChapterResponse.from_model(annotation.chapter)

        return cls(**data)


class AnnotationListResponse(BaseModel):
    """Schema for list of annotations."""

    annotations: List[AnnotationResponse] = Field(..., description="List of annotations")
    total: int = Field(..., description="Total number of annotations")
    chapter_id: Optional[UUID] = Field(None, description="Chapter ID filter applied")
    annotation_type: Optional[str] = Field(None, description="Annotation type filter applied")


class ChapterAnnotationsResponse(BaseModel):
    """Schema for chapter annotations response."""

    chapter_id: UUID = Field(..., description="Chapter unique identifier")
    chapter_title: str = Field(..., description="Chapter title")
    total_pages: int = Field(..., description="Total pages in chapter")
    annotations: List[AnnotationResponse] = Field(..., description="Chapter annotations")
    annotations_by_page: Dict[int, List[AnnotationResponse]] = Field(
        ..., description="Annotations grouped by page number"
    )

    @classmethod
    def from_chapter_and_annotations(cls, chapter, annotations):
        """Create response from chapter and annotations."""
        # Group annotations by page
        annotations_by_page = {}
        for annotation in annotations:
            page = annotation.page_number or 0
            if page not in annotations_by_page:
                annotations_by_page[page] = []
            annotations_by_page[page].append(AnnotationResponse.from_model(annotation))

        return cls(
            chapter_id=chapter.id,
            chapter_title=f"Chapter {chapter.chapter_number}" + (f" - {chapter.title}" if chapter.title else ""),
            total_pages=chapter.page_count,
            annotations=[AnnotationResponse.from_model(a) for a in annotations],
            annotations_by_page=annotations_by_page,
        )


# MangaDx integration schemas
class MangaDxSearchRequest(BaseModel):
    """Schema for MangaDx search requests."""
    
    title: Optional[str] = Field(None, description="Manga title to search for")
    author: Optional[str] = Field(None, description="Author name to search for")
    artist: Optional[str] = Field(None, description="Artist name to search for")
    year: Optional[int] = Field(None, ge=1900, le=2030, description="Publication year")
    status: Optional[List[str]] = Field(None, description="Publication status filter")
    content_rating: Optional[List[str]] = Field(None, description="Content rating filter")
    original_language: Optional[List[str]] = Field(None, description="Original language filter")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results (1-100)")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate publication status values."""
        if v is not None:
            allowed_statuses = ["ongoing", "completed", "hiatus", "cancelled"]
            for status in v:
                if status not in allowed_statuses:
                    raise ValueError(f"Invalid status '{status}'. Must be one of: {allowed_statuses}")
        return v
    
    @field_validator("content_rating")
    @classmethod
    def validate_content_rating(cls, v):
        """Validate content rating values."""
        if v is not None:
            allowed_ratings = ["safe", "suggestive", "erotica", "pornographic"]
            for rating in v:
                if rating not in allowed_ratings:
                    raise ValueError(f"Invalid content rating '{rating}'. Must be one of: {allowed_ratings}")
        return v


class MangaDxMangaInfo(BaseModel):
    """Schema for MangaDx manga information in search results."""
    
    id: str = Field(..., description="MangaDx manga UUID")
    title: str = Field(..., description="Primary manga title")
    alternative_titles: List[str] = Field(default_factory=list, description="Alternative titles")
    description: Optional[str] = Field(None, description="Manga description")
    author: Optional[str] = Field(None, description="Author name")
    artist: Optional[str] = Field(None, description="Artist name")
    genres: List[str] = Field(default_factory=list, description="Manga genres")
    tags: List[str] = Field(default_factory=list, description="Manga tags")
    status: str = Field(..., description="Publication status")
    content_rating: str = Field(..., description="Content rating")
    original_language: str = Field(..., description="Original language")
    publication_year: Optional[int] = Field(None, description="Publication year")
    last_volume: Optional[str] = Field(None, description="Last volume number")
    last_chapter: Optional[str] = Field(None, description="Last chapter number")
    cover_art_url: Optional[str] = Field(None, description="Cover art image URL")
    
    # MangaDx metadata
    mangadx_created_at: Optional[datetime] = Field(None, description="MangaDx creation timestamp")
    mangadx_updated_at: Optional[datetime] = Field(None, description="MangaDx update timestamp")


class MangaDxSearchResponse(BaseModel):
    """Schema for MangaDx search response."""
    
    results: List[MangaDxMangaInfo] = Field(default_factory=list, description="Search results")
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether there are more results")


class MangaDxImportRequest(BaseModel):
    """Schema for MangaDx metadata import requests."""
    
    mangadx_id: str = Field(..., description="MangaDx manga UUID to import")
    target_series_id: Optional[UUID] = Field(
        None, 
        description="Optional existing series ID to enrich with metadata"
    )
    import_cover_art: bool = Field(default=True, description="Whether to download cover art")
    import_chapters: bool = Field(default=False, description="Whether to import chapter metadata")
    overwrite_existing: bool = Field(
        default=False, 
        description="Whether to overwrite existing metadata fields"
    )
    custom_title: Optional[str] = Field(
        None, 
        description="Custom title override (if different from MangaDx)"
    )


class MangaDxImportResult(BaseModel):
    """Schema for MangaDx import operation result."""
    
    success: bool = Field(..., description="Whether import was successful")
    series_id: Optional[UUID] = Field(None, description="ID of created/updated series")
    mangadx_id: str = Field(..., description="MangaDx manga UUID that was imported")
    operation: str = Field(..., description="Operation performed (created/updated/enriched)")
    
    # Import statistics
    metadata_fields_updated: List[str] = Field(
        default_factory=list, 
        description="List of metadata fields that were updated"
    )
    cover_art_downloaded: bool = Field(default=False, description="Whether cover art was downloaded")
    chapters_imported: int = Field(default=0, description="Number of chapters imported")
    
    # Error information
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    errors: List[str] = Field(default_factory=list, description="Error messages if failed")
    
    # Timing information
    import_duration_ms: Optional[int] = Field(None, description="Import duration in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MangaDxImportResponse(BaseModel):
    """Schema for MangaDx import API response."""
    
    status: str = Field(..., description="Import status (success/partial/failed)")
    message: str = Field(..., description="Human-readable status message")
    result: MangaDxImportResult = Field(..., description="Detailed import result")


class MangaDxBulkImportRequest(BaseModel):
    """Schema for bulk MangaDx import requests."""
    
    import_requests: List[MangaDxImportRequest] = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="List of import requests (max 50)"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Job priority for background processing")
    notify_on_completion: bool = Field(
        default=True, 
        description="Whether to create notification job on completion"
    )


class MangaDxBulkImportResponse(BaseModel):
    """Schema for bulk MangaDx import response."""
    
    status: str = Field(..., description="Request status (scheduled/failed)")
    message: str = Field(..., description="Human-readable status message")
    job_id: Optional[UUID] = Field(None, description="Background job ID")
    import_count: int = Field(..., description="Number of imports scheduled")


class MangaDxEnrichmentRequest(BaseModel):
    """Schema for enriching existing series with MangaDx metadata."""
    
    series_id: UUID = Field(..., description="Local series ID to enrich")
    search_query: Optional[str] = Field(
        None, 
        description="Override search query (uses series title if not provided)"
    )
    auto_select_best_match: bool = Field(
        default=False, 
        description="Automatically select best match if confidence is high"
    )
    confidence_threshold: float = Field(
        default=0.8, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence for auto-selection (0.0-1.0)"
    )
    import_cover_art: bool = Field(default=True, description="Whether to download cover art")
    overwrite_existing: bool = Field(
        default=False, 
        description="Whether to overwrite existing metadata fields"
    )


class MangaDxEnrichmentCandidate(BaseModel):
    """Schema for MangaDx enrichment candidate."""
    
    mangadx_info: MangaDxMangaInfo = Field(..., description="MangaDx manga information")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence (0.0-1.0)")
    match_reasons: List[str] = Field(
        default_factory=list, 
        description="Reasons for this match (title, author, etc.)"
    )
    is_recommended: bool = Field(..., description="Whether this is the recommended match")


class MangaDxEnrichmentResponse(BaseModel):
    """Schema for MangaDx enrichment response."""
    
    series_id: UUID = Field(..., description="Local series ID")
    series_title: str = Field(..., description="Local series title")
    candidates: List[MangaDxEnrichmentCandidate] = Field(
        default_factory=list, 
        description="Potential MangaDx matches"
    )
    auto_selected: Optional[MangaDxEnrichmentCandidate] = Field(
        None, 
        description="Auto-selected candidate if confidence threshold met"
    )
    search_query_used: str = Field(..., description="Search query that was used")
    total_candidates: int = Field(..., description="Total number of candidates found")


class MangaDxHealthResponse(BaseModel):
    """Schema for MangaDx API health check response."""
    
    api_accessible: bool = Field(..., description="Whether MangaDx API is accessible")
    response_time_ms: Optional[int] = Field(None, description="API response time in milliseconds")
    last_check: datetime = Field(..., description="Last health check timestamp")
    error_message: Optional[str] = Field(None, description="Error message if health check failed")


    @classmethod
    def from_model(cls, operation):
        """Create FileOperationResponse from FileOperation model."""
        return cls(
            id=operation.id,
            operation_type=operation.operation_type,
            status=operation.status,
            source_path=operation.source_path,
            target_path=operation.target_path,
            backup_path=operation.backup_path,
            affected_series_ids=operation.affected_series_ids,
            affected_chapter_ids=operation.affected_chapter_ids,
            operation_metadata=operation.operation_metadata,
            validation_results=operation.validation_results,
            error_message=operation.error_message,
            retry_count=operation.retry_count,
            max_retries=operation.max_retries,
            started_at=operation.started_at,
            completed_at=operation.completed_at,
            validated_at=operation.validated_at,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )


class ValidationResult(BaseModel):
    """Schema for validation results."""

    is_valid: bool = Field(..., description="Whether the operation is valid")
    warnings: List[str] = Field(default_factory=list, description="Non-critical validation warnings")
    errors: List[str] = Field(default_factory=list, description="Critical validation errors")
    conflicts: List[dict] = Field(default_factory=list, description="Detected conflicts")
    
    # Affected data summary
    affected_series_count: int = Field(default=0, description="Number of affected series")
    affected_chapter_count: int = Field(default=0, description="Number of affected chapters")
    
    # Risk assessment
    risk_level: str = Field(default="low", description="Risk level (low, medium, high)")
    requires_confirmation: bool = Field(default=False, description="Whether user confirmation is required")
    
    # Performance impact
    estimated_duration_seconds: Optional[float] = Field(None, description="Estimated operation duration")
    estimated_disk_usage_mb: Optional[float] = Field(None, description="Estimated disk usage for backups")

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v):
        """Validate risk level."""
        allowed_levels = ["low", "medium", "high"]
        if v not in allowed_levels:
            raise ValueError(f"Invalid risk level. Must be one of: {allowed_levels}")
        return v


class FileOperationConfirmationRequest(BaseModel):
    """Schema for confirming a file operation after validation."""

    operation_id: UUID = Field(..., description="Operation ID to confirm")
    confirmed: bool = Field(..., description="User confirmation")
    confirmation_message: Optional[str] = Field(None, description="Optional confirmation message")


class FileOperationListResponse(BaseModel):
    """Schema for listing file operations."""

    operations: List[FileOperationResponse] = Field(..., description="List of operations")
    total: int = Field(..., description="Total number of operations")
    status_filter: Optional[str] = Field(None, description="Applied status filter")
    operation_type_filter: Optional[str] = Field(None, description="Applied operation type filter")


# Download Job schemas
class DownloadJobProgressInfo(BaseModel):
    """Schema for download job progress information."""
    
    total_chapters: int = Field(..., description="Total number of chapters to download")
    downloaded_chapters: int = Field(..., description="Number of chapters completed")
    current_chapter: Optional[Dict[str, Any]] = Field(None, description="Current chapter being downloaded")
    current_chapter_progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Current chapter progress (0.0-1.0)")
    error_count: int = Field(default=0, description="Number of chapters that failed to download")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="List of error details")
    started_at: Optional[str] = Field(None, description="Download start timestamp (ISO format)")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion timestamp (ISO format)")
    
    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_chapters == 0:
            return 0.0
        base_progress = self.downloaded_chapters / self.total_chapters
        current_contribution = self.current_chapter_progress / self.total_chapters if self.current_chapter else 0.0
        return min(100.0, (base_progress + current_contribution) * 100.0)
    
    @property
    def is_complete(self) -> bool:
        """Check if download is complete."""
        return self.downloaded_chapters >= self.total_chapters and not self.current_chapter


class DownloadJobRequest(BaseModel):
    """Schema for download job requests."""
    
    download_type: Literal["single", "batch", "series"] = Field(..., description="Type of download")
    manga_id: str = Field(..., description="External manga ID (MangaDx UUID)")
    
    # Chapter selection
    chapter_ids: Optional[List[str]] = Field(None, description="Specific chapter IDs to download (for single/batch)")
    volume_number: Optional[str] = Field(None, description="Volume number (for volume downloads)")
    
    # Local association
    series_id: Optional[UUID] = Field(None, description="Local series ID to associate with")
    
    # Download options
    destination_path: Optional[str] = Field(None, description="Custom destination path")
    priority: int = Field(default=3, ge=1, le=10, description="Job priority (1-10, higher = more urgent)")
    
    # Notification options
    notify_on_completion: bool = Field(default=True, description="Send notification when download completes")
    
    @field_validator("download_type")
    @classmethod
    def validate_download_type(cls, v):
        """Validate download type."""
        if v == "single" and not cls.chapter_ids:
            raise ValueError("Single download requires chapter_ids")
        elif v == "batch" and not cls.chapter_ids:
            raise ValueError("Batch download requires chapter_ids")
        return v


class DownloadJobResponse(BaseModel):
    """Schema for download job responses."""
    
    id: UUID = Field(..., description="Job unique identifier")
    job_type: str = Field(default="download", description="Job type")
    status: Literal["pending", "running", "completed", "failed"] = Field(..., description="Job status")
    
    # Download metadata
    download_type: str = Field(..., description="Type of download")
    manga_id: str = Field(..., description="External manga ID")
    series_id: Optional[UUID] = Field(None, description="Associated local series ID")
    batch_type: Optional[str] = Field(None, description="Batch type (single, multiple, volume, series)")
    volume_number: Optional[str] = Field(None, description="Volume number for volume downloads")
    destination_path: Optional[str] = Field(None, description="Download destination path")
    
    # Progress tracking
    progress: Optional[DownloadJobProgressInfo] = Field(None, description="Download progress information")
    
    # Job metadata
    priority: int = Field(..., description="Job priority")
    retry_count: int = Field(..., description="Number of retry attempts")
    max_retries: int = Field(..., description="Maximum retry attempts")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    
    # Timing
    scheduled_at: datetime = Field(..., description="Job scheduled time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    created_at: datetime = Field(..., description="Job creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    # Computed properties
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now(timezone.utc).replace(tzinfo=None)
        return (end_time - self.started_at).total_seconds()
    
    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time based on current progress."""
        if not self.progress or not self.started_at or self.progress.total_chapters == 0:
            return None
        
        if self.progress.is_complete:
            return 0.0
        
        elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - self.started_at).total_seconds()
        progress_ratio = self.progress.progress_percentage / 100.0
        
        if progress_ratio <= 0:
            return None
        
        total_estimated = elapsed / progress_ratio
        return max(0.0, total_estimated - elapsed)
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_job_model(cls, job: "JobQueue") -> "DownloadJobResponse":
        """Create DownloadJobResponse from JobQueue model."""
        payload = job.payload or {}
        
        # Extract progress information
        progress_data = payload.get("progress", {})
        progress = None
        if progress_data:
            progress = DownloadJobProgressInfo(**progress_data)
        
        return cls(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            download_type=payload.get("download_type", "mangadx"),
            manga_id=payload.get("manga_id", ""),
            series_id=UUID(payload["series_id"]) if payload.get("series_id") else None,
            batch_type=payload.get("batch_type"),
            volume_number=payload.get("volume_number"),
            destination_path=payload.get("destination_path"),
            progress=progress,
            priority=job.priority,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            error_message=job.error_message,
            scheduled_at=job.scheduled_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class DownloadJobListResponse(BaseModel):
    """Schema for listing download jobs."""
    
    jobs: List[DownloadJobResponse] = Field(..., description="List of download jobs")
    total: int = Field(..., description="Total number of jobs")
    active_downloads: int = Field(..., description="Number of currently active downloads")
    pending_downloads: int = Field(..., description="Number of pending downloads")
    failed_downloads: int = Field(..., description="Number of failed downloads")
    completed_downloads: int = Field(..., description="Number of completed downloads")
    
    # Filters applied
    status_filter: Optional[str] = Field(None, description="Applied status filter")
    download_type_filter: Optional[str] = Field(None, description="Applied download type filter")
    
    # Pagination info
    pagination: Optional[PaginationMeta] = Field(None, description="Pagination metadata")


class DownloadJobActionRequest(BaseModel):
    """Schema for download job actions (cancel, retry, etc.)."""
    
    action: Literal["cancel", "retry", "pause", "resume"] = Field(..., description="Action to perform")
    reason: Optional[str] = Field(None, description="Optional reason for the action")


class DownloadJobActionResponse(BaseModel):
    """Schema for download job action responses."""
    
    job_id: UUID = Field(..., description="Job ID that action was performed on")
    action: str = Field(..., description="Action that was performed")
    success: bool = Field(..., description="Whether action was successful")
    message: str = Field(..., description="Human-readable result message")
    new_status: Optional[str] = Field(None, description="New job status after action")


class DownloadStatsResponse(BaseModel):
    """Schema for download system statistics."""
    
    # Current queue status
    total_jobs: int = Field(..., description="Total number of download jobs")
    active_jobs: int = Field(..., description="Currently running jobs")
    pending_jobs: int = Field(..., description="Pending jobs in queue")
    failed_jobs: int = Field(..., description="Failed jobs")
    completed_jobs: int = Field(..., description="Successfully completed jobs")
    
    # Recent activity (last 24 hours)
    jobs_created_today: int = Field(..., description="Jobs created in last 24 hours")
    jobs_completed_today: int = Field(..., description="Jobs completed in last 24 hours")
    chapters_downloaded_today: int = Field(..., description="Chapters downloaded in last 24 hours")
    
    # System health
    average_job_duration_minutes: Optional[float] = Field(None, description="Average job duration in minutes")
    success_rate_percentage: float = Field(..., description="Overall success rate percentage")
    current_download_speed_mbps: Optional[float] = Field(None, description="Current download speed in Mbps")
    
    # Storage usage
    total_downloaded_size_gb: Optional[float] = Field(None, description="Total size of downloaded content in GB")
    available_storage_gb: Optional[float] = Field(None, description="Available storage space in GB")
    
    # Last updated
    stats_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkDownloadRequest(BaseModel):
    """Schema for bulk download requests."""
    
    downloads: List[DownloadJobRequest] = Field(
        ..., 
        min_length=1, 
        max_length=50, 
        description="List of download requests (max 50)"
    )
    global_priority: Optional[int] = Field(None, ge=1, le=10, description="Global priority override")
    batch_name: Optional[str] = Field(None, description="Optional name for the batch")
    stagger_delay_seconds: int = Field(default=5, ge=0, le=300, description="Delay between job starts (0-300s)")


class BulkDownloadResponse(BaseModel):
    """Schema for bulk download responses."""
    
    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Batch status (scheduled/partial/failed)")
    message: str = Field(..., description="Human-readable status message")
    total_requested: int = Field(..., description="Total number of downloads requested")
    successfully_queued: int = Field(..., description="Number of downloads successfully queued")
    failed_to_queue: int = Field(..., description="Number of downloads that failed to queue")
    job_ids: List[UUID] = Field(..., description="List of created job IDs")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed requests")
