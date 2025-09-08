"""Service layer for storage path management."""

import os
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func

from app.models.storage_path import StoragePath
from app.schemas.storage import (
    StoragePathCreate,
    StoragePathUpdate,
    StoragePathValidationResult,
    StoragePathStats,
    BulkOperationResult
)

logger = logging.getLogger(__name__)


class StoragePathService:
    """Service for managing storage paths."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, path_id: int) -> Optional[StoragePath]:
        """Get storage path by ID."""
        result = await self.db.execute(select(StoragePath).where(StoragePath.id == path_id))
        return result.scalars().first()

    async def get_by_path(self, path: str) -> Optional[StoragePath]:
        """Get storage path by filesystem path."""
        normalized_path = os.path.normpath(path)
        result = await self.db.execute(select(StoragePath).where(StoragePath.path == normalized_path))
        return result.scalars().first()

    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = False,
        accessible_only: bool = False
    ) -> List[StoragePath]:
        """Get all storage paths with optional filters."""
        query = select(StoragePath)
        
        if active_only:
            query = query.where(StoragePath.is_active.is_(True))
        if accessible_only:
            query = query.where(StoragePath.is_accessible.is_(True))
        
        query = query.order_by(StoragePath.priority.desc(), StoragePath.created_at).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(self, active_only: bool = False, accessible_only: bool = False) -> int:
        """Count storage paths with optional filters."""
        query = select(func.count(StoragePath.id))
        
        if active_only:
            query = query.where(StoragePath.is_active.is_(True))
        if accessible_only:
            query = query.where(StoragePath.is_accessible.is_(True))
        
        result = await self.db.execute(query)
        return result.scalar()

    async def create(self, storage_path_data: StoragePathCreate) -> StoragePath:
        """Create a new storage path."""
        # Check if path already exists
        existing = await self.get_by_path(storage_path_data.path)
        if existing:
            raise ValueError(f"Storage path already exists: {storage_path_data.path}")

        # Create new storage path
        storage_path = StoragePath(**storage_path_data.dict())
        
        # Validate the path on creation
        validation_result = self.validate_path(storage_path_data.path)
        storage_path.is_accessible = validation_result.is_accessible
        storage_path.validation_error = validation_result.error_message
        storage_path.last_validated_at = datetime.now(timezone.utc)
        
        # Update space information if accessible
        if validation_result.is_accessible:
            storage_path.total_space_bytes = validation_result.total_space_bytes
            storage_path.used_space_bytes = validation_result.used_space_bytes

        self.db.add(storage_path)
        await self.db.commit()
        await self.db.refresh(storage_path)
        
        logger.info(f"Created storage path: {storage_path.name} -> {storage_path.path}")
        return storage_path

    async def update(self, path_id: int, update_data: StoragePathUpdate) -> Optional[StoragePath]:
        """Update a storage path."""
        storage_path = await self.get_by_id(path_id)
        if not storage_path:
            return None

        # Apply updates
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(storage_path, field, value)
        
        storage_path.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(storage_path)
        
        logger.info(f"Updated storage path: {storage_path.name} (ID: {path_id})")
        return storage_path

    async def delete(self, path_id: int) -> bool:
        """Delete a storage path."""
        storage_path = await self.get_by_id(path_id)
        if not storage_path:
            return False

        await self.db.delete(storage_path)
        await self.db.commit()
        
        logger.info(f"Deleted storage path: {storage_path.name} (ID: {path_id})")
        return True

    def validate_path(self, path: str) -> StoragePathValidationResult:
        """Validate a storage path for accessibility and permissions."""
        normalized_path = os.path.normpath(path)
        result = StoragePathValidationResult(
            path=normalized_path,
            is_valid=False,
            is_accessible=False,
            exists=False,
            is_readable=False,
            is_writable=False,
            is_network=False
        )
        
        try:
            # Check if path exists
            path_obj = Path(normalized_path)
            result.exists = path_obj.exists()
            
            if not result.exists:
                result.error_message = "Path does not exist"
                return result
            
            # Check if it's a directory
            if not path_obj.is_dir():
                result.error_message = "Path is not a directory"
                return result
            
            # Check permissions
            result.is_readable = os.access(normalized_path, os.R_OK)
            result.is_writable = os.access(normalized_path, os.W_OK)
            
            if not result.is_readable:
                result.error_message = "Path is not readable"
                return result
            
            # Check if it's network storage (basic heuristic)
            result.is_network = self._is_network_path(normalized_path)
            
            # Get disk usage statistics
            try:
                disk_usage = shutil.disk_usage(normalized_path)
                result.total_space_bytes = disk_usage.total
                result.free_space_bytes = disk_usage.free
                result.used_space_bytes = disk_usage.total - disk_usage.free
            except Exception as e:
                logger.warning(f"Failed to get disk usage for {normalized_path}: {e}")
            
            # Path is accessible if we made it this far
            result.is_accessible = True
            result.is_valid = True
            
        except PermissionError:
            result.error_message = "Permission denied accessing path"
        except OSError as e:
            result.error_message = f"System error accessing path: {str(e)}"
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error validating path {normalized_path}: {e}")
        
        return result

    async def revalidate_path(self, path_id: int) -> Optional[StoragePath]:
        """Revalidate a storage path and update its status."""
        storage_path = await self.get_by_id(path_id)
        if not storage_path:
            return None

        validation_result = self.validate_path(storage_path.path)
        
        # Update validation status
        storage_path.is_accessible = validation_result.is_accessible
        storage_path.validation_error = validation_result.error_message
        storage_path.last_validated_at = datetime.now(timezone.utc)
        
        # Update space information if accessible
        if validation_result.is_accessible:
            storage_path.total_space_bytes = validation_result.total_space_bytes
            storage_path.used_space_bytes = validation_result.used_space_bytes
        
        await self.db.commit()
        await self.db.refresh(storage_path)
        
        logger.info(f"Revalidated storage path: {storage_path.name} -> accessible: {validation_result.is_accessible}")
        return storage_path

    async def get_stats(self) -> StoragePathStats:
        """Get overall storage path statistics."""
        # Get basic counts
        total_query = select(func.count(StoragePath.id))
        active_query = select(func.count(StoragePath.id)).where(StoragePath.is_active.is_(True))
        network_query = select(func.count(StoragePath.id)).where(StoragePath.is_network.is_(True))
        accessible_query = select(func.count(StoragePath.id)).where(StoragePath.is_accessible.is_(True))
        
        total_result = await self.db.execute(total_query)
        active_result = await self.db.execute(active_query)
        network_result = await self.db.execute(network_query)
        accessible_result = await self.db.execute(accessible_query)
        
        total_paths = total_result.scalar()
        active_paths = active_result.scalar()
        network_paths = network_result.scalar()
        accessible_paths = accessible_result.scalar()
        
        # Aggregate space and file statistics
        accessible_query = select(StoragePath).where(
            and_(StoragePath.is_accessible.is_(True), StoragePath.is_active.is_(True))
        )
        accessible_result = await self.db.execute(accessible_query)
        accessible_storage_paths = accessible_result.scalars().all()
        
        total_space_bytes = 0
        used_space_bytes = 0
        total_files = 0
        total_series = 0
        
        for sp in accessible_storage_paths:
            if sp.total_space_bytes:
                total_space_bytes += sp.total_space_bytes
            if sp.used_space_bytes:
                used_space_bytes += sp.used_space_bytes
            total_files += sp.file_count
            total_series += sp.series_count
        
        return StoragePathStats(
            total_paths=total_paths,
            active_paths=active_paths,
            network_paths=network_paths,
            accessible_paths=accessible_paths,
            total_space_bytes=total_space_bytes if total_space_bytes > 0 else None,
            used_space_bytes=used_space_bytes if used_space_bytes > 0 else None,
            total_files=total_files,
            total_series=total_series
        )

    async def bulk_operation(self, path_ids: List[int], operation: str) -> BulkOperationResult:
        """Perform bulk operation on multiple storage paths."""
        result = BulkOperationResult(
            operation=operation,
            total_requested=len(path_ids),
            successful=0,
            failed=0
        )
        
        for path_id in path_ids:
            try:
                if operation == "activate":
                    success = await self._activate_path(path_id)
                elif operation == "deactivate":
                    success = await self._deactivate_path(path_id)
                elif operation == "validate":
                    success = await self._validate_path_bulk(path_id)
                elif operation == "delete":
                    success = await self.delete(path_id)
                else:
                    success = False
                    result.errors[path_id] = f"Unknown operation: {operation}"
                
                if success:
                    result.successful += 1
                    result.results[path_id] = {"success": True}
                else:
                    result.failed += 1
                    if path_id not in result.errors:
                        result.errors[path_id] = "Operation failed"
                        
            except Exception as e:
                result.failed += 1
                result.errors[path_id] = str(e)
                logger.error(f"Bulk operation {operation} failed for path {path_id}: {e}")
        
        return result

    async def _activate_path(self, path_id: int) -> bool:
        """Activate a storage path."""
        storage_path = await self.get_by_id(path_id)
        if not storage_path:
            return False
        
        storage_path.is_active = True
        storage_path.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def _deactivate_path(self, path_id: int) -> bool:
        """Deactivate a storage path."""
        storage_path = await self.get_by_id(path_id)
        if not storage_path:
            return False
        
        storage_path.is_active = False
        storage_path.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def _validate_path_bulk(self, path_id: int) -> bool:
        """Validate a path as part of bulk operation."""
        result = await self.revalidate_path(path_id)
        return result is not None

    def _is_network_path(self, path: str) -> bool:
        """Determine if a path is on network storage (basic heuristic)."""
        try:
            # Windows network paths
            if os.name == 'nt' and (path.startswith('\\\\') or path.startswith('//')):
                return True
            
            # Unix network mount detection
            if os.name == 'posix':
                # Check if path is on a network filesystem
                try:
                    stat = os.statvfs(path)
                    # Some network filesystems have specific signatures
                    # This is a basic heuristic and may need adjustment
                    fstype = getattr(stat, 'f_type', None)
                    if fstype and fstype in [0x6969, 0x564c]:  # NFS, CIFS magic numbers
                        return True
                except (OSError, AttributeError):
                    pass
            
            return False
        except Exception:
            return False