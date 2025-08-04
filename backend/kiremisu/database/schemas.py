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
        None, description="Optional specific library path ID to scan. If not provided, scans all enabled paths"
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
            updated_at=job.updated_at
        )


class JobListResponse(BaseModel):
    """Schema for list of jobs."""
    
    jobs: List[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs returned")
    job_type_filter: Optional[str] = Field(None, description="Applied job type filter")


class JobScheduleRequest(BaseModel):
    """Schema for job scheduling requests."""
    
    job_type: str = Field(..., description="Type of job to schedule (library_scan, auto_schedule)")
    library_path_id: Optional[UUID] = Field(None, description="Optional specific library path ID for manual scans")
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
    skipped_count: Optional[int] = Field(None, description="Number of paths skipped (for auto scheduling)")
    total_paths: Optional[int] = Field(None, description="Total paths evaluated (for auto scheduling)")


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
