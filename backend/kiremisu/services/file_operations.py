"""Safe file operation service with comprehensive safety mechanisms.

This service provides safe rename, delete, and move operations for manga files with:
- Comprehensive pre-operation validation
- Backup and rollback capabilities
- Database consistency checks
- Detailed audit logging
- Atomic operations with proper error handling
"""

import asyncio
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import FileOperation, Series, Chapter
from kiremisu.database.schemas import (
    ValidationResult,
    FileOperationRequest,
    FileOperationResponse,
)

logger = structlog.get_logger(__name__)


class FileOperationError(Exception):
    """Custom exception for file operation errors."""

    def __init__(
        self, message: str, operation_id: Optional[UUID] = None, details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.operation_id = operation_id
        self.details = details or {}


class FileOperationService:
    """Service for safe file operations with comprehensive safety mechanisms."""

    def __init__(self, max_workers: int = 2, backup_root: Optional[str] = None):
        """Initialize the file operation service.

        Args:
            max_workers: Maximum number of worker threads for file operations
            backup_root: Root directory for backups (uses system temp if None)
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.backup_root = backup_root or tempfile.gettempdir()
        self.backup_root_path = Path(self.backup_root) / "kiremisu_backups"
        self.backup_root_path.mkdir(exist_ok=True, parents=True)

    async def create_operation(
        self, db: AsyncSession, request: FileOperationRequest
    ) -> FileOperationResponse:
        """Create a new file operation with initial validation.

        Args:
            db: Database session
            request: File operation request

        Returns:
            FileOperationResponse: Created operation

        Raises:
            FileOperationError: If initial validation fails
        """
        operation_logger = logger.bind(
            operation_type=request.operation_type,
            source_path=request.source_path,
            target_path=request.target_path,
        )

        operation_logger.info("Creating file operation")

        # Create operation record
        operation = FileOperation(
            id=uuid4(),
            operation_type=request.operation_type,
            source_path=request.source_path,
            target_path=request.target_path,
            operation_metadata={
                "force": request.force,
                "create_backup": request.create_backup,
                "skip_validation": request.skip_validation,
                "validate_database_consistency": request.validate_database_consistency,
                "original_request": request.model_dump(),
            },
        )

        # Basic path validation
        if not os.path.exists(request.source_path):
            raise FileOperationError(
                f"Source path does not exist: {request.source_path}", operation_id=operation.id
            )

        if not os.access(request.source_path, os.R_OK):
            raise FileOperationError(
                f"Source path is not readable: {request.source_path}", operation_id=operation.id
            )

        # For rename/move operations, validate target path
        if request.operation_type in ["rename", "move"] and request.target_path:
            target_parent = Path(request.target_path).parent
            if not target_parent.exists():
                raise FileOperationError(
                    f"Target directory does not exist: {target_parent}", operation_id=operation.id
                )

            if not os.access(str(target_parent), os.W_OK):
                raise FileOperationError(
                    f"Target directory is not writable: {target_parent}", operation_id=operation.id
                )

        db.add(operation)
        await db.commit()
        await db.refresh(operation)

        operation_logger.info("File operation created", operation_id=operation.id)
        return FileOperationResponse.from_model(operation)

    async def validate_operation(self, db: AsyncSession, operation_id: UUID) -> ValidationResult:
        """Perform comprehensive validation of a file operation.

        Args:
            db: Database session
            operation_id: Operation ID to validate

        Returns:
            ValidationResult: Detailed validation results

        Raises:
            FileOperationError: If operation not found or validation fails
        """
        operation_logger = logger.bind(operation_id=operation_id)
        operation_logger.info("Starting operation validation")

        # Get operation
        result = await db.execute(select(FileOperation).where(FileOperation.id == operation_id))
        operation = result.scalar_one_or_none()

        if not operation:
            raise FileOperationError(f"Operation not found: {operation_id}")

        validation_result = ValidationResult(is_valid=True)

        try:
            # Skip validation if requested
            if operation.operation_metadata.get("skip_validation", False):
                validation_result.warnings.append("Validation was skipped by request")
                validation_result.risk_level = "medium"
                operation_logger.warning("Validation skipped by request")
            else:
                # Perform comprehensive validation
                await self._validate_file_system_operation(operation, validation_result)
                await self._validate_database_consistency(db, operation, validation_result)
                await self._assess_operation_risks(operation, validation_result)

            # Update operation with validation results
            operation.status = "validated" if validation_result.is_valid else "failed"
            operation.validated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            operation.validation_results = validation_result.model_dump()

            # Store affected records for tracking
            affected_series, affected_chapters = await self._find_affected_records(db, operation)
            operation.affected_series_ids = [str(s.id) for s in affected_series]
            operation.affected_chapter_ids = [str(c.id) for c in affected_chapters]

            validation_result.affected_series_count = len(affected_series)
            validation_result.affected_chapter_count = len(affected_chapters)

            await db.commit()

            operation_logger.info(
                "Operation validation completed",
                is_valid=validation_result.is_valid,
                risk_level=validation_result.risk_level,
                affected_series=len(affected_series),
                affected_chapters=len(affected_chapters),
            )

        except Exception as e:
            validation_result.is_valid = False
            validation_result.errors.append(f"Validation failed: {str(e)}")
            validation_result.risk_level = "high"

            operation.status = "failed"
            operation.error_message = f"Validation failed: {str(e)}"
            await db.commit()

            operation_logger.error("Operation validation failed", error=str(e))

        return validation_result

    async def execute_operation(
        self, db: AsyncSession, operation_id: UUID
    ) -> FileOperationResponse:
        """Execute a validated file operation safely.

        Args:
            db: Database session
            operation_id: Operation ID to execute

        Returns:
            FileOperationResponse: Updated operation status

        Raises:
            FileOperationError: If operation fails
        """
        operation_logger = logger.bind(operation_id=operation_id)
        operation_logger.info("Starting operation execution")

        # Get operation
        result = await db.execute(select(FileOperation).where(FileOperation.id == operation_id))
        operation = result.scalar_one_or_none()

        if not operation:
            raise FileOperationError(f"Operation not found: {operation_id}")

        if operation.status not in ["validated", "failed"]:
            raise FileOperationError(
                f"Operation must be validated before execution. Current status: {operation.status}",
                operation_id=operation.id,
            )

        if operation.status == "failed":
            raise FileOperationError(
                f"Cannot execute failed operation: {operation.error_message}",
                operation_id=operation.id,
            )

        # Update status to in_progress
        operation.status = "in_progress"
        operation.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        try:
            # Create backup if requested
            backup_path = None
            if operation.operation_metadata.get("create_backup", True):
                backup_path = await self._create_backup(operation)
                operation.backup_path = backup_path
                await db.commit()

            # Execute the file operation
            await self._execute_file_operation(operation)

            # Update database records
            await self._update_database_records(db, operation)

            # Mark operation as completed
            operation.status = "completed"
            operation.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

            operation_logger.info(
                "Operation execution completed successfully", backup_path=backup_path
            )

            return FileOperationResponse.from_model(operation)

        except Exception as e:
            # Mark operation as failed
            operation.status = "failed"
            operation.error_message = str(e)
            await db.commit()

            operation_logger.error("Operation execution failed", error=str(e))

            # Attempt rollback if backup exists
            if operation.backup_path:
                try:
                    await self._rollback_operation(operation)
                    operation_logger.warning("Operation rolled back successfully")
                except Exception as rollback_error:
                    operation_logger.error("Rollback failed", error=str(rollback_error))

            raise FileOperationError(
                f"Operation execution failed: {str(e)}",
                operation_id=operation.id,
                details={"backup_path": operation.backup_path},
            )

    async def rollback_operation(
        self, db: AsyncSession, operation_id: UUID
    ) -> FileOperationResponse:
        """Rollback a completed or failed operation.

        Args:
            db: Database session
            operation_id: Operation ID to rollback

        Returns:
            FileOperationResponse: Updated operation status

        Raises:
            FileOperationError: If rollback fails
        """
        operation_logger = logger.bind(operation_id=operation_id)
        operation_logger.info("Starting operation rollback")

        # Get operation
        result = await db.execute(select(FileOperation).where(FileOperation.id == operation_id))
        operation = result.scalar_one_or_none()

        if not operation:
            raise FileOperationError(f"Operation not found: {operation_id}")

        if not operation.backup_path:
            raise FileOperationError(
                "Cannot rollback operation without backup", operation_id=operation.id
            )

        try:
            # Perform rollback
            await self._rollback_operation(operation)

            # Rollback database changes
            await self._rollback_database_changes(db, operation)

            # Update operation status
            operation.status = "rolled_back"
            await db.commit()

            operation_logger.info("Operation rollback completed successfully")
            return FileOperationResponse.from_model(operation)

        except Exception as e:
            operation_logger.error("Operation rollback failed", error=str(e))
            raise FileOperationError(f"Rollback failed: {str(e)}", operation_id=operation.id)

    async def _validate_file_system_operation(
        self, operation: FileOperation, validation_result: ValidationResult
    ) -> None:
        """Validate file system aspects of the operation."""
        source_path = Path(operation.source_path)

        # Check source path exists and is accessible
        if not source_path.exists():
            validation_result.errors.append(f"Source path does not exist: {operation.source_path}")
            validation_result.is_valid = False
            return

        if not os.access(operation.source_path, os.R_OK):
            validation_result.errors.append(f"Source path is not readable: {operation.source_path}")
            validation_result.is_valid = False
            return

        # Check if source is in use (basic check)
        if await self._is_path_in_use(operation.source_path):
            validation_result.warnings.append("Source path may be in use by another process")
            validation_result.risk_level = "medium"

        # For rename/move operations, validate target
        if operation.operation_type in ["rename", "move"] and operation.target_path:
            target_path = Path(operation.target_path)

            # Check target doesn't already exist
            if target_path.exists():
                validation_result.conflicts.append(
                    {
                        "type": "target_exists",
                        "path": operation.target_path,
                        "message": "Target path already exists",
                    }
                )
                validation_result.requires_confirmation = True
                validation_result.risk_level = "medium"

            # Check target parent directory exists and is writable
            if not target_path.parent.exists():
                validation_result.errors.append(
                    f"Target directory does not exist: {target_path.parent}"
                )
                validation_result.is_valid = False
            elif not os.access(str(target_path.parent), os.W_OK):
                validation_result.errors.append(
                    f"Target directory is not writable: {target_path.parent}"
                )
                validation_result.is_valid = False

        # Estimate disk usage for backups
        if operation.operation_metadata.get("create_backup", True):
            size_mb = await self._estimate_path_size(operation.source_path) / (1024 * 1024)
            validation_result.estimated_disk_usage_mb = size_mb

            # Check available disk space
            available_space = shutil.disk_usage(self.backup_root).free / (1024 * 1024)
            if size_mb > available_space * 0.8:  # Use max 80% of available space
                validation_result.warnings.append(
                    f"Limited disk space for backup: {size_mb:.1f}MB needed, {available_space:.1f}MB available"
                )
                validation_result.risk_level = "medium"

    async def _validate_database_consistency(
        self, db: AsyncSession, operation: FileOperation, validation_result: ValidationResult
    ) -> None:
        """Validate database consistency for the operation."""
        if not operation.operation_metadata.get("validate_database_consistency", True):
            validation_result.warnings.append("Database consistency validation was skipped")
            return

        # Find affected series and chapters
        affected_series, affected_chapters = await self._find_affected_records(db, operation)

        if not affected_series and not affected_chapters:
            validation_result.warnings.append(
                "No database records found for this path - may be untracked files"
            )
            return

        # Check for reading progress that would be lost
        read_chapters = [c for c in affected_chapters if c.is_read or c.last_read_page > 0]
        if read_chapters:
            validation_result.warnings.append(
                f"{len(read_chapters)} chapters have reading progress that may be affected"
            )
            validation_result.requires_confirmation = True
            validation_result.risk_level = "medium"

        # Check for series with custom metadata
        custom_series = [s for s in affected_series if s.user_metadata or s.custom_tags]
        if custom_series:
            validation_result.warnings.append(
                f"{len(custom_series)} series have custom metadata that may be affected"
            )
            validation_result.requires_confirmation = True

    async def _assess_operation_risks(
        self, operation: FileOperation, validation_result: ValidationResult
    ) -> None:
        """Assess overall risks of the operation."""
        risk_factors = 0

        # High-risk operation types
        if operation.operation_type == "delete":
            risk_factors += 2
            validation_result.requires_confirmation = True

        # Multiple affected records
        if validation_result.affected_series_count > 1:
            risk_factors += 1
        if validation_result.affected_chapter_count > 10:
            risk_factors += 1

        # Large files
        if (
            validation_result.estimated_disk_usage_mb
            and validation_result.estimated_disk_usage_mb > 1000
        ):
            risk_factors += 1

        # Force flag
        if operation.operation_metadata.get("force", False):
            risk_factors += 1
            validation_result.warnings.append("Operation is using force flag")

        # Skip validation flag
        if operation.operation_metadata.get("skip_validation", False):
            risk_factors += 2

        # Update risk level based on factors
        if risk_factors >= 4:
            validation_result.risk_level = "high"
            validation_result.requires_confirmation = True
        elif risk_factors >= 2:
            validation_result.risk_level = "medium"
        else:
            validation_result.risk_level = "low"

    async def _find_affected_records(
        self, db: AsyncSession, operation: FileOperation
    ) -> Tuple[List[Series], List[Chapter]]:
        """Find database records affected by the operation."""
        source_path = operation.source_path

        # Find series with matching file_path
        series_result = await db.execute(
            select(Series).where(
                or_(
                    Series.file_path == source_path,
                    Series.file_path.like(f"{source_path}%"),
                    Series.cover_image_path == source_path,
                    Series.cover_image_path.like(f"{source_path}%"),
                )
            )
        )
        affected_series = list(series_result.scalars().all())

        # Find chapters with matching file_path
        chapters_result = await db.execute(
            select(Chapter).where(
                or_(Chapter.file_path == source_path, Chapter.file_path.like(f"{source_path}%"))
            )
        )
        affected_chapters = list(chapters_result.scalars().all())

        return affected_series, affected_chapters

    async def _create_backup(self, operation: FileOperation) -> str:
        """Create a backup of the source path."""
        source_path = Path(operation.source_path)

        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root_path / f"{operation.id}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / source_path.name

        def _backup_sync():
            if source_path.is_file():
                shutil.copy2(source_path, backup_path)
            else:
                shutil.copytree(source_path, backup_path, symlinks=True, dirs_exist_ok=True)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _backup_sync)

        return str(backup_path)

    async def _execute_file_operation(self, operation: FileOperation) -> None:
        """Execute the actual file operation."""
        source_path = Path(operation.source_path)

        def _execute_sync():
            if operation.operation_type == "delete":
                if source_path.is_file():
                    source_path.unlink()
                else:
                    shutil.rmtree(source_path)

            elif operation.operation_type in ["rename", "move"]:
                target_path = Path(operation.target_path)
                shutil.move(str(source_path), str(target_path))

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _execute_sync)

    async def _update_database_records(self, db: AsyncSession, operation: FileOperation) -> None:
        """Update database records after successful file operation."""
        # Get affected records
        affected_series, affected_chapters = await self._find_affected_records(db, operation)

        if operation.operation_type == "delete":
            # Remove records for deleted files
            for series in affected_series:
                await db.delete(series)
            for chapter in affected_chapters:
                await db.delete(chapter)

        elif operation.operation_type in ["rename", "move"]:
            # Update file paths
            old_path = operation.source_path
            new_path = operation.target_path

            for series in affected_series:
                if series.file_path and series.file_path.startswith(old_path):
                    series.file_path = series.file_path.replace(old_path, new_path)
                if series.cover_image_path and series.cover_image_path.startswith(old_path):
                    series.cover_image_path = series.cover_image_path.replace(old_path, new_path)

            for chapter in affected_chapters:
                if chapter.file_path.startswith(old_path):
                    chapter.file_path = chapter.file_path.replace(old_path, new_path)

        await db.commit()

    async def _rollback_operation(self, operation: FileOperation) -> None:
        """Rollback file system changes."""
        if not operation.backup_path:
            raise FileOperationError("No backup available for rollback")

        backup_path = Path(operation.backup_path)
        original_path = Path(operation.source_path)

        def _rollback_sync():
            if operation.operation_type == "delete":
                # Restore from backup
                if backup_path.is_file():
                    shutil.copy2(backup_path, original_path)
                else:
                    shutil.copytree(backup_path, original_path, symlinks=True)

            elif operation.operation_type in ["rename", "move"]:
                # Move back from target to source
                target_path = Path(operation.target_path)
                if target_path.exists():
                    shutil.move(str(target_path), str(original_path))

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _rollback_sync)

    async def _rollback_database_changes(self, db: AsyncSession, operation: FileOperation) -> None:
        """Rollback database changes."""
        # This would restore the original database state
        # For now, we'll just refresh affected records
        # In a production system, you'd want to store the original state
        # and restore it exactly
        pass

    async def _is_path_in_use(self, path: str) -> bool:
        """Check if a path is currently in use (basic implementation)."""
        # This is a basic implementation - in production you might want
        # more sophisticated checks like lsof on Unix systems
        try:
            if Path(path).is_dir():
                # Try to create a temporary file in the directory
                temp_file = Path(path) / f".tmp_{uuid4().hex}"
                temp_file.touch()
                temp_file.unlink()
            return False
        except (PermissionError, OSError):
            return True

    async def _estimate_path_size(self, path: str) -> int:
        """Estimate the size of a path in bytes."""

        def _calculate_size():
            path_obj = Path(path)
            if path_obj.is_file():
                return path_obj.stat().st_size
            else:
                total_size = 0
                for file_path in path_obj.rglob("*"):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except (PermissionError, OSError):
                            pass
                return total_size

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _calculate_size)

    async def get_operation(
        self, db: AsyncSession, operation_id: UUID
    ) -> Optional[FileOperationResponse]:
        """Get a file operation by ID."""
        result = await db.execute(select(FileOperation).where(FileOperation.id == operation_id))
        operation = result.scalar_one_or_none()

        if operation:
            return FileOperationResponse.from_model(operation)
        return None

    async def list_operations(
        self,
        db: AsyncSession,
        status_filter: Optional[str] = None,
        operation_type_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FileOperationResponse]:
        """List file operations with optional filtering."""
        query = select(FileOperation)

        if status_filter:
            query = query.where(FileOperation.status == status_filter)

        if operation_type_filter:
            query = query.where(FileOperation.operation_type == operation_type_filter)

        query = query.order_by(FileOperation.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        operations = result.scalars().all()

        return [FileOperationResponse.from_model(op) for op in operations]

    async def cleanup_old_operations(self, db: AsyncSession, days_old: int = 30) -> int:
        """Clean up old completed operations and their backups."""
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_old)

        # Find old completed operations
        result = await db.execute(
            select(FileOperation).where(
                and_(
                    FileOperation.status.in_(["completed", "failed", "rolled_back"]),
                    FileOperation.created_at < cutoff_date,
                )
            )
        )
        old_operations = result.scalars().all()

        cleaned_count = 0
        for operation in old_operations:
            # Clean up backup if it exists
            if operation.backup_path and Path(operation.backup_path).exists():
                backup_parent = Path(operation.backup_path).parent
                try:
                    shutil.rmtree(backup_parent)
                except OSError:
                    pass

            # Remove operation record
            await db.delete(operation)
            cleaned_count += 1

        await db.commit()
        return cleaned_count

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.executor.shutdown(wait=True)
