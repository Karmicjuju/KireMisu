"""
Filesystem browsing API endpoints with enhanced security.
"""

import os
import logging
import re
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, validator

# Security logging setup
security_logger = logging.getLogger("kiremisu.security.filesystem")
security_logger.setLevel(logging.INFO)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])

# Security constants
MANGA_STORAGE_BASE = Path("/manga-storage").resolve()
MAX_PATH_LENGTH = 4096
MAX_ITEMS_PER_PAGE = 1000
DEFAULT_PAGE_SIZE = 100

# Dangerous path patterns
DANGEROUS_PATTERNS = [
    r"\.\./",  # Path traversal
    r"\.\.\\",  # Windows path traversal
    r"%2e%2e",  # URL encoded ..
    r"%252e%252e",  # Double URL encoded ..
    r"\.{2,}",  # Multiple dots
    r'[<>:"|?*]',  # Windows forbidden characters
    r"[\x00-\x1f]",  # Control characters
]


class DirectoryItem(BaseModel):
    """A filesystem item (file or directory)."""

    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[int] = None


class DirectoryListing(BaseModel):
    """Response for directory listing."""

    current_path: str
    parent_path: Optional[str]
    items: List[DirectoryItem]
    total_items: int
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    has_more: bool = False


def validate_path_input(path: str, client_ip: str = "unknown") -> None:
    """
    Comprehensive path input validation.

    Args:
        path: The path to validate
        client_ip: Client IP for security logging

    Raises:
        HTTPException: If path is invalid
    """
    # Log access attempt
    security_logger.info(f"Path access attempt: path='{path}' client_ip='{client_ip}'")

    # Check path length
    if len(path) > MAX_PATH_LENGTH:
        security_logger.warning(f"Path too long: length={len(path)} client_ip='{client_ip}'")
        raise HTTPException(
            status_code=400,
            detail=f"Path too long. Maximum length is {MAX_PATH_LENGTH} characters.",
        )

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            security_logger.warning(
                f"Dangerous pattern detected: pattern='{pattern}' path='{path}' client_ip='{client_ip}'"
            )
            raise HTTPException(status_code=400, detail="Invalid path format detected.")


def validate_path_security(requested_path: Path, client_ip: str = "unknown") -> Path:
    """
    Enhanced security validation using os.path.commonpath().

    Args:
        requested_path: The resolved path to validate
        client_ip: Client IP for security logging

    Returns:
        Path: The validated path

    Raises:
        HTTPException: If path is outside allowed area
    """
    try:
        # Use os.path.commonpath for robust validation
        common_path = Path(os.path.commonpath([str(MANGA_STORAGE_BASE), str(requested_path)]))

        if common_path != MANGA_STORAGE_BASE:
            security_logger.error(
                f"Path traversal attempt blocked: requested='{requested_path}' "
                f"base='{MANGA_STORAGE_BASE}' common='{common_path}' client_ip='{client_ip}'"
            )
            raise HTTPException(
                status_code=403, detail="Access denied. Path is outside allowed directory."
            )

        # Additional verification - ensure path starts with base
        if not str(requested_path).startswith(str(MANGA_STORAGE_BASE)):
            security_logger.error(
                f"Path prefix validation failed: requested='{requested_path}' "
                f"base='{MANGA_STORAGE_BASE}' client_ip='{client_ip}'"
            )
            raise HTTPException(
                status_code=403, detail="Access denied. Path is outside allowed directory."
            )

        security_logger.info(
            f"Path validation successful: path='{requested_path}' client_ip='{client_ip}'"
        )
        return requested_path

    except ValueError as e:
        security_logger.error(
            f"Path validation error: {str(e)} requested='{requested_path}' client_ip='{client_ip}'"
        )
        raise HTTPException(status_code=403, detail="Access denied. Invalid path structure.")


