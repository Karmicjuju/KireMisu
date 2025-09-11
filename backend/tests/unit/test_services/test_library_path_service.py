import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.library_path import LibraryPath
from app.services.library_path import LibraryPathService
from app.schemas.library_path import (
    LibraryPathCreate,
    LibraryPathUpdate,
    DirectoryItem,
    DirectoryBrowseResponse,
    PathValidationResult,
    StorageInfo
)


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def library_path_service(db_session):
    """Create a library path service instance."""
    return LibraryPathService(db_session)


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_library_path_create():
    """Sample library path creation data."""
    return LibraryPathCreate(
        name="Test Library",
        path="/home/user/test-manga",
        is_active=True,
        priority=5
    )


class TestLibraryPathServiceCRUD:
    """Test CRUD operations in LibraryPathService."""

    def test_create_library_path_success(self, library_path_service, sample_library_path_create):
        """Test successful library path creation with normalization."""
        # Test path normalization
        sample_library_path_create.path = "/home/user//test-manga/../test-manga/"
        
        library_path = library_path_service.create_library_path(sample_library_path_create)
        
        assert library_path.id is not None
        assert library_path.name == "Test Library"
        # Path should be normalized
        assert library_path.path == os.path.normpath("/home/user//test-manga/../test-manga/")
        assert library_path.is_active is True
        assert library_path.priority == 5

    def test_create_library_path_duplicate_path(self, library_path_service, sample_library_path_create):
        """Test library path creation with duplicate path fails."""
        # Create first library path
        library_path_service.create_library_path(sample_library_path_create)
        
        # Try to create second library path with same path (but normalized)
        duplicate_path = LibraryPathCreate(
            name="Different Library",
            path="/home/user/test-manga/",  # Same path with trailing slash
            is_active=True,
            priority=1
        )
        
        with pytest.raises(ValueError, match="already configured"):
            library_path_service.create_library_path(duplicate_path)

    def test_create_library_path_duplicate_name(self, library_path_service, sample_library_path_create):
        """Test library path creation with duplicate name fails."""
        # Create first library path
        library_path_service.create_library_path(sample_library_path_create)
        
        # Try to create second library path with same name
        duplicate_name = LibraryPathCreate(
            name="Test Library",  # Same name
            path="/home/user/different-manga",
            is_active=True,
            priority=1
        )
        
        with pytest.raises(ValueError, match="already in use"):
            library_path_service.create_library_path(duplicate_name)

    def test_get_library_path_by_id(self, library_path_service, sample_library_path_create):
        """Test getting library path by ID."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        retrieved_path = library_path_service.get_library_path_by_id(created_path.id)
        
        assert retrieved_path is not None
        assert retrieved_path.id == created_path.id
        assert retrieved_path.name == "Test Library"

    def test_get_library_path_by_id_not_found(self, library_path_service):
        """Test getting library path by non-existent ID returns None."""
        path = library_path_service.get_library_path_by_id(999)
        assert path is None

    def test_get_all_library_paths(self, library_path_service):
        """Test getting all library paths."""
        # Create test paths
        paths = [
            LibraryPathCreate(name="Active High", path="/active/high", priority=10, is_active=True),
            LibraryPathCreate(name="Active Low", path="/active/low", priority=1, is_active=True),
            LibraryPathCreate(name="Inactive", path="/inactive", priority=5, is_active=False),
        ]
        
        for path_data in paths:
            library_path_service.create_library_path(path_data)
        
        # Test getting active only (default)
        active_paths = library_path_service.get_all_library_paths()
        assert len(active_paths) == 2
        assert all(path.is_active for path in active_paths)
        
        # Test getting all including inactive
        all_paths = library_path_service.get_all_library_paths(include_inactive=True)
        assert len(all_paths) == 3

    def test_get_active_library_paths(self, library_path_service):
        """Test getting only active library paths."""
        paths = [
            LibraryPathCreate(name="Active", path="/active", is_active=True),
            LibraryPathCreate(name="Inactive", path="/inactive", is_active=False),
        ]
        
        for path_data in paths:
            library_path_service.create_library_path(path_data)
        
        active_paths = library_path_service.get_active_library_paths()
        assert len(active_paths) == 1
        assert active_paths[0].name == "Active"

    def test_update_library_path_success(self, library_path_service, sample_library_path_create):
        """Test successful library path update."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        update_data = LibraryPathUpdate(
            name="Updated Library",
            is_active=False,
            priority=15
        )
        
        updated_path = library_path_service.update_library_path(created_path.id, update_data)
        
        assert updated_path is not None
        assert updated_path.name == "Updated Library"
        assert updated_path.is_active is False
        assert updated_path.priority == 15

    def test_update_library_path_duplicate_name(self, library_path_service):
        """Test updating library path with duplicate name fails."""
        # Create two library paths
        path1_data = LibraryPathCreate(name="Library 1", path="/path1")
        path2_data = LibraryPathCreate(name="Library 2", path="/path2")
        
        path1 = library_path_service.create_library_path(path1_data)
        library_path_service.create_library_path(path2_data)
        
        # Try to update path1 with path2's name
        update_data = LibraryPathUpdate(name="Library 2")
        
        with pytest.raises(ValueError, match="already in use"):
            library_path_service.update_library_path(path1.id, update_data)

    def test_update_library_path_not_found(self, library_path_service):
        """Test updating non-existent library path returns None."""
        update_data = LibraryPathUpdate(name="Updated Library")
        result = library_path_service.update_library_path(999, update_data)
        assert result is None

    def test_delete_library_path(self, library_path_service, sample_library_path_create):
        """Test deleting library path."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        result = library_path_service.delete_library_path(created_path.id)
        assert result is True
        
        # Verify path is deleted
        retrieved_path = library_path_service.get_library_path_by_id(created_path.id)
        assert retrieved_path is None

    def test_delete_library_path_not_found(self, library_path_service):
        """Test deleting non-existent library path returns False."""
        result = library_path_service.delete_library_path(999)
        assert result is False


class TestLibraryPathServiceValidation:
    """Test path validation functionality."""

    def test_validate_path_success(self, library_path_service, temp_directory):
        """Test successful path validation."""
        result = library_path_service.validate_path(temp_directory)
        
        assert result.is_valid is True
        assert result.exists is True
        assert result.is_directory is True
        assert result.is_readable is True
        assert result.is_writable is True
        assert result.error_message is None or "read-only" in result.error_message
        assert result.total_space is not None
        assert result.free_space is not None

    def test_validate_path_not_exists(self, library_path_service):
        """Test validation of non-existent path."""
        result = library_path_service.validate_path("/nonexistent/path")
        
        assert result.is_valid is False
        assert result.exists is False
        assert result.error_message == "Path does not exist"

    def test_validate_path_not_directory(self, library_path_service, temp_directory):
        """Test validation of file path (not directory)."""
        # Create a file
        file_path = os.path.join(temp_directory, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("test")
        
        result = library_path_service.validate_path(file_path)
        
        assert result.is_valid is False
        assert result.exists is True
        assert result.is_directory is False
        assert result.error_message == "Path is not a directory"

    @patch('os.access')
    def test_validate_path_not_readable(self, mock_access, library_path_service, temp_directory):
        """Test validation of non-readable directory."""
        def access_side_effect(path, mode):
            if mode == os.R_OK:
                return False
            return True
        
        mock_access.side_effect = access_side_effect
        
        result = library_path_service.validate_path(temp_directory)
        
        assert result.is_valid is False
        assert result.is_readable is False
        assert result.error_message == "Directory is not readable"

    @patch('os.access')
    def test_validate_path_not_writable(self, mock_access, library_path_service, temp_directory):
        """Test validation of read-only directory."""
        def access_side_effect(path, mode):
            if mode == os.W_OK:
                return False
            return True
        
        mock_access.side_effect = access_side_effect
        
        result = library_path_service.validate_path(temp_directory)
        
        assert result.is_valid is True  # Still valid, just read-only
        assert result.is_readable is True
        assert result.is_writable is False
        assert "read-only" in result.error_message

    @patch('shutil.disk_usage')
    def test_validate_path_disk_usage_error(self, mock_disk_usage, library_path_service, temp_directory):
        """Test validation when disk usage check fails."""
        mock_disk_usage.side_effect = OSError("Permission denied")
        
        result = library_path_service.validate_path(temp_directory)
        
        # Should still be valid, just without disk usage info
        assert result.is_valid is True
        assert result.total_space is None
        assert result.free_space is None

    @patch('os.path.exists')
    def test_validate_path_exception_handling(self, mock_exists, library_path_service):
        """Test validation with unexpected exception."""
        mock_exists.side_effect = PermissionError("Access denied")
        
        result = library_path_service.validate_path("/test/path")
        
        assert result.is_valid is False
        assert "Error validating path" in result.error_message


class TestLibraryPathServiceBrowsing:
    """Test directory browsing functionality."""

    def test_browse_directory_success(self, library_path_service, temp_directory):
        """Test successful directory browsing."""
        # Create test directory structure
        subdir = os.path.join(temp_directory, "subdir")
        os.makedirs(subdir)
        
        file_path = os.path.join(temp_directory, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("test content")
        
        result = library_path_service.browse_directory(temp_directory)
        
        assert isinstance(result, DirectoryBrowseResponse)
        assert result.current_path == temp_directory
        assert result.total_items == 2
        
        # Should have both directory and file
        item_names = {item.name for item in result.items}
        assert "subdir" in item_names
        assert "test_file.txt" in item_names
        
        # Check item properties
        subdir_item = next(item for item in result.items if item.name == "subdir")
        file_item = next(item for item in result.items if item.name == "test_file.txt")
        
        assert subdir_item.is_directory is True
        assert subdir_item.size is None
        assert file_item.is_directory is False
        assert file_item.size is not None

    def test_browse_directory_ordering(self, library_path_service, temp_directory):
        """Test that items are ordered correctly (directories first, then alphabetical)."""
        # Create mixed files and directories
        items = [
            ("z_file.txt", "file"),
            ("a_directory", "dir"),
            ("m_file.txt", "file"),
            ("b_directory", "dir"),
        ]
        
        for name, item_type in items:
            item_path = os.path.join(temp_directory, name)
            if item_type == "dir":
                os.makedirs(item_path)
            else:
                with open(item_path, "w") as f:
                    f.write("test")
        
        result = library_path_service.browse_directory(temp_directory)
        
        # Directories should come first, then files, both alphabetically sorted
        expected_order = ["a_directory", "b_directory", "m_file.txt", "z_file.txt"]
        actual_order = [item.name for item in result.items]
        
        assert actual_order == expected_order

    def test_browse_directory_hidden_files(self, library_path_service, temp_directory):
        """Test browsing with hidden files."""
        # Create visible and hidden items
        visible_file = os.path.join(temp_directory, "visible.txt")
        hidden_file = os.path.join(temp_directory, ".hidden.txt")
        hidden_dir = os.path.join(temp_directory, ".hidden_dir")
        
        with open(visible_file, "w") as f:
            f.write("visible")
        with open(hidden_file, "w") as f:
            f.write("hidden")
        os.makedirs(hidden_dir)
        
        # Browse without hidden files (default)
        result_no_hidden = library_path_service.browse_directory(temp_directory)
        names_no_hidden = {item.name for item in result_no_hidden.items}
        assert "visible.txt" in names_no_hidden
        assert ".hidden.txt" not in names_no_hidden
        assert ".hidden_dir" not in names_no_hidden
        
        # Browse with hidden files
        result_with_hidden = library_path_service.browse_directory(temp_directory, show_hidden=True)
        names_with_hidden = {item.name for item in result_with_hidden.items}
        assert "visible.txt" in names_with_hidden
        assert ".hidden.txt" in names_with_hidden
        assert ".hidden_dir" in names_with_hidden

    def test_browse_directory_parent_path(self, library_path_service, temp_directory):
        """Test parent path calculation."""
        # Browse root-level directory
        result = library_path_service.browse_directory(temp_directory)
        assert result.parent_path is not None  # Should have a parent
        
        # Browse subdirectory
        subdir = os.path.join(temp_directory, "subdir")
        os.makedirs(subdir)
        
        result = library_path_service.browse_directory(subdir)
        assert result.parent_path == temp_directory

    def test_browse_directory_not_exists(self, library_path_service):
        """Test browsing non-existent directory."""
        with pytest.raises(FileNotFoundError):
            library_path_service.browse_directory("/nonexistent/path")

    def test_browse_directory_not_directory(self, library_path_service, temp_directory):
        """Test browsing a file path."""
        file_path = os.path.join(temp_directory, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("test")
        
        with pytest.raises(NotADirectoryError):
            library_path_service.browse_directory(file_path)

    @patch('os.access')
    def test_browse_directory_not_readable(self, mock_access, library_path_service, temp_directory):
        """Test browsing non-readable directory."""
        mock_access.return_value = False
        
        with pytest.raises(PermissionError):
            library_path_service.browse_directory(temp_directory)

    @patch('os.listdir')
    def test_browse_directory_listdir_error(self, mock_listdir, library_path_service, temp_directory):
        """Test browsing when listing directory contents fails."""
        mock_listdir.side_effect = PermissionError("Access denied")
        
        with pytest.raises(PermissionError):
            library_path_service.browse_directory(temp_directory)

    def test_browse_directory_skip_inaccessible_items(self, library_path_service, temp_directory):
        """Test that inaccessible items are skipped gracefully."""
        # Create a file we can access
        good_file = os.path.join(temp_directory, "good_file.txt")
        with open(good_file, "w") as f:
            f.write("accessible")
        
        # Mock os.stat to fail for certain files
        original_stat = os.stat
        
        def stat_side_effect(path):
            if "bad_file" in path:
                raise PermissionError("Access denied")
            return original_stat(path)
        
        # Create a "bad" file that will cause stat to fail
        bad_file = os.path.join(temp_directory, "bad_file.txt")
        with open(bad_file, "w") as f:
            f.write("inaccessible")
        
        with patch('os.stat', side_effect=stat_side_effect):
            result = library_path_service.browse_directory(temp_directory)
            
            # Should only have the good file
            names = {item.name for item in result.items}
            assert "good_file.txt" in names
            assert "bad_file.txt" not in names


class TestLibraryPathServiceStorageInfo:
    """Test storage information functionality."""

    def test_get_storage_info_success(self, library_path_service, sample_library_path_create):
        """Test getting storage info for existing library path."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = (1000000000, 600000000, 400000000)  # 1GB total, 600MB used, 400MB free
            
            storage_info = library_path_service.get_storage_info(created_path.id)
            
            assert storage_info is not None
            assert isinstance(storage_info, StorageInfo)
            assert storage_info.total_space == 1000000000
            assert storage_info.used_space == 600000000
            assert storage_info.free_space == 400000000
            assert storage_info.usage_percentage == 60.0

    def test_get_storage_info_not_found(self, library_path_service):
        """Test getting storage info for non-existent library path."""
        storage_info = library_path_service.get_storage_info(999)
        assert storage_info is None

    def test_get_storage_info_disk_usage_error(self, library_path_service, sample_library_path_create):
        """Test getting storage info when disk usage check fails."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.side_effect = OSError("Permission denied")
            
            storage_info = library_path_service.get_storage_info(created_path.id)
            assert storage_info is None

    def test_get_storage_info_zero_total_space(self, library_path_service, sample_library_path_create):
        """Test storage info calculation with zero total space."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = (0, 0, 0)  # Zero space
            
            storage_info = library_path_service.get_storage_info(created_path.id)
            
            assert storage_info is not None
            assert storage_info.usage_percentage == 0.0


