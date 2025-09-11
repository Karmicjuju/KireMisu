import json
import tempfile
import shutil
from typing import Dict, Any
from unittest.mock import patch, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.library_path import LibraryPath
from app.models.user import User
from app.repositories.library_path import LibraryPathRepository
from app.services.library_path import LibraryPathService
from app.schemas.library_path import LibraryPathCreate, LibraryPathUpdate


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
def client(db_session):
    """Create a test client with mocked database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True
    )
    return user


@pytest.fixture
def auth_headers(mock_user):
    """Create authentication headers for API requests."""
    # Mock the authentication dependency
    def get_current_active_user():
        return mock_user
    
    from app.api.v1.endpoints.auth import get_current_active_user as original_auth
    app.dependency_overrides[original_auth] = get_current_active_user
    
    yield {"Authorization": "Bearer mock-token"}
    
    # Clean up
    if original_auth in app.dependency_overrides:
        del app.dependency_overrides[original_auth]


@pytest.fixture
def sample_library_path_data():
    """Sample library path data for testing."""
    return {
        "name": "Test Library",
        "path": "/home/user/test-manga",
        "is_active": True,
        "priority": 5
    }


class TestLibraryPathsAPI:
    """Test cases for library paths API endpoints."""

    def test_create_library_path_success(self, client, auth_headers, sample_library_path_data):
        """Test successful library path creation."""
        response = client.post(
            "/api/v1/library-paths/",
            json=sample_library_path_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_library_path_data["name"]
        assert data["path"] == sample_library_path_data["path"]
        assert data["is_active"] == sample_library_path_data["is_active"]
        assert data["priority"] == sample_library_path_data["priority"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_library_path_invalid_data(self, client, auth_headers):
        """Test library path creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name
            "path": "relative/path",  # Non-absolute path
            "priority": "invalid"  # Invalid priority type
        }
        
        response = client.post(
            "/api/v1/library-paths/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_library_path_duplicate_name(self, client, auth_headers, sample_library_path_data):
        """Test creating library path with duplicate name."""
        # Create first library path
        client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        
        # Try to create second with same name
        duplicate_data = sample_library_path_data.copy()
        duplicate_data["path"] = "/different/path"
        
        response = client.post(
            "/api/v1/library-paths/",
            json=duplicate_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already in use" in response.json()["detail"]

    def test_create_library_path_duplicate_path(self, client, auth_headers, sample_library_path_data):
        """Test creating library path with duplicate path."""
        # Create first library path
        client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        
        # Try to create second with same path
        duplicate_data = sample_library_path_data.copy()
        duplicate_data["name"] = "Different Library"
        
        response = client.post(
            "/api/v1/library-paths/",
            json=duplicate_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already configured" in response.json()["detail"]

    def test_create_library_path_server_error(self, client, auth_headers, sample_library_path_data):
        """Test library path creation with server error."""
        with patch('app.services.library_path.LibraryPathService.create_library_path') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            response = client.post(
                "/api/v1/library-paths/",
                json=sample_library_path_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create library path" in response.json()["detail"]

    def test_get_library_paths_empty(self, client, auth_headers):
        """Test getting library paths when none exist."""
        response = client.get("/api/v1/library-paths/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_library_paths_success(self, client, auth_headers):
        """Test getting library paths successfully."""
        # Create test library paths
        paths_data = [
            {"name": "Library 1", "path": "/path1", "priority": 10, "is_active": True},
            {"name": "Library 2", "path": "/path2", "priority": 5, "is_active": True},
            {"name": "Inactive Library", "path": "/inactive", "priority": 8, "is_active": False},
        ]
        
        for path_data in paths_data:
            client.post("/api/v1/library-paths/", json=path_data, headers=auth_headers)
        
        # Get active only (default)
        response = client.get("/api/v1/library-paths/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2  # Only active paths
        assert all(path["is_active"] for path in data)
        # Should be ordered by priority descending
        assert data[0]["name"] == "Library 1"  # priority 10
        assert data[1]["name"] == "Library 2"  # priority 5

    def test_get_library_paths_include_inactive(self, client, auth_headers):
        """Test getting library paths including inactive ones."""
        # Create test library paths
        paths_data = [
            {"name": "Active", "path": "/active", "is_active": True},
            {"name": "Inactive", "path": "/inactive", "is_active": False},
        ]
        
        for path_data in paths_data:
            client.post("/api/v1/library-paths/", json=path_data, headers=auth_headers)
        
        # Get all including inactive
        response = client.get(
            "/api/v1/library-paths/",
            params={"include_inactive": True},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        active_statuses = {path["name"]: path["is_active"] for path in data}
        assert active_statuses["Active"] is True
        assert active_statuses["Inactive"] is False

    def test_get_library_path_by_id_success(self, client, auth_headers, sample_library_path_data):
        """Test getting library path by ID successfully."""
        # Create library path
        create_response = client.post(
            "/api/v1/library-paths/",
            json=sample_library_path_data,
            headers=auth_headers
        )
        library_path_id = create_response.json()["id"]
        
        # Get library path by ID
        response = client.get(f"/api/v1/library-paths/{library_path_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == library_path_id
        assert data["name"] == sample_library_path_data["name"]

    def test_get_library_path_by_id_not_found(self, client, auth_headers):
        """Test getting library path by non-existent ID."""
        response = client.get("/api/v1/library-paths/999", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_update_library_path_success(self, client, auth_headers, sample_library_path_data):
        """Test updating library path successfully."""
        # Create library path
        create_response = client.post(
            "/api/v1/library-paths/",
            json=sample_library_path_data,
            headers=auth_headers
        )
        library_path_id = create_response.json()["id"]
        
        # Update library path
        update_data = {
            "name": "Updated Library",
            "is_active": False,
            "priority": 15
        }
        
        response = client.put(
            f"/api/v1/library-paths/{library_path_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Library"
        assert data["is_active"] is False
        assert data["priority"] == 15

    def test_update_library_path_not_found(self, client, auth_headers):
        """Test updating non-existent library path."""
        update_data = {"name": "Updated Library"}
        
        response = client.put(
            "/api/v1/library-paths/999",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_library_path_duplicate_name(self, client, auth_headers):
        """Test updating library path with duplicate name."""
        # Create two library paths
        path1_data = {"name": "Library 1", "path": "/path1"}
        path2_data = {"name": "Library 2", "path": "/path2"}
        
        create_response1 = client.post("/api/v1/library-paths/", json=path1_data, headers=auth_headers)
        client.post("/api/v1/library-paths/", json=path2_data, headers=auth_headers)
        
        path1_id = create_response1.json()["id"]
        
        # Try to update path1 with path2's name
        update_data = {"name": "Library 2"}
        
        response = client.put(
            f"/api/v1/library-paths/{path1_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already in use" in response.json()["detail"]

    def test_update_library_path_server_error(self, client, auth_headers, sample_library_path_data):
        """Test library path update with server error."""
        # Create library path
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        with patch('app.services.library_path.LibraryPathService.update_library_path') as mock_update:
            mock_update.side_effect = Exception("Database error")
            
            response = client.put(
                f"/api/v1/library-paths/{library_path_id}",
                json={"name": "Updated"},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to update library path" in response.json()["detail"]

    def test_delete_library_path_success(self, client, auth_headers, sample_library_path_data):
        """Test deleting library path successfully."""
        # Create library path
        create_response = client.post(
            "/api/v1/library-paths/",
            json=sample_library_path_data,
            headers=auth_headers
        )
        library_path_id = create_response.json()["id"]
        
        # Delete library path
        response = client.delete(f"/api/v1/library-paths/{library_path_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's deleted
        get_response = client.get(f"/api/v1/library-paths/{library_path_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_library_path_not_found(self, client, auth_headers):
        """Test deleting non-existent library path."""
        response = client.delete("/api/v1/library-paths/999", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validate_path_success(self, client, auth_headers, temp_directory):
        """Test path validation successfully."""
        with patch('app.services.library_path.LibraryPathService.validate_path') as mock_validate:
            mock_validate.return_value = Mock(
                is_valid=True,
                exists=True,
                is_directory=True,
                is_readable=True,
                is_writable=True,
                error_message=None,
                total_space=1000000000,
                free_space=500000000
            )
            
            response = client.post(
                "/api/v1/library-paths/validate-path",
                params={"path": temp_directory},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is True
            assert data["exists"] is True
            assert data["is_directory"] is True

    def test_validate_path_invalid(self, client, auth_headers):
        """Test validation of invalid path."""
        with patch('app.services.library_path.LibraryPathService.validate_path') as mock_validate:
            mock_validate.return_value = Mock(
                is_valid=False,
                exists=False,
                is_directory=False,
                is_readable=False,
                is_writable=False,
                error_message="Path does not exist",
                total_space=None,
                free_space=None
            )
            
            response = client.post(
                "/api/v1/library-paths/validate-path",
                params={"path": "/nonexistent/path"},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is False
            assert data["error_message"] == "Path does not exist"

    def test_validate_path_server_error(self, client, auth_headers):
        """Test path validation with server error."""
        with patch('app.services.library_path.LibraryPathService.validate_path') as mock_validate:
            mock_validate.side_effect = Exception("Validation error")
            
            response = client.post(
                "/api/v1/library-paths/validate-path",
                params={"path": "/test/path"},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to validate path" in response.json()["detail"]

    def test_validate_library_path_success(self, client, auth_headers, sample_library_path_data):
        """Test validating existing library path."""
        # Create library path
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        with patch('app.services.library_path.LibraryPathService.validate_path') as mock_validate:
            mock_validate.return_value = Mock(
                is_valid=True,
                exists=True,
                is_directory=True,
                is_readable=True,
                is_writable=False,
                error_message="Directory is read-only",
                total_space=1000000000,
                free_space=500000000
            )
            
            response = client.post(f"/api/v1/library-paths/{library_path_id}/validate", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is True
            assert data["is_writable"] is False
            assert "read-only" in data["error_message"]

    def test_validate_library_path_not_found(self, client, auth_headers):
        """Test validating non-existent library path."""
        response = client.post("/api/v1/library-paths/999/validate", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_browse_directory_success(self, client, auth_headers, temp_directory):
        """Test directory browsing successfully."""
        # Create test directory structure
        subdir = temp_directory + "/subdir"
        import os
        os.makedirs(subdir)
        
        with open(temp_directory + "/file.txt", "w") as f:
            f.write("test")
        
        with patch('app.services.library_path.LibraryPathService.browse_directory') as mock_browse:
            mock_browse.return_value = Mock(
                current_path=temp_directory,
                parent_path="/parent",
                items=[
                    Mock(name="subdir", path=subdir, is_directory=True, size=None),
                    Mock(name="file.txt", path=temp_directory + "/file.txt", is_directory=False, size=4)
                ],
                total_items=2
            )
            
            response = client.get(
                f"/api/v1/library-paths/browse/{temp_directory}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["current_path"] == temp_directory
            assert data["total_items"] == 2
            assert len(data["items"]) == 2

    def test_browse_directory_with_hidden_files(self, client, auth_headers, temp_directory):
        """Test directory browsing with hidden files."""
        with patch('app.services.library_path.LibraryPathService.browse_directory') as mock_browse:
            mock_browse.return_value = Mock(
                current_path=temp_directory,
                parent_path=None,
                items=[
                    Mock(name=".hidden", path=temp_directory + "/.hidden", is_directory=True, size=None),
                    Mock(name="visible.txt", path=temp_directory + "/visible.txt", is_directory=False, size=10)
                ],
                total_items=2
            )
            
            response = client.get(
                f"/api/v1/library-paths/browse/{temp_directory}",
                params={"show_hidden": True},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_browse.assert_called_once_with(temp_directory, show_hidden=True)

    def test_browse_directory_not_found(self, client, auth_headers):
        """Test browsing non-existent directory."""
        with patch('app.services.library_path.LibraryPathService.browse_directory') as mock_browse:
            mock_browse.side_effect = FileNotFoundError("Directory not found")
            
            response = client.get("/api/v1/library-paths/browse/nonexistent", headers=auth_headers)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"]

    def test_browse_directory_not_directory(self, client, auth_headers):
        """Test browsing a file path."""
        with patch('app.services.library_path.LibraryPathService.browse_directory') as mock_browse:
            mock_browse.side_effect = NotADirectoryError("Path is not a directory")
            
            response = client.get("/api/v1/library-paths/browse/file.txt", headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "not a directory" in response.json()["detail"]

    def test_browse_directory_permission_error(self, client, auth_headers):
        """Test browsing directory without permissions."""
        with patch('app.services.library_path.LibraryPathService.browse_directory') as mock_browse:
            mock_browse.side_effect = PermissionError("Directory is not accessible")
            
            response = client.get("/api/v1/library-paths/browse/restricted", headers=auth_headers)
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "not accessible" in response.json()["detail"]

    def test_browse_directory_server_error(self, client, auth_headers):
        """Test directory browsing with server error."""
        with patch('app.services.library_path.LibraryPathService.browse_directory') as mock_browse:
            mock_browse.side_effect = Exception("Unexpected error")
            
            response = client.get("/api/v1/library-paths/browse/test", headers=auth_headers)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to browse directory" in response.json()["detail"]

    def test_get_storage_info_success(self, client, auth_headers, sample_library_path_data):
        """Test getting storage info successfully."""
        # Create library path
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        with patch('app.services.library_path.LibraryPathService.get_storage_info') as mock_storage:
            mock_storage.return_value = Mock(
                total_space=1000000000,
                used_space=600000000,
                free_space=400000000,
                usage_percentage=60.0
            )
            
            response = client.get(f"/api/v1/library-paths/{library_path_id}/storage-info", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_space"] == 1000000000
            assert data["usage_percentage"] == 60.0

    def test_get_storage_info_not_found(self, client, auth_headers):
        """Test getting storage info for non-existent library path."""
        with patch('app.services.library_path.LibraryPathService.get_storage_info') as mock_storage:
            mock_storage.return_value = None
            
            response = client.get("/api/v1/library-paths/999/storage-info", headers=auth_headers)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_activate_library_path_success(self, client, auth_headers, sample_library_path_data):
        """Test activating library path successfully."""
        # Create inactive library path
        sample_library_path_data["is_active"] = False
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        response = client.patch(f"/api/v1/library-paths/{library_path_id}/activate", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is True

    def test_activate_library_path_not_found(self, client, auth_headers):
        """Test activating non-existent library path."""
        response = client.patch("/api/v1/library-paths/999/activate", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivate_library_path_success(self, client, auth_headers, sample_library_path_data):
        """Test deactivating library path successfully."""
        # Create active library path
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        response = client.patch(f"/api/v1/library-paths/{library_path_id}/deactivate", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    def test_update_priority_success(self, client, auth_headers, sample_library_path_data):
        """Test updating library path priority successfully."""
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        response = client.patch(
            f"/api/v1/library-paths/{library_path_id}/priority",
            params={"new_priority": 20},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["priority"] == 20

    def test_update_priority_not_found(self, client, auth_headers):
        """Test updating priority of non-existent library path."""
        response = client.patch(
            "/api/v1/library-paths/999/priority",
            params={"new_priority": 20},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_scan_for_manga_directories_success(self, client, auth_headers, sample_library_path_data):
        """Test scanning for manga directories successfully."""
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        with patch('app.services.library_path.LibraryPathService.scan_for_manga_directories') as mock_scan:
            mock_scan.return_value = ["/path/manga1", "/path/subdir/manga2"]
            
            response = client.get(f"/api/v1/library-paths/{library_path_id}/scan-manga", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert "/path/manga1" in data
            assert "/path/subdir/manga2" in data

    def test_scan_for_manga_directories_with_max_depth(self, client, auth_headers, sample_library_path_data):
        """Test scanning with custom max_depth."""
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        with patch('app.services.library_path.LibraryPathService.scan_for_manga_directories') as mock_scan:
            mock_scan.return_value = ["/path/manga1"]
            
            response = client.get(
                f"/api/v1/library-paths/{library_path_id}/scan-manga",
                params={"max_depth": 1},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_scan.assert_called_once_with(library_path_id, max_depth=1)

    def test_scan_for_manga_directories_not_found(self, client, auth_headers):
        """Test scanning for non-existent library path."""
        response = client.get("/api/v1/library-paths/999/scan-manga", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_scan_for_manga_directories_server_error(self, client, auth_headers, sample_library_path_data):
        """Test manga scanning with server error."""
        create_response = client.post("/api/v1/library-paths/", json=sample_library_path_data, headers=auth_headers)
        library_path_id = create_response.json()["id"]
        
        with patch('app.services.library_path.LibraryPathService.scan_for_manga_directories') as mock_scan:
            mock_scan.side_effect = Exception("Scanning error")
            
            response = client.get(f"/api/v1/library-paths/{library_path_id}/scan-manga", headers=auth_headers)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to scan for manga directories" in response.json()["detail"]


class TestLibraryPathsAPIAuthentication:
    """Test authentication requirements for library paths API."""

    def test_endpoints_require_authentication(self, client, sample_library_path_data):
        """Test that all endpoints require authentication."""
        endpoints_methods = [
            ("GET", "/api/v1/library-paths/"),
            ("POST", "/api/v1/library-paths/", sample_library_path_data),
            ("GET", "/api/v1/library-paths/1"),
            ("PUT", "/api/v1/library-paths/1", {"name": "Updated"}),
            ("DELETE", "/api/v1/library-paths/1"),
            ("POST", "/api/v1/library-paths/validate-path?path=/test"),
            ("POST", "/api/v1/library-paths/1/validate"),
            ("GET", "/api/v1/library-paths/browse/test"),
            ("GET", "/api/v1/library-paths/1/storage-info"),
            ("PATCH", "/api/v1/library-paths/1/activate"),
            ("PATCH", "/api/v1/library-paths/1/deactivate"),
            ("PATCH", "/api/v1/library-paths/1/priority?new_priority=10"),
            ("GET", "/api/v1/library-paths/1/scan-manga"),
        ]
        
        for method, endpoint, *data in endpoints_methods:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data[0] if data else None)
            elif method == "PUT":
                response = client.put(endpoint, json=data[0] if data else None)
            elif method == "DELETE":
                response = client.delete(endpoint)
            elif method == "PATCH":
                response = client.patch(endpoint)
            
            # Should return 401 or 403 for unauthenticated requests
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN], \
                f"Endpoint {method} {endpoint} should require authentication"


class TestLibraryPathsAPIErrorHandling:
    """Test error handling in library paths API."""

    def test_invalid_json_request(self, client, auth_headers):
        """Test handling of invalid JSON in requests."""
        response = client.post(
            "/api/v1/library-paths/",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_required_fields(self, client, auth_headers):
        """Test handling of missing required fields."""
        incomplete_data = {"name": "Test Library"}  # Missing path
        
        response = client.post(
            "/api/v1/library-paths/",
            json=incomplete_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_query_parameters(self, client, auth_headers):
        """Test handling of invalid query parameters."""
        response = client.get(
            "/api/v1/library-paths/1/scan-manga",
            params={"max_depth": "invalid"},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_path_parameter(self, client, auth_headers):
        """Test handling of invalid path parameters."""
        response = client.get("/api/v1/library-paths/invalid_id", headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLibraryPathsAPIAdvancedIntegrationScenarios:
    """Test advanced integration scenarios and complex workflows."""

    def test_complete_library_path_lifecycle(self, client, auth_headers):
        """Test complete CRUD lifecycle of a library path."""
        # 1. Create library path
        create_data = {
            "name": "Lifecycle Test",
            "path": "/lifecycle/test",
            "priority": 10,
            "is_active": True
        }
        
        create_response = client.post("/api/v1/library-paths/", json=create_data, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        path_id = create_response.json()["id"]
        
        # 2. Read the created path
        get_response = client.get(f"/api/v1/library-paths/{path_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["name"] == "Lifecycle Test"
        
        # 3. Update the path
        update_data = {"name": "Updated Lifecycle Test", "priority": 20}
        update_response = client.put(f"/api/v1/library-paths/{path_id}", json=update_data, headers=auth_headers)
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["name"] == "Updated Lifecycle Test"
        assert update_response.json()["priority"] == 20
        
        # 4. Deactivate the path
        deactivate_response = client.patch(f"/api/v1/library-paths/{path_id}/deactivate", headers=auth_headers)
        assert deactivate_response.status_code == status.HTTP_200_OK
        assert deactivate_response.json()["is_active"] is False
        
        # 5. Verify it's not in active list
        active_paths_response = client.get("/api/v1/library-paths/", headers=auth_headers)
        assert path_id not in [p["id"] for p in active_paths_response.json()]
        
        # 6. Verify it's in inactive list
        all_paths_response = client.get("/api/v1/library-paths/", params={"include_inactive": True}, headers=auth_headers)
        assert path_id in [p["id"] for p in all_paths_response.json()]
        
        # 7. Reactivate the path
        activate_response = client.patch(f"/api/v1/library-paths/{path_id}/activate", headers=auth_headers)
        assert activate_response.status_code == status.HTTP_200_OK
        assert activate_response.json()["is_active"] is True
        
        # 8. Delete the path
        delete_response = client.delete(f"/api/v1/library-paths/{path_id}", headers=auth_headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # 9. Verify deletion
        final_get_response = client.get(f"/api/v1/library-paths/{path_id}", headers=auth_headers)
        assert final_get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_priority_management_workflow(self, client, auth_headers):
        """Test priority management across multiple paths."""
        # Create multiple paths with different priorities
        paths_data = [
            {"name": "High Priority", "path": "/high", "priority": 100},
            {"name": "Medium Priority", "path": "/medium", "priority": 50},
            {"name": "Low Priority", "path": "/low", "priority": 10},
            {"name": "Zero Priority", "path": "/zero", "priority": 0},
            {"name": "Negative Priority", "path": "/negative", "priority": -10},
        ]
        
        created_paths = []
        for path_data in paths_data:
            response = client.post("/api/v1/library-paths/", json=path_data, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED
            created_paths.append(response.json())
        
        # Verify ordering
        all_paths_response = client.get("/api/v1/library-paths/", headers=auth_headers)
        paths = all_paths_response.json()
        
        # Should be ordered by priority descending
        priorities = [p["priority"] for p in paths]
        assert priorities == [100, 50, 10, 0, -10]
        
        # Update priorities
        for i, path in enumerate(created_paths):
            new_priority = (i + 1) * 5  # 5, 10, 15, 20, 25
            update_response = client.patch(
                f"/api/v1/library-paths/{path['id']}/priority",
                params={"new_priority": new_priority},
                headers=auth_headers
            )
            assert update_response.status_code == status.HTTP_200_OK
            assert update_response.json()["priority"] == new_priority
        
        # Verify new ordering
        updated_paths_response = client.get("/api/v1/library-paths/", headers=auth_headers)
        updated_paths = updated_paths_response.json()
        updated_priorities = [p["priority"] for p in updated_paths]
        assert updated_priorities == [25, 20, 15, 10, 5]

    def test_bulk_operations_consistency(self, client, auth_headers):
        """Test consistency when performing bulk operations."""
        # Create multiple paths
        paths_to_create = [
            {"name": f"Bulk Path {i}", "path": f"/bulk/{i}", "priority": i}
            for i in range(10)
        ]
        
        created_ids = []
        for path_data in paths_to_create:
            response = client.post("/api/v1/library-paths/", json=path_data, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED
            created_ids.append(response.json()["id"])
        
        # Verify all were created
        all_paths_response = client.get("/api/v1/library-paths/", headers=auth_headers)
        assert len(all_paths_response.json()) == 10
        
        # Deactivate half of them
        for path_id in created_ids[:5]:
            deactivate_response = client.patch(f"/api/v1/library-paths/{path_id}/deactivate", headers=auth_headers)
            assert deactivate_response.status_code == status.HTTP_200_OK
        
        # Verify count consistency
        active_response = client.get("/api/v1/library-paths/", headers=auth_headers)
        assert len(active_response.json()) == 5
        
        all_response = client.get("/api/v1/library-paths/", params={"include_inactive": True}, headers=auth_headers)
        assert len(all_response.json()) == 10
        
        # Delete some paths
        for path_id in created_ids[7:]:
            delete_response = client.delete(f"/api/v1/library-paths/{path_id}", headers=auth_headers)
            assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify final count
        final_response = client.get("/api/v1/library-paths/", params={"include_inactive": True}, headers=auth_headers)
        assert len(final_response.json()) == 7

    def test_path_validation_integration_workflow(self, client, auth_headers, temp_directory):
        """Test path validation integrated with path creation."""
        # First validate a path
        with patch('app.services.library_path.LibraryPathService.validate_path') as mock_validate:
            mock_validate.return_value = Mock(
                is_valid=True,
                exists=True,
                is_directory=True,
                is_readable=True,
                is_writable=True,
                error_message=None,
                total_space=1000000000,
                free_space=500000000
            )
            
            validate_response = client.post(
                "/api/v1/library-paths/validate-path",
                params={"path": temp_directory},
                headers=auth_headers
            )
            
            assert validate_response.status_code == status.HTTP_200_OK
            validation_result = validate_response.json()
            assert validation_result["is_valid"] is True
        
        # If validation successful, create the path
        create_data = {
            "name": "Validated Path",
            "path": temp_directory,
            "priority": 1
        }
        
        create_response = client.post("/api/v1/library-paths/", json=create_data, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        path_id = create_response.json()["id"]
        
        # Re-validate existing path
        revalidate_response = client.post(f"/api/v1/library-paths/{path_id}/validate", headers=auth_headers)
        assert revalidate_response.status_code == status.HTTP_200_OK

    def test_unicode_and_special_characters_integration(self, client, auth_headers):
        """Test API handling of unicode and special characters throughout workflow."""
        # Create paths with unicode characters
        unicode_paths = [
            {"name": "日本語 Library", "path": "/home/漫画"},
            {"name": "Español Biblioteca", "path": "/home/cómics"},
            {"name": "Русская библиотека", "path": "/home/манга"},
            {"name": "Special !@#$%^&*() Chars", "path": "/home/special-chars"},
        ]
        
        created_ids = []
        for path_data in unicode_paths:
            response = client.post("/api/v1/library-paths/", json=path_data, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED
            created_ids.append(response.json()["id"])
        
        # Verify all paths are retrievable
        all_paths_response = client.get("/api/v1/library-paths/", headers=auth_headers)
        paths = all_paths_response.json()
        
        created_names = {p["name"] for p in paths if p["id"] in created_ids}
        expected_names = {p["name"] for p in unicode_paths}
        assert created_names == expected_names
        
        # Test updates with unicode
        update_data = {"name": "Updated 日本語 Library"}
        update_response = client.put(f"/api/v1/library-paths/{created_ids[0]}", json=update_data, headers=auth_headers)
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["name"] == "Updated 日本語 Library"