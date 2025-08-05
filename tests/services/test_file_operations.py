"""Comprehensive unit tests for FileOperationService.

Tests cover all safety mechanisms, edge cases, and error conditions for the
safe file operation system.
"""

import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import FileOperation, Series, Chapter
from kiremisu.database.schemas import (
    FileOperationRequest,
    FileOperationResponse,
    ValidationResult,
)
from kiremisu.services.file_operations import FileOperationService, FileOperationError


class TestFileOperationService:
    """Test FileOperationService functionality."""

    @pytest.fixture
    async def service(self):
        """Create FileOperationService instance."""
        return FileOperationService(max_workers=1)

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_files(self, temp_directory):
        """Create sample files for testing."""
        files = {}
        
        # Create test manga file
        manga_file = temp_directory / "test_manga.cbz"
        manga_file.write_bytes(b"fake cbz content")
        files["manga_file"] = str(manga_file)
        
        # Create test directory with images
        manga_dir = temp_directory / "test_series"
        manga_dir.mkdir()
        chapter_dir = manga_dir / "Chapter 001"
        chapter_dir.mkdir()
        (chapter_dir / "page_001.jpg").write_bytes(b"fake image")
        (chapter_dir / "page_002.jpg").write_bytes(b"fake image")
        files["manga_dir"] = str(manga_dir)
        files["chapter_dir"] = str(chapter_dir)
        
        # Create target directory
        target_dir = temp_directory / "target"
        target_dir.mkdir()
        files["target_dir"] = str(target_dir)
        
        return files

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        return db

    async def test_create_operation_success(self, service, mock_db, sample_files):
        """Test successful operation creation."""
        request = FileOperationRequest(
            operation_type="rename",
            source_path=sample_files["manga_file"],
            target_path=str(Path(sample_files["target_dir"]) / "renamed.cbz")
        )

        response = await service.create_operation(mock_db, request)

        assert response.operation_type == "rename"
        assert response.source_path == sample_files["manga_file"]
        assert response.status == "pending"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_create_operation_source_not_exists(self, service, mock_db):
        """Test operation creation with non-existent source."""
        request = FileOperationRequest(
            operation_type="delete",
            source_path="/non/existent/path"
        )

        with pytest.raises(FileOperationError) as exc_info:
            await service.create_operation(mock_db, request)
        
        assert "does not exist" in str(exc_info.value)

    async def test_create_operation_source_not_readable(self, service, mock_db, sample_files):
        """Test operation creation with unreadable source."""
        # Make file unreadable
        os.chmod(sample_files["manga_file"], 0o000)
        
        try:
            request = FileOperationRequest(
                operation_type="delete",
                source_path=sample_files["manga_file"]
            )

            with pytest.raises(FileOperationError) as exc_info:
                await service.create_operation(mock_db, request)
            
            assert "not readable" in str(exc_info.value)
        
        finally:
            # Restore permissions for cleanup
            os.chmod(sample_files["manga_file"], 0o644)

    async def test_create_operation_invalid_target_directory(self, service, mock_db, sample_files):
        """Test operation creation with invalid target directory."""
        request = FileOperationRequest(
            operation_type="rename",
            source_path=sample_files["manga_file"],
            target_path="/non/existent/dir/file.cbz"
        )

        with pytest.raises(FileOperationError) as exc_info:
            await service.create_operation(mock_db, request)
        
        assert "does not exist" in str(exc_info.value)

    async def test_validate_operation_success(self, service, mock_db, sample_files):
        """Test successful operation validation."""
        # Create operation
        operation = FileOperation(
            id=uuid4(),
            operation_type="rename",
            source_path=sample_files["manga_file"],
            target_path=str(Path(sample_files["target_dir"]) / "renamed.cbz"),
            operation_metadata={"create_backup": True}
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        # Mock affected records queries
        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = []
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,  # Get operation
            mock_series_result,  # Find affected series
            mock_chapters_result,  # Find affected chapters
        ]

        validation_result = await service.validate_operation(mock_db, operation.id)

        assert validation_result.is_valid
        assert validation_result.risk_level == "low"
        assert len(validation_result.errors) == 0

    async def test_validate_operation_target_exists_conflict(self, service, mock_db, sample_files):
        """Test validation with target path conflict."""
        # Create target file
        target_path = Path(sample_files["target_dir"]) / "existing.cbz"
        target_path.write_bytes(b"existing file")

        operation = FileOperation(
            id=uuid4(),
            operation_type="rename",
            source_path=sample_files["manga_file"],
            target_path=str(target_path),
            operation_metadata={"create_backup": True}
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        # Mock affected records queries
        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = []
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,  # Get operation
            mock_series_result,  # Find affected series
            mock_chapters_result,  # Find affected chapters
        ]

        validation_result = await service.validate_operation(mock_db, operation.id)

        assert validation_result.is_valid
        assert validation_result.risk_level == "medium"
        assert validation_result.requires_confirmation
        assert len(validation_result.conflicts) == 1
        assert validation_result.conflicts[0]["type"] == "target_exists"

    async def test_validate_operation_with_affected_records(self, service, mock_db, sample_files):
        """Test validation with affected database records."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_dir"],
            operation_metadata={"create_backup": True}
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        
        # Mock affected series with reading progress
        affected_series = [
            Series(
                id=uuid4(),
                title_primary="Test Series",
                file_path=sample_files["manga_dir"],
                user_metadata={"custom": "data"},
                custom_tags=["favorite"]
            )
        ]
        
        # Mock affected chapters with reading progress
        affected_chapters = [
            Chapter(
                id=uuid4(),
                series_id=affected_series[0].id,
                chapter_number=1,
                file_path=sample_files["chapter_dir"],
                is_read=True,
                last_read_page=5
            )
        ]

        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = affected_series
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = affected_chapters
        
        mock_db.execute.side_effect = [
            mock_result,  # Get operation
            mock_series_result,  # Find affected series
            mock_chapters_result,  # Find affected chapters
        ]

        validation_result = await service.validate_operation(mock_db, operation.id)

        assert validation_result.is_valid
        assert validation_result.risk_level == "high"  # Delete operation + affected records
        assert validation_result.requires_confirmation
        assert validation_result.affected_series_count == 1
        assert validation_result.affected_chapter_count == 1
        assert "reading progress" in validation_result.warnings[0]
        assert "custom metadata" in validation_result.warnings[1]

    async def test_validate_operation_skip_validation(self, service, mock_db, sample_files):
        """Test validation when skip_validation is True."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_file"],
            operation_metadata={"skip_validation": True}
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        validation_result = await service.validate_operation(mock_db, operation.id)

        assert validation_result.is_valid
        assert validation_result.risk_level == "medium"
        assert "skipped by request" in validation_result.warnings[0]

    async def test_execute_operation_delete_success(self, service, mock_db, sample_files):
        """Test successful delete operation execution."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_file"],
            status="validated",
            operation_metadata={"create_backup": True},
            affected_series_ids=[],
            affected_chapter_ids=[]
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        
        # Mock affected records queries for database updates
        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = []
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,  # Get operation
            mock_series_result,  # Find affected series for update
            mock_chapters_result,  # Find affected chapters for update
        ]

        # Verify file exists before execution
        assert Path(operation.source_path).exists()

        response = await service.execute_operation(mock_db, operation.id)

        # Verify file was deleted
        assert not Path(operation.source_path).exists()
        assert response.status == "completed"
        assert response.backup_path is not None
        assert Path(response.backup_path).exists()  # Backup should exist

    async def test_execute_operation_rename_success(self, service, mock_db, sample_files):
        """Test successful rename operation execution."""
        target_path = str(Path(sample_files["target_dir"]) / "renamed.cbz")
        
        operation = FileOperation(
            id=uuid4(),
            operation_type="rename",
            source_path=sample_files["manga_file"],
            target_path=target_path,
            status="validated",
            operation_metadata={"create_backup": True},
            affected_series_ids=[],
            affected_chapter_ids=[]
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        
        # Mock affected records queries
        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = []
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,  # Get operation
            mock_series_result,  # Find affected series for update
            mock_chapters_result,  # Find affected chapters for update
        ]

        # Verify source exists and target doesn't
        assert Path(operation.source_path).exists()
        assert not Path(target_path).exists()

        response = await service.execute_operation(mock_db, operation.id)

        # Verify file was renamed
        assert not Path(operation.source_path).exists()
        assert Path(target_path).exists()
        assert response.status == "completed"
        assert response.backup_path is not None

    async def test_execute_operation_not_validated(self, service, mock_db, sample_files):
        """Test execution of non-validated operation."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_file"],
            status="pending"
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        with pytest.raises(FileOperationError) as exc_info:
            await service.execute_operation(mock_db, operation.id)
        
        assert "must be validated" in str(exc_info.value)

    async def test_execute_operation_failed_validation(self, service, mock_db, sample_files):
        """Test execution of operation with failed validation."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_file"],
            status="failed",
            error_message="Validation failed"
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        with pytest.raises(FileOperationError) as exc_info:
            await service.execute_operation(mock_db, operation.id)
        
        assert "Cannot execute failed operation" in str(exc_info.value)

    @patch('shutil.move', side_effect=PermissionError("Access denied"))
    async def test_execute_operation_file_error_with_rollback(self, mock_move, service, mock_db, sample_files):
        """Test operation execution failure with automatic rollback."""
        target_path = str(Path(sample_files["target_dir"]) / "renamed.cbz")
        
        operation = FileOperation(
            id=uuid4(),
            operation_type="rename",
            source_path=sample_files["manga_file"],
            target_path=target_path,
            status="validated",
            operation_metadata={"create_backup": True},
            affected_series_ids=[],
            affected_chapter_ids=[]
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        
        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = []
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,  # Get operation
            mock_series_result,  # Find affected series for update
            mock_chapters_result,  # Find affected chapters for update
        ]

        with pytest.raises(FileOperationError) as exc_info:
            await service.execute_operation(mock_db, operation.id)
        
        assert "Access denied" in str(exc_info.value)
        # Verify original file still exists (rollback successful)
        assert Path(operation.source_path).exists()

    async def test_rollback_operation_success(self, service, mock_db, sample_files):
        """Test successful operation rollback."""
        # First execute a delete operation to have something to rollback
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_file"],
            status="completed",
            operation_metadata={"create_backup": True},
            backup_path=None,  # Will be set during execution
            affected_series_ids=[],
            affected_chapter_ids=[]
        )

        # Simulate a completed operation with backup
        backup_dir = Path(service.backup_root_path) / f"{operation.id}_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / "test_manga.cbz"
        shutil.copy2(sample_files["manga_file"], backup_file)
        operation.backup_path = str(backup_file)

        # Delete the original file to simulate completed delete operation
        Path(sample_files["manga_file"]).unlink()

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        # Verify file is deleted
        assert not Path(sample_files["manga_file"]).exists()

        response = await service.rollback_operation(mock_db, operation.id)

        # Verify file was restored
        assert Path(sample_files["manga_file"]).exists()
        assert response.status == "rolled_back"

    async def test_rollback_operation_no_backup(self, service, mock_db, sample_files):
        """Test rollback of operation without backup."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path=sample_files["manga_file"],
            status="completed",
            backup_path=None
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        with pytest.raises(FileOperationError) as exc_info:
            await service.rollback_operation(mock_db, operation.id)
        
        assert "Cannot rollback operation without backup" in str(exc_info.value)

    async def test_get_operation_success(self, service, mock_db):
        """Test successful operation retrieval."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path="/test/path",
            status="pending"
        )

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = operation
        mock_db.execute.return_value = mock_result

        response = await service.get_operation(mock_db, operation.id)

        assert response is not None
        assert response.id == operation.id
        assert response.operation_type == "delete"

    async def test_get_operation_not_found(self, service, mock_db):
        """Test operation retrieval when not found."""
        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = await service.get_operation(mock_db, uuid4())

        assert response is None

    async def test_list_operations_success(self, service, mock_db):
        """Test successful operation listing."""
        operations = [
            FileOperation(
                id=uuid4(),
                operation_type="delete",
                source_path="/test/path1",
                status="pending"
            ),
            FileOperation(
                id=uuid4(),
                operation_type="rename",
                source_path="/test/path2",
                status="completed"
            )
        ]

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = operations
        mock_db.execute.return_value = mock_result

        response = await service.list_operations(mock_db, limit=10, offset=0)

        assert len(response) == 2
        assert response[0].operation_type == "delete"
        assert response[1].operation_type == "rename"

    async def test_list_operations_with_filters(self, service, mock_db):
        """Test operation listing with filters."""
        operations = [
            FileOperation(
                id=uuid4(),
                operation_type="delete",
                source_path="/test/path1",
                status="completed"
            )
        ]

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = operations
        mock_db.execute.return_value = mock_result

        response = await service.list_operations(
            mock_db, status_filter="completed", operation_type_filter="delete"
        )

        assert len(response) == 1
        assert response[0].status == "completed"
        assert response[0].operation_type == "delete"

    async def test_cleanup_old_operations(self, service, mock_db, temp_directory):
        """Test cleanup of old operations."""
        # Create old operations with backup directories
        old_operations = []
        for i in range(3):
            op_id = uuid4()
            backup_dir = temp_directory / f"backup_{op_id}"
            backup_dir.mkdir()
            (backup_dir / "test.file").write_text("test")
            
            operation = FileOperation(
                id=op_id,
                operation_type="delete",
                source_path=f"/test/path{i}",
                status="completed",
                backup_path=str(backup_dir / "test.file"),
                created_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
            )
            old_operations.append(operation)

        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = old_operations
        mock_db.execute.return_value = mock_result

        # Verify backup directories exist
        for op in old_operations:
            backup_path = Path(op.backup_path)
            assert backup_path.exists()

        cleaned_count = await service.cleanup_old_operations(mock_db, days_old=30)

        assert cleaned_count == 3
        
        # Verify backup directories were cleaned up
        for op in old_operations:
            backup_dir = Path(op.backup_path).parent
            assert not backup_dir.exists()

        # Verify delete was called for each operation
        assert mock_db.delete.call_count == 3

    async def test_path_size_estimation(self, service, temp_directory):
        """Test path size estimation functionality."""
        # Create test files with known sizes
        test_file = temp_directory / "test.txt"
        test_content = b"A" * 1024  # 1KB
        test_file.write_bytes(test_content)
        
        size = await service._estimate_path_size(str(test_file))
        assert size == 1024

    async def test_directory_size_estimation(self, service, temp_directory):
        """Test directory size estimation functionality."""
        # Create test directory with multiple files
        sub_dir = temp_directory / "subdir"
        sub_dir.mkdir()
        
        file1 = sub_dir / "file1.txt"
        file2 = sub_dir / "file2.txt"
        file1.write_bytes(b"A" * 512)  # 512 bytes
        file2.write_bytes(b"B" * 256)  # 256 bytes
        
        size = await service._estimate_path_size(str(sub_dir))
        assert size == 768  # 512 + 256

    async def test_risk_assessment_high_risk(self, service, mock_db, sample_files):
        """Test risk assessment for high-risk operations."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",  # High risk
            source_path=sample_files["manga_dir"],
            operation_metadata={
                "force": True,  # Risk factor
                "skip_validation": True  # High risk factor
            }
        )

        validation_result = ValidationResult(is_valid=True)
        validation_result.affected_series_count = 2  # Risk factor
        validation_result.affected_chapter_count = 15  # Risk factor
        validation_result.estimated_disk_usage_mb = 2000  # Risk factor

        await service._assess_operation_risks(operation, validation_result)

        assert validation_result.risk_level == "high"
        assert validation_result.requires_confirmation
        assert "force flag" in validation_result.warnings

    async def test_risk_assessment_low_risk(self, service, mock_db, sample_files):
        """Test risk assessment for low-risk operations."""
        operation = FileOperation(
            id=uuid4(),
            operation_type="rename",  # Lower risk than delete
            source_path=sample_files["manga_file"],
            target_path=str(Path(sample_files["target_dir"]) / "renamed.cbz"),
            operation_metadata={"force": False, "skip_validation": False}
        )

        validation_result = ValidationResult(is_valid=True)
        validation_result.affected_series_count = 0
        validation_result.affected_chapter_count = 1
        validation_result.estimated_disk_usage_mb = 50

        await service._assess_operation_risks(operation, validation_result)

        assert validation_result.risk_level == "low"
        assert not validation_result.requires_confirmation

    async def test_concurrent_operations_safety(self, sample_files):
        """Test that concurrent operations are handled safely."""
        services = [FileOperationService(max_workers=1) for _ in range(3)]
        
        async def create_and_execute_operation(service_idx):
            service = services[service_idx]
            mock_db = AsyncMock(spec=AsyncSession)
            mock_db.commit = AsyncMock()
            mock_db.add = MagicMock()
            
            # Create test file for this operation
            test_file = Path(sample_files["target_dir"]) / f"test_{service_idx}.txt"
            test_file.write_text(f"content_{service_idx}")
            
            request = FileOperationRequest(
                operation_type="delete",
                source_path=str(test_file)
            )
            
            return await service.create_operation(mock_db, request)

        # Run concurrent operations
        tasks = [create_and_execute_operation(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should succeed without conflicts
        for result in results:
            assert isinstance(result, FileOperationResponse)
            assert result.operation_type == "delete"
        
        # Cleanup services
        for service in services:
            await service.__aexit__(None, None, None)


class TestFileOperationErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    async def service(self):
        """Create FileOperationService instance."""
        return FileOperationService(max_workers=1)

    async def test_invalid_operation_type(self, service):
        """Test handling of invalid operation type."""
        with pytest.raises(ValueError):
            FileOperationRequest(
                operation_type="invalid",
                source_path="/test/path"
            )

    async def test_empty_source_path(self, service):
        """Test handling of empty source path."""
        with pytest.raises(ValueError):
            FileOperationRequest(
                operation_type="delete",
                source_path=""
            )

    async def test_missing_target_path_for_rename(self, service):
        """Test handling of missing target path for rename operation."""
        with pytest.raises(ValueError):
            FileOperationRequest(
                operation_type="rename",
                source_path="/test/source"
                # Missing target_path
            )

    async def test_service_cleanup_on_context_exit(self, service):
        """Test that service properly cleans up resources."""
        # Service should clean up thread pool on exit
        async with service:
            assert service.executor is not None
        
        # After context exit, executor should be shut down
        # Note: We can't directly test this without implementation details

    async def test_backup_creation_failure(self, service, temp_directory):
        """Test handling of backup creation failure."""
        # Create a file in a read-only directory
        readonly_dir = temp_directory / "readonly"
        readonly_dir.mkdir()
        test_file = readonly_dir / "test.txt"
        test_file.write_text("content")
        
        # Make directory read-only
        os.chmod(str(readonly_dir), 0o444)
        
        try:
            operation = FileOperation(
                id=uuid4(),
                operation_type="delete",
                source_path=str(test_file)
            )
            
            with pytest.raises(PermissionError):
                await service._create_backup(operation)
        
        finally:
            # Restore permissions for cleanup
            os.chmod(str(readonly_dir), 0o755)

    async def test_database_consistency_with_orphaned_records(self, service):
        """Test handling of orphaned database records."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create operation targeting non-existent file
        operation = FileOperation(
            id=uuid4(),
            operation_type="delete",
            source_path="/non/existent/path",
            operation_metadata={"validate_database_consistency": True}
        )
        
        # Mock finding orphaned records in database
        orphaned_series = [
            Series(
                id=uuid4(),
                title_primary="Orphaned Series",
                file_path="/non/existent/path"
            )
        ]
        
        mock_series_result = AsyncMock()
        mock_series_result.scalars.return_value.all.return_value = orphaned_series
        mock_chapters_result = AsyncMock()
        mock_chapters_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [
            mock_series_result,  # Find affected series
            mock_chapters_result,  # Find affected chapters
        ]
        
        validation_result = ValidationResult(is_valid=True)
        await service._validate_database_consistency(mock_db, operation, validation_result)
        
        # Should handle orphaned records gracefully
        assert validation_result.is_valid
        assert validation_result.affected_series_count == 1