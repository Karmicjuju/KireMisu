"""Tests for storage path management functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.storage import StoragePathService
from app.schemas.storage import StoragePathCreate, StoragePathUpdate
from app.models.storage_path import StoragePath


class TestStoragePathService:
    """Test storage path service functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        """Create storage service instance."""
        return StoragePathService(mock_db)

    def test_validate_path_existing_directory(self, service, temp_dir):
        """Test path validation for existing directory."""
        result = service.validate_path(temp_dir)
        
        assert result.path == os.path.normpath(temp_dir)
        assert result.is_valid is True
        assert result.is_accessible is True
        assert result.exists is True
        assert result.is_readable is True
        assert result.error_message is None

    def test_validate_path_nonexistent(self, service):
        """Test path validation for non-existent path."""
        nonexistent_path = "/this/path/does/not/exist"
        result = service.validate_path(nonexistent_path)
        
        assert result.is_valid is False
        assert result.is_accessible is False
        assert result.exists is False
        assert result.error_message == "Path does not exist"

    def test_validate_path_security_blocks_system_dirs(self, service):
        """Test that system directories are blocked."""
        # This test validates the schema validation, not the service
        with pytest.raises(ValueError, match="Path points to system directory"):
            StoragePathCreate(
                name="System",
                path="/etc/passwd"
            )

    def test_validate_path_security_blocks_traversal(self, service):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(ValueError, match="Path points to system directory"):
            StoragePathCreate(
                name="Traversal",
                path="../../../etc/passwd"
            )

    def test_storage_path_create_schema_validation(self):
        """Test storage path creation schema validation."""
        # Valid path
        valid_path = StoragePathCreate(
            name="My Library",
            path="/home/user/manga",
            is_active=True,
            priority=5
        )
        assert valid_path.name == "My Library"
        assert valid_path.path == "/home/user/manga"
        assert valid_path.is_active is True
        assert valid_path.priority == 5

    def test_storage_path_create_schema_reserved_names(self):
        """Test that reserved names are blocked."""
        with pytest.raises(ValueError, match="Reserved name not allowed"):
            StoragePathCreate(
                name="system",
                path="/home/user/manga"
            )

    def test_storage_path_update_schema(self):
        """Test storage path update schema validation."""
        update_data = StoragePathUpdate(
            name="Updated Library",
            is_active=False,
            priority=10
        )
        assert update_data.name == "Updated Library"
        assert update_data.is_active is False
        assert update_data.priority == 10

    @patch('os.access')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_path_permission_denied(self, mock_is_dir, mock_exists, mock_access, service):
        """Test path validation when permission is denied."""
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_access.return_value = False  # No read access
        
        result = service.validate_path("/restricted/path")
        
        assert result.is_accessible is False
        assert result.error_message == "Path is not readable"

    @patch('shutil.disk_usage')
    @patch('os.access')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_path_with_disk_usage(self, mock_is_dir, mock_exists, mock_access, mock_disk_usage, service, temp_dir):
        """Test path validation includes disk usage statistics."""
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_access.return_value = True
        mock_disk_usage.return_value = Mock(total=1000000, free=500000)
        
        result = service.validate_path(temp_dir)
        
        assert result.is_accessible is True
        assert result.total_space_bytes == 1000000
        assert result.free_space_bytes == 500000
        assert result.used_space_bytes == 500000

    def test_network_path_detection_windows_unc(self, service):
        """Test network path detection for Windows UNC paths."""
        result = service._is_network_path("\\\\server\\share\\path")
        assert result is True

    def test_network_path_detection_local_path(self, service):
        """Test that local paths are not detected as network."""
        result = service._is_network_path("/home/user/manga")
        assert result is False