@router.get("/browse", response_model=DirectoryListing)
async def browse_directory(
    request: Request,
    path: str = Query("/manga-storage", description="Directory path to browse"),
    show_hidden: bool = Query(False, description="Show hidden files and directories"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_ITEMS_PER_PAGE, description="Items per page"
    ),
) -> DirectoryListing:
    """
    Browse manga storage directories with enhanced security and pagination.

    Security features:
    - Comprehensive input validation and sanitization
    - os.path.commonpath() validation to prevent path traversal
    - Security audit logging
    - Information disclosure reduction
    - Pagination for large directories
    """
    client_ip = get_client_ip(request)

    try:
        # Input validation
        validate_path_input(path, client_ip)

        # Normalize and resolve the requested path
        requested_path = Path(path).resolve()

        # Enhanced security validation
        validated_path = validate_path_security(requested_path, client_ip)

        # Check if directory exists and is accessible
        if not validated_path.exists():
            security_logger.info(
                f"Directory not found: path='{validated_path}' client_ip='{client_ip}'"
            )
            raise HTTPException(status_code=404, detail="Directory not found")

        if not validated_path.is_dir():
            security_logger.warning(
                f"Path is not directory: path='{validated_path}' client_ip='{client_ip}'"
            )
            raise HTTPException(status_code=400, detail="Path is not a directory")

        if not os.access(validated_path, os.R_OK):
            security_logger.warning(
                f"Directory not readable: path='{validated_path}' client_ip='{client_ip}'"
            )
            raise HTTPException(status_code=403, detail="Directory is not readable")

        # Get parent directory (only if it's still within manga storage)
        parent_path = None
        if validated_path.parent != validated_path and validated_path != MANGA_STORAGE_BASE:
            try:
                parent_validated = validate_path_security(validated_path.parent, client_ip)
                parent_path = str(parent_validated)
            except HTTPException:
                # Parent is outside manga storage, don't provide it
                pass

        # List directory contents with pagination
        all_items = []
        try:
            for item in validated_path.iterdir():
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith("."):
                    continue

                try:
                    stat_info = item.stat()
                    # Limit exposed metadata for security
                    all_items.append(
                        DirectoryItem(
                            name=item.name,
                            path=str(item),
                            is_directory=item.is_dir(),
                            size=stat_info.st_size if item.is_file() else None,
                            modified=int(stat_info.st_mtime),
                        )
                    )
                except (OSError, PermissionError):
                    # Skip items we can't access, don't log for security
                    continue

        except PermissionError:
            security_logger.warning(
                f"Permission denied listing: path='{validated_path}' client_ip='{client_ip}'"
            )
            raise HTTPException(status_code=403, detail="Permission denied")

        # Sort items: directories first, then files, both alphabetically
        all_items.sort(key=lambda x: (not x.is_directory, x.name.lower()))

        # Implement pagination
        total_items = len(all_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = all_items[start_idx:end_idx]
        has_more = end_idx < total_items

        # Log successful access
        security_logger.info(
            f"Directory access successful: path='{validated_path}' "
            f"items={len(paginated_items)} page={page} client_ip='{client_ip}'"
        )

        return DirectoryListing(
            current_path=str(validated_path),
            parent_path=parent_path,
            items=paginated_items,
            total_items=total_items,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    except HTTPException:
        raise
    except Exception as e:
        security_logger.error(
            f"Unexpected error in browse_directory: {str(e)} path='{path}' client_ip='{client_ip}'"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/validate-path")
async def validate_path(
    request: Request, path: str = Query(..., description="Path to validate")
) -> dict:
    """
    Validate if a path exists and is a directory within manga storage.
    Enhanced with security logging and comprehensive validation.
    """
    client_ip = get_client_ip(request)

    try:
        # Input validation
        validate_path_input(path, client_ip)

        # Normalize and resolve the requested path
        requested_path = Path(path).resolve()

        # Enhanced security validation
        validated_path = validate_path_security(requested_path, client_ip)

        result = {
            "exists": validated_path.exists(),
            "is_directory": validated_path.is_dir() if validated_path.exists() else False,
            "readable": os.access(validated_path, os.R_OK) if validated_path.exists() else False,
            "path": str(validated_path),
        }

        security_logger.info(
            f"Path validation successful: path='{validated_path}' "
            f"exists={result['exists']} is_dir={result['is_directory']} client_ip='{client_ip}'"
        )

        return result

    except HTTPException as e:
        # Return safe error response without exposing details
        return {
            "exists": False,
            "is_directory": False,
            "readable": False,
            "error": "Invalid path",
            "path": path,
        }
    except Exception as e:
        security_logger.error(
            f"Unexpected error in validate_path: {str(e)} path='{path}' client_ip='{client_ip}'"
        )
        return {
            "exists": False,
            "is_directory": False,
            "readable": False,
            "error": "Validation failed",
            "path": path,
        }
