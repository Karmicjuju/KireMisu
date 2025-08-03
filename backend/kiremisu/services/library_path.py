"""Library path service layer."""

import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath
from kiremisu.database.schemas import LibraryPathCreate, LibraryPathUpdate


class LibraryPathService:
    """Service for managing library paths."""

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
        # Validate path exists and is accessible
        if not os.path.exists(library_path_data.path):
            raise ValueError(f"Path does not exist: {library_path_data.path}")

        if not os.path.isdir(library_path_data.path):
            raise ValueError(f"Path is not a directory: {library_path_data.path}")

        if not os.access(library_path_data.path, os.R_OK):
            raise ValueError(f"Path is not readable: {library_path_data.path}")

        # Check if path already exists
        existing = await LibraryPathService.get_by_path(db, library_path_data.path)
        if existing:
            raise ValueError(f"Path already exists: {library_path_data.path}")

        library_path = LibraryPath(
            path=library_path_data.path,
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
        if update_data.path and update_data.path != library_path.path:
            if not os.path.exists(update_data.path):
                raise ValueError(f"Path does not exist: {update_data.path}")

            if not os.path.isdir(update_data.path):
                raise ValueError(f"Path is not a directory: {update_data.path}")

            if not os.access(update_data.path, os.R_OK):
                raise ValueError(f"Path is not readable: {update_data.path}")

            # Check if new path already exists
            existing = await LibraryPathService.get_by_path(db, update_data.path)
            if existing and existing.id != path_id:
                raise ValueError(f"Path already exists: {update_data.path}")

        # Update fields
        if update_data.path is not None:
            library_path.path = update_data.path
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
