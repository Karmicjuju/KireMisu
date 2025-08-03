"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional
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