class TestLibraryPathServiceAdditionalEdgeCases:
    """Test additional edge cases and error scenarios."""

    def test_create_library_path_path_normalization_edge_cases(self, library_path_service):
        """Test path normalization with various edge cases."""
        test_cases = [
            ("/path//with//double//slashes/", "/path/with/double/slashes"),
            ("/path/with/../parent/reference", "/path/parent/reference"),
            ("/path/./current/./reference", "/path/current/reference"),
            ("/path/trailing/slash/", "/path/trailing/slash"),
        ]
        
        for i, (input_path, expected_normalized) in enumerate(test_cases):
            path_data = LibraryPathCreate(
                name=f"Test Path {i}",
                path=input_path,
                is_active=True,
                priority=i
            )
            
            library_path = library_path_service.create_library_path(path_data)
            assert library_path.path == os.path.normpath(expected_normalized)

    def test_validate_path_with_unicode_characters(self, library_path_service, temp_directory):
        """Test path validation with unicode characters in path."""
        unicode_subdir = os.path.join(temp_directory, "测试目录")  # Chinese characters
        os.makedirs(unicode_subdir, exist_ok=True)
        
        result = library_path_service.validate_path(unicode_subdir)
        
        assert result.exists is True
        assert result.is_directory is True
        assert result.is_valid is True

    def test_browse_directory_with_unicode_filenames(self, library_path_service, temp_directory):
        """Test directory browsing with unicode filenames."""
        # Create files with unicode names
        unicode_files = ["日本語.txt", "español.txt", "français.txt", "русский.txt"]
        
        for filename in unicode_files:
            filepath = os.path.join(temp_directory, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("test content")
        
        result = library_path_service.browse_directory(temp_directory)
        
        assert result.total_items == len(unicode_files)
        found_names = {item.name for item in result.items}
        for expected_name in unicode_files:
            assert expected_name in found_names

    def test_browse_directory_with_symlinks(self, library_path_service, temp_directory):
        """Test directory browsing behavior with symbolic links."""
        # Create a regular file
        regular_file = os.path.join(temp_directory, "regular.txt")
        with open(regular_file, "w") as f:
            f.write("regular file")
        
        # Create a symbolic link (if supported on the platform)
        try:
            symlink_path = os.path.join(temp_directory, "symlink.txt")
            os.symlink(regular_file, symlink_path)
            
            result = library_path_service.browse_directory(temp_directory)
            
            # Should include both regular file and symlink
            assert result.total_items >= 2
            names = {item.name for item in result.items}
            assert "regular.txt" in names
            assert "symlink.txt" in names
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform, skip this test
            pytest.skip("Symbolic links not supported on this platform")

    def test_get_storage_info_with_very_large_numbers(self, library_path_service, sample_library_path_create):
        """Test storage info calculation with very large numbers."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            # Test with very large numbers (petabytes)
            total = 1024 * 1024 * 1024 * 1024 * 1024  # 1 PB
            used = int(total * 0.75)  # 75% used
            free = total - used
            mock_disk_usage.return_value = (total, used, free)
            
            storage_info = library_path_service.get_storage_info(created_path.id)
            
            assert storage_info is not None
            assert storage_info.total_space == total
            assert storage_info.used_space == used
            assert storage_info.free_space == free
            assert storage_info.usage_percentage == 75.0

    def test_service_with_database_connection_issues(self, library_path_service, sample_library_path_create):
        """Test service behavior when database operations fail."""
        # This test verifies that service methods properly propagate repository errors
        with patch.object(library_path_service.library_path_repo, 'create_library_path') as mock_create:
            mock_create.side_effect = Exception("Database connection lost")
            
            with pytest.raises(Exception, match="Database connection lost"):
                library_path_service.create_library_path(sample_library_path_create)

    def test_reorder_priorities_with_empty_list(self, library_path_service):
        """Test reordering priorities with empty input list."""
        result = library_path_service.reorder_priorities([])
        assert result == []

    def test_reorder_priorities_with_duplicate_ids(self, library_path_service, sample_library_path_create):
        """Test reordering priorities with duplicate path IDs in input."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Try to update the same path multiple times
        reorder_data = [
            (created_path.id, 10),
            (created_path.id, 20),  # Duplicate ID with different priority
        ]
        
        updated_paths = library_path_service.reorder_priorities(reorder_data)
        
        # Should process both updates, but only return unique paths
        assert len(updated_paths) == 2  # Both operations succeed
        # Final priority should be 20 (last update)
        final_path = library_path_service.get_library_path_by_id(created_path.id)
        assert final_path.priority == 20

    def test_scan_for_manga_directories_with_max_depth_zero(self, library_path_service, sample_library_path_create, temp_directory):
        """Test manga scanning with max_depth=0 (should scan only root level)."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Add manga file directly in root
        with open(os.path.join(temp_directory, "root_manga.cbz"), "w") as f:
            f.write("root manga")
        
        # Add manga file in subdirectory
        subdir = os.path.join(temp_directory, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "sub_manga.cbz"), "w") as f:
            f.write("sub manga")
        
        # With max_depth=0, should not scan at all (depth > max_depth immediately)
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id, max_depth=0)
        
        # With current implementation, max_depth=0 means don't go deeper than current level
        # But since scanning starts at depth 0, it should still find root level
        assert temp_directory in manga_directories or len(manga_directories) == 0

    def test_validate_path_with_very_long_path(self, library_path_service):
        """Test path validation with very long path names."""
        # Create a very long path (near filesystem limits)
        base_path = "/very/long/path"
        long_component = "a" * 200  # Very long directory name
        very_long_path = base_path + "/" + long_component
        
        result = library_path_service.validate_path(very_long_path)
        
        # Should handle long paths gracefully
        assert result.is_valid is False
        assert result.exists is False
        assert "does not exist" in result.error_message


class TestLibraryPathServicePriorityManagement:
    """Test priority management functionality."""

    def test_update_priority_success(self, library_path_service, sample_library_path_create):
        """Test updating library path priority."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        updated_path = library_path_service.update_priority(created_path.id, 20)
        
        assert updated_path is not None
        assert updated_path.priority == 20

    def test_update_priority_not_found(self, library_path_service):
        """Test updating priority of non-existent library path."""
        result = library_path_service.update_priority(999, 10)
        assert result is None

    def test_activate_deactivate_library_path(self, library_path_service, sample_library_path_create):
        """Test activating and deactivating library paths."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Deactivate
        deactivated_path = library_path_service.deactivate_library_path(created_path.id)
        assert deactivated_path is not None
        assert deactivated_path.is_active is False
        
        # Activate
        activated_path = library_path_service.activate_library_path(created_path.id)
        assert activated_path is not None
        assert activated_path.is_active is True

    def test_reorder_priorities_success(self, library_path_service):
        """Test reordering multiple library path priorities."""
        # Create multiple library paths
        paths_data = [
            LibraryPathCreate(name="Path 1", path="/path1", priority=1),
            LibraryPathCreate(name="Path 2", path="/path2", priority=2),
            LibraryPathCreate(name="Path 3", path="/path3", priority=3),
        ]
        
        created_paths = []
        for path_data in paths_data:
            created_paths.append(library_path_service.create_library_path(path_data))
        
        # Reorder priorities
        reorder_data = [
            (created_paths[0].id, 10),
            (created_paths[1].id, 20),
            (created_paths[2].id, 5),
        ]
        
        updated_paths = library_path_service.reorder_priorities(reorder_data)
        
        assert len(updated_paths) == 3
        # Check that priorities were updated
        path_priorities = {path.id: path.priority for path in updated_paths}
        assert path_priorities[created_paths[0].id] == 10
        assert path_priorities[created_paths[1].id] == 20
        assert path_priorities[created_paths[2].id] == 5

    def test_reorder_priorities_partial_failure(self, library_path_service):
        """Test reordering with some non-existent paths."""
        path_data = LibraryPathCreate(name="Path 1", path="/path1", priority=1)
        created_path = library_path_service.create_library_path(path_data)
        
        # Mix valid and invalid IDs
        reorder_data = [
            (created_path.id, 10),
            (999, 20),  # Non-existent path
        ]
        
        updated_paths = library_path_service.reorder_priorities(reorder_data)
        
        # Should only return the successfully updated path
        assert len(updated_paths) == 1
        assert updated_paths[0].id == created_path.id
        assert updated_paths[0].priority == 10

    def test_get_next_priority(self, library_path_service):
        """Test getting next available priority."""
        # Initially should be 1 (0 + 1)
        assert library_path_service.get_next_priority() == 1
        
        # Create some paths
        priorities = [5, 10, 3]
        for i, priority in enumerate(priorities):
            path_data = LibraryPathCreate(name=f"Path {i}", path=f"/path{i}", priority=priority)
            library_path_service.create_library_path(path_data)
        
        # Next priority should be highest + 1
        assert library_path_service.get_next_priority() == 11

    def test_activate_deactivate_nonexistent_paths(self, library_path_service):
        """Test activating/deactivating non-existent library paths."""
        # Test activating non-existent path
        result = library_path_service.activate_library_path(999)
        assert result is None
        
        # Test deactivating non-existent path
        result = library_path_service.deactivate_library_path(999)
        assert result is None

    def test_update_priority_with_negative_values(self, library_path_service, sample_library_path_create):
        """Test updating priority with negative values."""
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Update to negative priority
        updated_path = library_path_service.update_priority(created_path.id, -10)
        
        assert updated_path is not None
        assert updated_path.priority == -10

    def test_get_next_priority_with_negative_priorities(self, library_path_service):
        """Test getting next priority when all existing priorities are negative."""
        # Create paths with negative priorities
        priorities = [-10, -5, -15]
        for i, priority in enumerate(priorities):
            path_data = LibraryPathCreate(name=f"Path {i}", path=f"/path{i}", priority=priority)
            library_path_service.create_library_path(path_data)
        
        # Next priority should be highest (least negative) + 1
        next_priority = library_path_service.get_next_priority()
        assert next_priority == -4  # -5 + 1


class TestLibraryPathServiceMangaScanning:
    """Test manga directory scanning functionality."""

    def test_scan_for_manga_directories_success(self, library_path_service, sample_library_path_create, temp_directory):
        """Test successful manga directory scanning."""
        # Update sample path to use temp directory
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create directory structure with manga files
        manga_dir1 = os.path.join(temp_directory, "manga1")
        manga_dir2 = os.path.join(temp_directory, "subdir", "manga2")
        no_manga_dir = os.path.join(temp_directory, "no_manga")
        
        os.makedirs(manga_dir1)
        os.makedirs(manga_dir2)
        os.makedirs(no_manga_dir)
        
        # Add manga files
        with open(os.path.join(manga_dir1, "chapter1.cbz"), "w") as f:
            f.write("dummy")
        with open(os.path.join(manga_dir2, "volume1.pdf"), "w") as f:
            f.write("dummy")
        with open(os.path.join(manga_dir2, "page1.jpg"), "w") as f:
            f.write("dummy")
        
        # Add non-manga file to no_manga_dir
        with open(os.path.join(no_manga_dir, "readme.txt"), "w") as f:
            f.write("dummy")
        
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
        
        assert len(manga_directories) == 2
        assert manga_dir1 in manga_directories
        assert manga_dir2 in manga_directories
        assert no_manga_dir not in manga_directories
        # Should be sorted
        assert manga_directories == sorted(manga_directories)

    def test_scan_for_manga_directories_max_depth(self, library_path_service, sample_library_path_create, temp_directory):
        """Test manga scanning respects max_depth parameter."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create nested structure
        shallow_dir = os.path.join(temp_directory, "shallow")
        deep_dir = os.path.join(temp_directory, "level1", "level2", "level3", "deep")
        
        os.makedirs(shallow_dir)
        os.makedirs(deep_dir)
        
        # Add manga files
        with open(os.path.join(shallow_dir, "chapter1.cbz"), "w") as f:
            f.write("dummy")
        with open(os.path.join(deep_dir, "chapter1.cbz"), "w") as f:
            f.write("dummy")
        
        # Scan with max_depth=2 (should find both)
        manga_dirs_depth2 = library_path_service.scan_for_manga_directories(created_path.id, max_depth=2)
        assert len(manga_dirs_depth2) == 2
        
        # Scan with max_depth=1 (should only find shallow)
        manga_dirs_depth1 = library_path_service.scan_for_manga_directories(created_path.id, max_depth=1)
        assert len(manga_dirs_depth1) == 1
        assert shallow_dir in manga_dirs_depth1

    def test_scan_for_manga_directories_not_found(self, library_path_service):
        """Test scanning non-existent library path returns empty list."""
        manga_directories = library_path_service.scan_for_manga_directories(999)
        assert manga_directories == []

    def test_scan_for_manga_directories_permission_error(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning handles permission errors gracefully."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create directory structure
        manga_dir = os.path.join(temp_directory, "manga")
        os.makedirs(manga_dir)
        
        # Add manga file
        with open(os.path.join(manga_dir, "chapter1.cbz"), "w") as f:
            f.write("dummy")
        
        # Mock os.listdir to raise PermissionError
        original_listdir = os.listdir
        
        def listdir_side_effect(path):
            if path == temp_directory:
                raise PermissionError("Access denied")
            return original_listdir(path)
        
        with patch('os.listdir', side_effect=listdir_side_effect):
            manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
            # Should return empty list, not raise exception
            assert manga_directories == []

    def test_scan_manga_file_extension_detection(self, library_path_service, sample_library_path_create, temp_directory):
        """Test that manga file extensions are detected correctly."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Test different file extensions
        test_extensions = [
            (".cbz", True),
            (".cbr", True),
            (".zip", True),
            (".rar", True),
            (".pdf", True),
            (".jpg", True),
            (".jpeg", True),
            (".png", True),
            (".gif", True),
            (".webp", True),
            (".txt", False),
            (".doc", False),
            (".mp4", False),
        ]
        
        for i, (ext, should_be_manga) in enumerate(test_extensions):
            test_dir = os.path.join(temp_directory, f"test_{i}")
            os.makedirs(test_dir)
            
            test_file = os.path.join(test_dir, f"file{ext}")
            with open(test_file, "w") as f:
                f.write("dummy")
        
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
        
        # Count expected manga directories
        expected_count = sum(1 for ext, should_be_manga in test_extensions if should_be_manga)
        assert len(manga_directories) == expected_count

    def test_scan_for_manga_directories_case_insensitive(self, library_path_service, sample_library_path_create, temp_directory):
        """Test that file extension detection is case insensitive."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create directories with uppercase extensions
        case_test_dir = os.path.join(temp_directory, "case_test")
        os.makedirs(case_test_dir)
        
        # Add files with mixed case extensions
        extensions = [".CBZ", ".JPG", ".PDF", ".Png"]
        for ext in extensions:
            test_file = os.path.join(case_test_dir, f"file{ext}")
            with open(test_file, "w") as f:
                f.write("dummy")
        
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
        
        assert len(manga_directories) == 1
        assert case_test_dir in manga_directories

    def test_scan_for_manga_directories_empty_library_path(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning empty library path directory."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Empty directory - no subdirectories
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
        
        assert manga_directories == []

    def test_scan_for_manga_directories_with_subdirectories_no_manga(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning directories with subdirectories but no manga files."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create nested directory structure without manga files
        for i in range(3):
            level_dir = os.path.join(temp_directory, f"level_{i}")
            os.makedirs(level_dir)
            
            # Add non-manga files
            with open(os.path.join(level_dir, "readme.txt"), "w") as f:
                f.write("not manga")
            with open(os.path.join(level_dir, "data.json"), "w") as f:
                f.write("{}")
        
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
        
        assert manga_directories == []

    def test_scan_for_manga_directories_mixed_files_and_subdirs(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning directories with both files and subdirectories at same level."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create files directly in temp_directory (should not be considered a manga directory unless it has manga files)
        with open(os.path.join(temp_directory, "manga.cbz"), "w") as f:
            f.write("manga file")
        
        # Create subdirectory with manga files
        manga_subdir = os.path.join(temp_directory, "manga_subdir")
        os.makedirs(manga_subdir)
        with open(os.path.join(manga_subdir, "chapter1.jpg"), "w") as f:
            f.write("image")
        
        manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
        
        # Both root directory and subdirectory should be detected
        assert len(manga_directories) == 2
        assert temp_directory in manga_directories
        assert manga_subdir in manga_directories

    def test_scan_for_manga_directories_exception_in_scanning(self, library_path_service, sample_library_path_create, temp_directory):
        """Test that scanning handles exceptions gracefully and continues."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create a directory that will work
        good_dir = os.path.join(temp_directory, "good")
        os.makedirs(good_dir)
        with open(os.path.join(good_dir, "manga.cbz"), "w") as f:
            f.write("manga")
        
        # Mock os.listdir to fail for the temp_directory but work for subdirectories
        original_listdir = os.listdir
        
        def listdir_side_effect(path):
            if path == temp_directory:
                raise OSError("Permission denied")
            return original_listdir(path)
        
        with patch('os.listdir', side_effect=listdir_side_effect):
            manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
            # Should handle the exception and return empty list
            assert manga_directories == []

    def test_scan_for_manga_directories_with_broken_symlinks(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning handles broken symbolic links gracefully."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create a regular directory with manga
        good_dir = os.path.join(temp_directory, "good_dir")
        os.makedirs(good_dir)
        with open(os.path.join(good_dir, "manga.cbz"), "w") as f:
            f.write("manga")
        
        try:
            # Create a broken symlink
            broken_link = os.path.join(temp_directory, "broken_link")
            os.symlink("/nonexistent/target", broken_link)
            
            manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
            
            # Should find the good directory and handle broken symlink gracefully
            assert good_dir in manga_directories
            # Broken symlink should not cause the scan to fail
            
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform, skip this test
            pytest.skip("Symbolic links not supported on this platform")

    def test_scan_for_manga_directories_os_error_in_is_manga_directory(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning when is_manga_directory check fails due to OS error."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create directory structure
        test_dir = os.path.join(temp_directory, "test_dir")
        os.makedirs(test_dir)
        
        # Mock os.listdir to fail when checking for manga files
        original_listdir = os.listdir
        
        def listdir_side_effect(path):
            if path == test_dir:
                raise OSError("Permission denied")
            return original_listdir(path)
        
        with patch('os.listdir', side_effect=listdir_side_effect):
            manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
            # Should not include the problematic directory
            assert test_dir not in manga_directories

    def test_scan_for_manga_directories_os_error_in_scan_directory(self, library_path_service, sample_library_path_create, temp_directory):
        """Test scanning when scan_directory encounters OS errors on subdirectories."""
        sample_library_path_create.path = temp_directory
        created_path = library_path_service.create_library_path(sample_library_path_create)
        
        # Create directory structure
        good_dir = os.path.join(temp_directory, "good_dir")
        bad_dir = os.path.join(temp_directory, "bad_dir")
        os.makedirs(good_dir)
        os.makedirs(bad_dir)
        
        # Add manga file to good directory
        with open(os.path.join(good_dir, "manga.cbz"), "w") as f:
            f.write("manga")
        
        # Mock os.listdir to work for temp_directory and good_dir but fail for bad_dir
        original_listdir = os.listdir
        
        def listdir_side_effect(path):
            if path == bad_dir:
                raise PermissionError("Permission denied")
            return original_listdir(path)
        
        with patch('os.listdir', side_effect=listdir_side_effect):
            manga_directories = library_path_service.scan_for_manga_directories(created_path.id)
            # Should still find the good directory
            assert good_dir in manga_directories
            assert bad_dir not in manga_directories