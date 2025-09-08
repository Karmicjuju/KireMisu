"""Pydantic schemas for storage path management."""

from datetime import datetime
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, validator
import os
import re
from enum import Enum


class StoragePathBase(BaseModel):
    """Base schema for storage path."""
    
    name: str = Field(..., min_length=1, max_length=255, description="User-friendly name for the storage path")
    path: str = Field(..., min_length=1, max_length=500, description="Filesystem path to the storage location")
    is_active: bool = Field(default=True, description="Whether the storage path is active")
    is_network: bool = Field(default=False, description="Whether this is network-mounted storage")
    priority: int = Field(default=0, ge=0, le=100, description="Scan priority (higher values scanned first)")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate storage path name."""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        # Prevent potentially dangerous names
        if v.lower() in ["system", "root", "admin", "..", "."]:
            raise ValueError("Reserved name not allowed")
        return v

    @validator("path")
    def validate_path(cls, v: str) -> str:
        """Validate and normalize storage path."""
        v = v.strip()
        if not v:
            raise ValueError("Path cannot be empty")
        
        # Normalize path separators and resolve
        normalized_path = os.path.normpath(v)
        
        # Security: Block obviously dangerous paths
        dangerous_patterns = [
            r"\.\.[\\/]",  # Path traversal
            r"^[\\/]etc[\\/]",  # System directories
            r"^[\\/]proc[\\/]",
            r"^[\\/]sys[\\/]",
            r"^[\\/]dev[\\/]",
            r"^[\\/]root[\\/]",
            r"^C:[\\/]Windows[\\/]",  # Windows system
            r"^C:[\\/]Program Files",
        ]
        
        for pattern in dangerous_patterns:
            if re.match(pattern, normalized_path, re.IGNORECASE):
                raise ValueError("Path points to system directory")
        
        return normalized_path

    @validator("extra_metadata")
    def validate_extra_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extra_metadata doesn't contain sensitive information."""
        if not isinstance(v, dict):
            return {}
        
        # Remove any keys that might contain sensitive data
        sensitive_keys = ["password", "token", "secret", "key", "auth"]
        cleaned = {k: val for k, val in v.items() if not any(s in k.lower() for s in sensitive_keys)}
        
        # Limit metadata size
        if len(str(cleaned)) > 10000:  # 10KB limit
            raise ValueError("Metadata too large")
        
        return cleaned


class StoragePathCreate(StoragePathBase):
    """Schema for creating a new storage path."""
    pass


class StoragePathUpdate(BaseModel):
    """Schema for updating a storage path."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    is_network: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    extra_metadata: Optional[Dict[str, Any]] = None

    @validator("name", pre=True, always=True)
    def validate_name_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Validate name if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
            if v.lower() in ["system", "root", "admin", "..", "."]:
                raise ValueError("Reserved name not allowed")
        return v

    @validator("extra_metadata", pre=True, always=True)
    def validate_extra_metadata_if_provided(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate extra_metadata if provided."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("Extra metadata must be a dictionary")
            
            # Remove sensitive keys
            sensitive_keys = ["password", "token", "secret", "key", "auth"]
            cleaned = {k: val for k, val in v.items() if not any(s in k.lower() for s in sensitive_keys)}
            
            # Limit metadata size
            if len(str(cleaned)) > 10000:
                raise ValueError("Metadata too large")
            
            return cleaned
        return v


class StoragePathResponse(StoragePathBase):
    """Schema for storage path response."""
    
    id: int
    
    # Storage metrics
    total_space_bytes: Optional[int] = None
    used_space_bytes: Optional[int] = None
    file_count: int = 0
    series_count: int = 0
    
    # Validation status
    is_accessible: bool = False
    last_validated_at: Optional[datetime] = None
    validation_error: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_scanned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StoragePathValidationResult(BaseModel):
    """Schema for path validation results."""
    
    path: str
    is_valid: bool
    is_accessible: bool
    exists: bool
    is_readable: bool
    is_writable: bool
    is_network: bool
    error_message: Optional[str] = None
    total_space_bytes: Optional[int] = None
    free_space_bytes: Optional[int] = None
    used_space_bytes: Optional[int] = None


class StoragePathStats(BaseModel):
    """Schema for storage path statistics."""
    
    total_paths: int
    active_paths: int
    network_paths: int
    accessible_paths: int
    total_space_bytes: Optional[int] = None
    used_space_bytes: Optional[int] = None
    total_files: int = 0
    total_series: int = 0


class BulkStoragePathOperation(BaseModel):
    """Schema for bulk operations on storage paths."""
    
    path_ids: list[int] = Field(..., min_items=1, max_items=100)
    operation: str = Field(..., pattern="^(activate|deactivate|validate|delete)$")


class BulkOperationResult(BaseModel):
    """Schema for bulk operation results."""
    
    operation: str
    total_requested: int
    successful: int
    failed: int
    errors: Dict[int, str] = Field(default_factory=dict)  # path_id -> error_message
    results: Dict[int, Any] = Field(default_factory=dict)  # path_id -> result_data


# File Format Detection Schemas

class SupportedFormatEnum(str, Enum):
    """Supported manga file formats."""
    CBZ = "cbz"
    CBR = "cbr"
    PDF = "pdf"
    ZIP = "zip"
    RAR = "rar"
    FOLDER = "folder"


class FileFormatInfo(BaseModel):
    """Schema for file format detection results."""
    
    path: str
    format_type: Optional[SupportedFormatEnum] = None
    is_supported: bool = False
    is_valid: bool = False
    is_corrupted: bool = False
    file_size: int = 0
    page_count: Optional[int] = None
    has_images: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FileFormatValidationRequest(BaseModel):
    """Schema for file format validation request."""
    
    file_paths: List[str] = Field(..., min_items=1, max_items=100, description="List of file/directory paths to validate")


class FileFormatValidationResponse(BaseModel):
    """Schema for file format validation response."""
    
    total_files: int
    supported_files: int
    unsupported_files: int
    corrupted_files: int
    results: List[FileFormatInfo]


class SupportedFormatInfo(BaseModel):
    """Schema for supported format information."""
    
    format: str
    name: str
    description: str
    extensions: List[str]
    validation_level: str  # "full", "basic", "none"


# Library Scan Schemas

class LibraryScanRequest(BaseModel):
    """Schema for library scan request."""
    
    storage_path_ids: Optional[List[int]] = Field(
        None,
        description="List of storage path IDs to scan. If null, scans all active paths."
    )
    full_scan: bool = Field(
        default=False,
        description="If true, performs a full rescan ignoring last scan times."
    )


class ScanProgressResponse(BaseModel):
    """Schema for scan progress response."""
    
    scan_id: str
    status: str  # "running", "completed", "failed", "cancelled"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    file_stats: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


class LibraryScanResponse(BaseModel):
    """Schema for library scan initiation response."""
    
    scan_id: str
    message: str
    status: str