"""Library path service layer."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath
from kiremisu.database.schemas import LibraryPathCreate, LibraryPathUpdate


class LibraryPathService:
    """Service for managing library paths."""

    @staticmethod
    def _validate_and_sanitize_path(path: str) -> str:
        """
        Validate and sanitize a file system path for security.

        Protects against:
        - Directory traversal attacks (../, ..\\)
        - Invalid characters and names
        - Symlink attacks
        - Non-absolute paths

        Args:
            path: The path to validate

        Returns:
            The sanitized absolute path

        Raises:
            ValueError: If the path is invalid or unsafe
        """
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")

        # Remove any null bytes (security protection)
        if "\x00" in path:
            raise ValueError("Path contains null bytes")

        # Convert to Path object for normalization
        try:
            path_obj = Path(path).resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid path format: {e}")

        # Ensure path is absolute after resolution
        if not path_obj.is_absolute():
            raise ValueError("Path must be absolute")

        # Get the normalized string representation
        normalized_path = str(path_obj)

        # Additional security checks
        dangerous_patterns = ["..", "\\.\\", "/./", "\0", "\r", "\n"]

        for pattern in dangerous_patterns:
            if pattern in normalized_path:
                raise ValueError(f"Path contains dangerous pattern: {pattern}")

        # Check for reserved names on Windows
        if os.name == "nt":
            reserved_names = {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                "COM1",
                "COM2",
                "COM3",
                "COM4",
                "COM5",
                "COM6",
                "COM7",
                "COM8",
                "COM9",
                "LPT1",
                "LPT2",
                "LPT3",
                "LPT4",
                "LPT5",
                "LPT6",
                "LPT7",
                "LPT8",
                "LPT9",
            }
            path_parts = path_obj.parts
            for part in path_parts:
                if part.upper().split(".")[0] in reserved_names:
                    raise ValueError(f"Path contains reserved Windows name: {part}")

        # Ensure the path doesn't try to escape to system directories
        # This is a basic protection - adjust based on your deployment environment
        system_dirs = ["/etc", "/sys", "/proc", "/dev", "/root"]
        if os.name != "nt":
            for sys_dir in system_dirs:
                if normalized_path.startswith(sys_dir):
                    raise ValueError(f"Access to system directory not allowed: {sys_dir}")

        return normalized_path

    @staticmethod
    async def get_all(db: AsyncSession) -> List[LibraryPath]:
        """Get all library paths."""
        result = await db.execute(select(LibraryPath).order_by(LibraryPath.created_at))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, path_id: UUID) -> Optional[LibraryPath]:
        """Get library path by ID."""
        result = await db.execute(select(LibraryPath).where(LibraryPath.id == path_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_path(db: AsyncSession, path: str) -> Optional[LibraryPath]:
        """Get library path by path string."""
        result = await db.execute(select(LibraryPath).where(LibraryPath.path == path))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, library_path_data: LibraryPathCreate) -> LibraryPath:
        """Create a new library path."""
        # Validate and sanitize the path for security
        sanitized_path = LibraryPathService._validate_and_sanitize_path(library_path_data.path)

        # Validate path exists and is accessible
        if not os.path.exists(sanitized_path):
            raise ValueError(f"Path does not exist: {sanitized_path}")

        if not os.path.isdir(sanitized_path):
            raise ValueError(f"Path is not a directory: {sanitized_path}")

        if not os.access(sanitized_path, os.R_OK):
            raise ValueError(f"Path is not readable: {sanitized_path}")

        # Check if path already exists
        existing = await LibraryPathService.get_by_path(db, sanitized_path)
        if existing:
            raise ValueError(f"Path already exists: {sanitized_path}")

        library_path = LibraryPath(
            path=sanitized_path,
            enabled=library_path_data.enabled,
            scan_interval_hours=library_path_data.scan_interval_hours,
        )

        db.add(library_path)
        await db.flush()
        await db.refresh(library_path)
        return library_path

    @staticmethod
    async def update(
        db: AsyncSession, path_id: UUID, update_data: LibraryPathUpdate
    ) -> Optional[LibraryPath]:
        """Update an existing library path."""
        library_path = await LibraryPathService.get_by_id(db, path_id)
        if not library_path:
            return None

        # Validate new path if provided
        sanitized_new_path = None
        if update_data.path and update_data.path != library_path.path:
            # Validate and sanitize the new path for security
            sanitized_new_path = LibraryPathService._validate_and_sanitize_path(update_data.path)

            if not os.path.exists(sanitized_new_path):
                raise ValueError(f"Path does not exist: {sanitized_new_path}")

            if not os.path.isdir(sanitized_new_path):
                raise ValueError(f"Path is not a directory: {sanitized_new_path}")

            if not os.access(sanitized_new_path, os.R_OK):
                raise ValueError(f"Path is not readable: {sanitized_new_path}")

            # Check if new path already exists
            existing = await LibraryPathService.get_by_path(db, sanitized_new_path)
            if existing and existing.id != path_id:
                raise ValueError(f"Path already exists: {sanitized_new_path}")

        # Update fields
        if sanitized_new_path is not None:
            library_path.path = sanitized_new_path
        if update_data.enabled is not None:
            library_path.enabled = update_data.enabled
        if update_data.scan_interval_hours is not None:
            library_path.scan_interval_hours = update_data.scan_interval_hours

        library_path.updated_at = datetime.utcnow()

        await db.flush()
        await db.refresh(library_path)
        return library_path

    @staticmethod
    async def delete(db: AsyncSession, path_id: UUID) -> bool:
        """Delete a library path."""
        library_path = await LibraryPathService.get_by_id(db, path_id)
        if not library_path:
            return False

        await db.delete(library_path)
        await db.flush()
        return True

    @staticmethod
    async def get_enabled_paths(db: AsyncSession) -> List[LibraryPath]:
        """Get all enabled library paths."""
        result = await db.execute(
            select(LibraryPath).where(LibraryPath.enabled == True).order_by(LibraryPath.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_last_scan(db: AsyncSession, path_id: UUID) -> Optional[LibraryPath]:
        """Update the last scan timestamp for a library path."""
        library_path = await LibraryPathService.get_by_id(db, path_id)
        if not library_path:
            return None

        library_path.last_scan = datetime.utcnow()
        library_path.updated_at = datetime.utcnow()

        await db.flush()
        await db.refresh(library_path)
        return library_path
