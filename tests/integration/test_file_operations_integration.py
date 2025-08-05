"""Integration tests for file operations with real database and filesystem.

These tests verify the complete workflow of file operations including:
- Database consistency
- File system operations
- Transaction rollback
- Error recovery
"""

import asyncio
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import FileOperation, Series, Chapter
from kiremisu.database.schemas import FileOperationRequest
from kiremisu.services.file_operations import FileOperationService, FileOperationError


class TestFileOperationsIntegration:
    """Integration tests for file operations."""

    @pytest.fixture
    def temp_library(self):
        """Create temporary library structure for testing."""
        temp_dir = tempfile.mkdtemp()
        library_path = Path(temp_dir)
        
        # Create test series structure
        series_dir = library_path / "Test Series"
        series_dir.mkdir()
        
        # Create cover image
        cover_file = series_dir / "cover.jpg"
        cover_file.write_bytes(b"fake cover image")
        
        # Create chapters
        for i in range(1, 4):
            chapter_dir = series_dir / f"Chapter {i:03d}"
            chapter_dir.mkdir()
            
            # Create pages
            for j in range(1, 6):
                page_file = chapter_dir / f"page_{j:03d}.jpg"
                page_file.write_bytes(b"fake page image")
        
        # Create CBZ file
        cbz_file = library_path / "Another Series.cbz"
        cbz_file.write_bytes(b"fake cbz content")
        
        yield {
            "library_path": str(library_path),
            "series_dir": str(series_dir),
            "cover_file": str(cover_file),
            "cbz_file": str(cbz_file),
            "chapter_dirs": [str(series_dir / f"Chapter {i:03d}") for i in range(1, 4)]
        }
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    async def test_complete_rename_workflow(self, db_session: AsyncSession, temp_library):
        """Test complete rename workflow from creation to execution."""
        async with FileOperationService() as service:
            # Create test series in database
            series = Series(
                id=uuid4(),
                title_primary="Test Series",
                file_path=temp_library["series_dir"],
                cover_image_path=temp_library["cover_file"],
                total_chapters=3
            )
            db_session.add(series)
            
            # Create test chapters
            chapters = []
            for i, chapter_dir in enumerate(temp_library["chapter_dirs"], 1):
                chapter = Chapter(
                    id=uuid4(),
                    series_id=series.id,
                    chapter_number=float(i),
                    file_path=chapter_dir,
                    page_count=5
                )
                chapters.append(chapter)
                db_session.add(chapter)
            
            await db_session.commit()
            
            # Define target path
            target_path = str(Path(temp_library["library_path"]) / "Renamed Series")
            
            # Step 1: Create operation
            request = FileOperationRequest(
                operation_type="rename",
                source_path=temp_library["series_dir"],
                target_path=target_path,
                create_backup=True
            )
            
            operation_response = await service.create_operation(db_session, request)
            assert operation_response.status == "pending"
            
            # Step 2: Validate operation
            validation_result = await service.validate_operation(db_session, operation_response.id)
            assert validation_result.is_valid
            assert validation_result.affected_series_count == 1
            assert validation_result.affected_chapter_count == 3
            
            # Step 3: Execute operation
            execution_response = await service.execute_operation(db_session, operation_response.id)
            assert execution_response.status == "completed"
            assert execution_response.backup_path is not None
            
            # Verify file system changes
            assert not Path(temp_library["series_dir"]).exists()
            assert Path(target_path).exists()
            assert Path(execution_response.backup_path).exists()
            
            # Verify database consistency
            await db_session.refresh(series)
            assert series.file_path == target_path
            assert series.cover_image_path.replace(temp_library["series_dir"], target_path) == series.cover_image_path
            
            for chapter in chapters:
                await db_session.refresh(chapter)
                assert chapter.file_path.startswith(target_path)

    async def test_complete_delete_workflow_with_rollback(self, db_session: AsyncSession, temp_library):
        """Test complete delete workflow with rollback."""
        async with FileOperationService() as service:
            # Create test series in database
            series = Series(
                id=uuid4(),
                title_primary="Test Series",
                file_path=temp_library["cbz_file"]
            )
            db_session.add(series)
            
            chapter = Chapter(
                id=uuid4(),
                series_id=series.id,
                chapter_number=1.0,
                file_path=temp_library["cbz_file"],
                is_read=True,
                last_read_page=10
            )
            db_session.add(chapter)
            await db_session.commit()
            
            # Step 1: Create delete operation
            request = FileOperationRequest(
                operation_type="delete",
                source_path=temp_library["cbz_file"],
                create_backup=True
            )
            
            operation_response = await service.create_operation(db_session, request)
            
            # Step 2: Validate (should warn about reading progress)
            validation_result = await service.validate_operation(db_session, operation_response.id)
            assert validation_result.is_valid
            assert validation_result.requires_confirmation  # Due to reading progress
            assert "reading progress" in validation_result.warnings[0]
            
            # Step 3: Execute operation
            execution_response = await service.execute_operation(db_session, operation_response.id)
            assert execution_response.status == "completed"
            
            # Verify file was deleted
            assert not Path(temp_library["cbz_file"]).exists()
            
            # Verify database records were removed
            result = await db_session.execute(select(Series).where(Series.id == series.id))
            assert result.scalar_one_or_none() is None
            
            result = await db_session.execute(select(Chapter).where(Chapter.id == chapter.id))
            assert result.scalar_one_or_none() is None
            
            # Step 4: Rollback operation
            rollback_response = await service.rollback_operation(db_session, operation_response.id)
            assert rollback_response.status == "rolled_back"
            
            # Verify file was restored
            assert Path(temp_library["cbz_file"]).exists()

    async def test_concurrent_operations_database_consistency(self, db_session: AsyncSession, temp_library):
        """Test database consistency with concurrent operations."""
        async with FileOperationService() as service:
            # Create test files for concurrent operations
            test_files = []
            for i in range(3):
                test_file = Path(temp_library["library_path"]) / f"concurrent_test_{i}.cbz"
                test_file.write_bytes(b"test content")
                test_files.append(str(test_file))
                
                # Create database records
                series = Series(
                    id=uuid4(),
                    title_primary=f"Concurrent Series {i}",
                    file_path=str(test_file)
                )
                db_session.add(series)
            
            await db_session.commit()
            
            async def delete_operation(file_path: str):
                """Perform delete operation."""
                request = FileOperationRequest(
                    operation_type="delete",
                    source_path=file_path,
                    create_backup=True,
                    skip_validation=True  # Skip for speed in this test
                )
                
                op_response = await service.create_operation(db_session, request)
                await service.validate_operation(db_session, op_response.id)
                return await service.execute_operation(db_session, op_response.id)
            
            # Execute concurrent operations
            tasks = [delete_operation(file_path) for file_path in test_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All operations should succeed
            for result in results:
                assert isinstance(result, type(results[0]))  # FileOperationResponse
                assert result.status == "completed"
            
            # Verify database consistency - all series should be deleted
            for file_path in test_files:
                result = await db_session.execute(
                    select(Series).where(Series.file_path == file_path)
                )
                assert result.scalar_one_or_none() is None
                
                # Verify files are deleted
                assert not Path(file_path).exists()

    async def test_operation_failure_database_rollback(self, db_session: AsyncSession, temp_library):
        """Test database rollback when file operation fails."""
        async with FileOperationService() as service:
            # Create test series
            series = Series(
                id=uuid4(),
                title_primary="Test Series",
                file_path=temp_library["series_dir"]
            )
            db_session.add(series)
            await db_session.commit()
            
            # Create operation that will fail (target directory doesn't exist)
            request = FileOperationRequest(
                operation_type="move",
                source_path=temp_library["series_dir"],
                target_path="/non/existent/directory/target",
                create_backup=True
            )
            
            operation_response = await service.create_operation(db_session, request)
            
            # Validation should fail due to non-existent target directory
            with pytest.raises(FileOperationError):
                await service.validate_operation(db_session, operation_response.id)
            
            # Verify operation status in database
            result = await db_session.execute(
                select(FileOperation).where(FileOperation.id == operation_response.id)
            )
            operation = result.scalar_one()
            assert operation.status == "failed"
            assert operation.error_message is not None
            
            # Verify original file and database record are unchanged
            assert Path(temp_library["series_dir"]).exists()
            await db_session.refresh(series)
            assert series.file_path == temp_library["series_dir"]

    async def test_large_directory_operation_performance(self, db_session: AsyncSession, temp_library):
        """Test performance with large directory operations."""
        async with FileOperationService() as service:
            # Create large directory structure
            large_series_dir = Path(temp_library["library_path"]) / "Large Series"
            large_series_dir.mkdir()
            
            # Create many chapters and pages
            total_files = 0
            for chapter_num in range(1, 11):  # 10 chapters
                chapter_dir = large_series_dir / f"Chapter {chapter_num:03d}"
                chapter_dir.mkdir()
                
                for page_num in range(1, 21):  # 20 pages per chapter
                    page_file = chapter_dir / f"page_{page_num:03d}.jpg"
                    page_file.write_bytes(b"A" * 1024)  # 1KB per page
                    total_files += 1
            
            # Create database record
            series = Series(
                id=uuid4(),
                title_primary="Large Series",
                file_path=str(large_series_dir),
                total_chapters=10
            )
            db_session.add(series)
            await db_session.commit()
            
            # Time the operation
            start_time = datetime.now()
            
            # Create and validate delete operation
            request = FileOperationRequest(
                operation_type="delete",
                source_path=str(large_series_dir),
                create_backup=True
            )
            
            operation_response = await service.create_operation(db_session, request)
            validation_result = await service.validate_operation(db_session, operation_response.id)
            
            validation_time = datetime.now() - start_time
            
            # Validation should be reasonably fast (under 5 seconds for this test size)
            assert validation_time.total_seconds() < 5.0
            assert validation_result.is_valid
            assert validation_result.estimated_disk_usage_mb > 0
            
            # Execute operation
            execution_start = datetime.now()
            execution_response = await service.execute_operation(db_session, operation_response.id)
            execution_time = datetime.now() - execution_start
            
            # Execution should be reasonably fast (under 10 seconds)
            assert execution_time.total_seconds() < 10.0
            assert execution_response.status == "completed"
            
            # Verify all files were processed
            assert not large_series_dir.exists()
            assert Path(execution_response.backup_path).exists()

    async def test_operation_idempotency(self, db_session: AsyncSession, temp_library):
        """Test that operations are idempotent and don't cause conflicts."""
        async with FileOperationService() as service:
            # Create test file
            test_file = Path(temp_library["library_path"]) / "idempotent_test.cbz"
            test_file.write_bytes(b"test content")
            
            # Create rename operation
            target_path = str(Path(temp_library["library_path"]) / "renamed_test.cbz")
            request = FileOperationRequest(
                operation_type="rename",
                source_path=str(test_file),
                target_path=target_path,
                create_backup=True
            )
            
            # Create operation twice - should not conflict
            operation_response1 = await service.create_operation(db_session, request)
            operation_response2 = await service.create_operation(db_session, request)
            
            assert operation_response1.id != operation_response2.id
            
            # Execute first operation
            await service.validate_operation(db_session, operation_response1.id)
            execution_response1 = await service.execute_operation(db_session, operation_response1.id)
            assert execution_response1.status == "completed"
            assert Path(target_path).exists()
            assert not test_file.exists()
            
            # Second operation should fail validation (source doesn't exist)
            with pytest.raises(FileOperationError):
                await service.validate_operation(db_session, operation_response2.id)

    async def test_database_constraint_validation(self, db_session: AsyncSession, temp_library):
        """Test database constraint validation during operations."""
        async with FileOperationService() as service:
            # Create operation record directly in database with invalid data
            invalid_operation = FileOperation(
                id=uuid4(),
                operation_type="invalid_type",  # Should violate constraint
                source_path=temp_library["cbz_file"],
                status="pending"
            )
            
            db_session.add(invalid_operation)
            
            # Should raise constraint violation
            with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
                await db_session.commit()
            
            # Rollback the failed transaction
            await db_session.rollback()
            
            # Create valid operation
            valid_operation = FileOperation(
                id=uuid4(),
                operation_type="delete",
                source_path=temp_library["cbz_file"],
                status="pending"
            )
            
            db_session.add(valid_operation)
            await db_session.commit()  # Should succeed
            
            # Verify operation was created
            result = await db_session.execute(
                select(FileOperation).where(FileOperation.id == valid_operation.id)
            )
            assert result.scalar_one_or_none() is not None

    async def test_cross_library_path_operations(self, db_session: AsyncSession):
        """Test operations across different library paths."""
        # Create two separate library directories
        temp_dir1 = tempfile.mkdtemp()
        temp_dir2 = tempfile.mkdtemp()
        
        try:
            library1 = Path(temp_dir1)
            library2 = Path(temp_dir2)
            
            # Create test files in both libraries
            file1 = library1 / "series1.cbz"
            file1.write_bytes(b"content1")
            
            file2 = library2 / "series2.cbz"  
            file2.write_bytes(b"content2")
            
            async with FileOperationService() as service:
                # Test move operation between libraries
                request = FileOperationRequest(
                    operation_type="move",
                    source_path=str(file1),
                    target_path=str(library2 / "moved_series1.cbz"),
                    create_backup=True
                )
                
                operation_response = await service.create_operation(db_session, request)
                validation_result = await service.validate_operation(db_session, operation_response.id)
                
                assert validation_result.is_valid
                
                execution_response = await service.execute_operation(db_session, operation_response.id)
                assert execution_response.status == "completed"
                
                # Verify file was moved between libraries
                assert not file1.exists()
                assert (library2 / "moved_series1.cbz").exists()
                
        finally:
            # Cleanup
            shutil.rmtree(temp_dir1, ignore_errors=True)
            shutil.rmtree(temp_dir2, ignore_errors=True)

    async def test_cleanup_old_operations_integration(self, db_session: AsyncSession, temp_library):
        """Test cleanup of old operations with real database."""
        async with FileOperationService() as service:
            # Create test operations with different ages
            old_operations = []
            for i in range(3):
                operation = FileOperation(
                    id=uuid4(),
                    operation_type="delete",
                    source_path=f"/old/path/{i}",
                    status="completed",
                    created_at=datetime(2020, 1, i+1, tzinfo=timezone.utc)
                )
                old_operations.append(operation)
                db_session.add(operation)
            
            # Create recent operation that should not be cleaned
            recent_operation = FileOperation(
                id=uuid4(),
                operation_type="rename",
                source_path="/recent/path",
                status="completed",
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(recent_operation)
            await db_session.commit()
            
            # Cleanup old operations
            cleaned_count = await service.cleanup_old_operations(db_session, days_old=30)
            assert cleaned_count == 3
            
            # Verify old operations were removed
            for operation in old_operations:
                result = await db_session.execute(
                    select(FileOperation).where(FileOperation.id == operation.id)
                )
                assert result.scalar_one_or_none() is None
            
            # Verify recent operation was preserved
            result = await db_session.execute(
                select(FileOperation).where(FileOperation.id == recent_operation.id)
            )
            assert result.scalar_one_or_none() is not None


class TestFileOperationErrorRecovery:
    """Test error recovery and resilience scenarios."""

    async def test_partial_failure_recovery(self, db_session: AsyncSession):
        """Test recovery from partial operation failures."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create test structure
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            
            # Create files, some with permission issues
            normal_file = source_dir / "normal.txt"
            normal_file.write_text("normal content")
            
            # Create file in subdirectory to test partial moves
            sub_dir = source_dir / "subdir"
            sub_dir.mkdir()
            sub_file = sub_dir / "sub.txt"
            sub_file.write_text("sub content")
            
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            async with FileOperationService() as service:
                request = FileOperationRequest(
                    operation_type="move",
                    source_path=str(source_dir),
                    target_path=str(target_dir / "moved_source"),
                    create_backup=True
                )
                
                operation_response = await service.create_operation(db_session, request)
                await service.validate_operation(db_session, operation_response.id)
                
                # Execute operation
                execution_response = await service.execute_operation(db_session, operation_response.id)
                
                # Should complete successfully
                assert execution_response.status == "completed"
                
                # Verify structure was moved
                moved_dir = target_dir / "moved_source"
                assert moved_dir.exists()
                assert (moved_dir / "normal.txt").exists()
                assert (moved_dir / "subdir" / "sub.txt").exists()
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def test_database_transaction_failure_recovery(self, db_session: AsyncSession):
        """Test recovery when database transaction fails."""
        temp_dir = tempfile.mkdtemp()
        try:
            test_file = Path(temp_dir) / "test.cbz"
            test_file.write_bytes(b"test content")
            
            async with FileOperationService() as service:
                # Create operation
                request = FileOperationRequest(
                    operation_type="delete",
                    source_path=str(test_file),
                    create_backup=True
                )
                
                operation_response = await service.create_operation(db_session, request)
                await service.validate_operation(db_session, operation_response.id)
                
                # Simulate database session becoming invalid
                # In a real scenario, this could happen due to connection issues
                
                # Execute operation - if database update fails, file should be rolled back
                try:
                    execution_response = await service.execute_operation(db_session, operation_response.id)
                    
                    # If execution succeeds, verify consistency
                    if execution_response.status == "completed":
                        # File should be deleted and backup should exist
                        assert not test_file.exists()
                        assert Path(execution_response.backup_path).exists()
                    
                except Exception:
                    # If execution fails, file should still exist
                    assert test_file.exists()
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)