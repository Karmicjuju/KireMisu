"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
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
