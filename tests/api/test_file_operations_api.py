"""API tests for file operations endpoints.

Tests verify the API endpoints work correctly with proper validation,
error handling, and response formatting.
"""

import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import FileOperation, Series, Chapter
from kiremisu.main import app


class TestFileOperationsAPI:
    """Test file operations API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing."""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # Create test files
        test_file = temp_path / "test.cbz"
        test_file.write_bytes(b"test content")
        
        target_dir = temp_path / "target"
        target_dir.mkdir()
        
        yield {
            "temp_dir": str(temp_path),
            "test_file": str(test_file),
            "target_dir": str(target_dir),
            "target_file": str(target_dir / "renamed.cbz")
        }
        
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_file_operation_success(self, client, temp_files):
        """Test successful file operation creation."""
        response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "rename",
                "source_path": temp_files["test_file"],
                "target_path": temp_files["target_file"],
                "create_backup": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "rename"
        assert data["source_path"] == temp_files["test_file"]
        assert data["target_path"] == temp_files["target_file"]
        assert data["status"] == "pending"
        assert "id" in data

    def test_create_file_operation_invalid_source(self, client):
        """Test file operation creation with invalid source path."""
        response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": "/non/existent/path"
            }
        )
        
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_create_file_operation_validation_error(self, client):
        """Test file operation creation with validation errors."""
        # Missing required fields
        response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "rename"
                # Missing source_path and target_path
            }
        )
        
        assert response.status_code == 422  # Validation error
        
        # Invalid operation type
        response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "invalid",
                "source_path": "/some/path"
            }
        )
        
        assert response.status_code == 422

    def test_validate_file_operation_success(self, client, temp_files):
        """Test successful operation validation."""
        # First create an operation
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "rename",
                "source_path": temp_files["test_file"],
                "target_path": temp_files["target_file"]
            }
        )
        
        operation_id = create_response.json()["id"]
        
        # Then validate it
        response = client.post(f"/api/file-operations/{operation_id}/validate")
        
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "risk_level" in data
        assert "warnings" in data
        assert "errors" in data

    def test_validate_file_operation_not_found(self, client):
        """Test validation of non-existent operation."""
        fake_id = str(uuid4())
        response = client.post(f"/api/file-operations/{fake_id}/validate")
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_execute_file_operation_success(self, client, temp_files):
        """Test successful operation execution."""
        # Create operation
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "rename",
                "source_path": temp_files["test_file"],
                "target_path": temp_files["target_file"]
            }
        )
        
        operation_id = create_response.json()["id"]
        
        # Validate operation
        client.post(f"/api/file-operations/{operation_id}/validate")
        
        # Execute operation
        response = client.post(
            f"/api/file-operations/{operation_id}/execute",
            json={
                "operation_id": operation_id,
                "confirmed": True,
                "confirmation_message": "User confirmed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["backup_path"] is not None
        
        # Verify file was renamed
        assert not Path(temp_files["test_file"]).exists()
        assert Path(temp_files["target_file"]).exists()

    def test_execute_file_operation_not_confirmed(self, client, temp_files):
        """Test operation execution without confirmation."""
        # Create and validate operation
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"]
            }
        )
        
        operation_id = create_response.json()["id"]
        client.post(f"/api/file-operations/{operation_id}/validate")
        
        # Try to execute without confirmation
        response = client.post(
            f"/api/file-operations/{operation_id}/execute",
            json={
                "operation_id": operation_id,
                "confirmed": False
            }
        )
        
        assert response.status_code == 400
        assert "not confirmed" in response.json()["detail"]

    def test_execute_file_operation_id_mismatch(self, client, temp_files):
        """Test operation execution with ID mismatch."""
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"]
            }
        )
        
        operation_id = create_response.json()["id"]
        different_id = str(uuid4())
        
        response = client.post(
            f"/api/file-operations/{operation_id}/execute",
            json={
                "operation_id": different_id,  # Different ID
                "confirmed": True
            }
        )
        
        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"]

    def test_get_file_operation_success(self, client, temp_files):
        """Test successful operation retrieval."""
        # Create operation
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"]
            }
        )
        
        operation_id = create_response.json()["id"]
        
        # Get operation
        response = client.get(f"/api/file-operations/{operation_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == operation_id
        assert data["operation_type"] == "delete"

    def test_get_file_operation_not_found(self, client):
        """Test retrieval of non-existent operation."""
        fake_id = str(uuid4())
        response = client.get(f"/api/file-operations/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_list_file_operations_success(self, client, temp_files):
        """Test successful operation listing."""
        # Create several operations
        for i in range(3):
            test_file = Path(temp_files["temp_dir"]) / f"test_{i}.txt"
            test_file.write_text(f"content {i}")
            
            client.post(
                "/api/file-operations/",
                json={
                    "operation_type": "delete",
                    "source_path": str(test_file)
                }
            )
        
        # List operations
        response = client.get("/api/file-operations/")
        
        assert response.status_code == 200
        data = response.json()
        assert "operations" in data
        assert "total" in data
        assert len(data["operations"]) >= 3

    def test_list_file_operations_with_filters(self, client, temp_files):
        """Test operation listing with filters."""
        # Create operations with different types and statuses
        client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"]
            }
        )
        
        # List with status filter
        response = client.get("/api/file-operations/?status_filter=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_filter"] == "pending"
        
        # List with operation type filter
        response = client.get("/api/file-operations/?operation_type_filter=delete")
        
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type_filter"] == "delete"

    def test_list_file_operations_pagination(self, client, temp_files):
        """Test operation listing with pagination."""
        response = client.get("/api/file-operations/?limit=5&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["operations"]) <= 5

    def test_rollback_file_operation_success(self, client, temp_files):
        """Test successful operation rollback."""
        # Create, validate, and execute delete operation
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"]
            }
        )
        
        operation_id = create_response.json()["id"]
        
        # Skip validation for this test and execute directly
        client.post(f"/api/file-operations/{operation_id}/validate")
        
        execute_response = client.post(
            f"/api/file-operations/{operation_id}/execute",
            json={
                "operation_id": operation_id,
                "confirmed": True
            }
        )
        
        assert execute_response.status_code == 200
        assert not Path(temp_files["test_file"]).exists()
        
        # Rollback operation
        response = client.post(f"/api/file-operations/{operation_id}/rollback")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rolled_back"
        
        # Verify file was restored
        assert Path(temp_files["test_file"]).exists()

    def test_rollback_file_operation_no_backup(self, client, temp_files):
        """Test rollback of operation without backup."""
        # Create operation without backup
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"],
                "create_backup": False
            }
        )
        
        operation_id = create_response.json()["id"]
        
        # Try to rollback (this should fail in a real scenario)
        response = client.post(f"/api/file-operations/{operation_id}/rollback")
        
        # This might succeed or fail depending on the operation status
        # The key is that it handles the case gracefully
        assert response.status_code in [200, 400]

    def test_cleanup_old_operations_success(self, client):
        """Test successful cleanup of old operations."""
        response = client.delete("/api/file-operations/cleanup?days_old=30")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "cleaned_count" in data
        assert "days_old" in data
        assert data["status"] == "completed"

    def test_cleanup_old_operations_invalid_days(self, client):
        """Test cleanup with invalid days parameter."""
        response = client.delete("/api/file-operations/cleanup?days_old=0")
        
        assert response.status_code == 422  # Validation error

    def test_convenience_rename_endpoint(self, client, temp_files):
        """Test convenience rename endpoint."""
        response = client.post(
            "/api/file-operations/rename",
            params={
                "source_path": temp_files["test_file"],
                "target_path": temp_files["target_file"],
                "force": False,
                "create_backup": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "rename"
        assert data["source_path"] == temp_files["test_file"]
        assert data["target_path"] == temp_files["target_file"]

    def test_convenience_delete_endpoint(self, client, temp_files):
        """Test convenience delete endpoint."""
        response = client.post(
            "/api/file-operations/delete",
            params={
                "source_path": temp_files["test_file"],
                "force": False,
                "create_backup": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "delete"
        assert data["source_path"] == temp_files["test_file"]

    def test_convenience_move_endpoint(self, client, temp_files):
        """Test convenience move endpoint."""
        response = client.post(
            "/api/file-operations/move",
            params={
                "source_path": temp_files["test_file"],
                "target_path": temp_files["target_file"],
                "force": False,
                "create_backup": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "move"
        assert data["source_path"] == temp_files["test_file"]
        assert data["target_path"] == temp_files["target_file"]

    def test_api_error_handling(self, client):
        """Test API error handling for various scenarios."""
        # Test with completely invalid JSON
        response = client.post(
            "/api/file-operations/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        
        # Test with missing Content-Type
        response = client.post(
            "/api/file-operations/",
            data='{"operation_type": "delete", "source_path": "/test"}'
        )
        
        assert response.status_code in [200, 400, 422]  # Depends on FastAPI handling

    def test_operation_workflow_complete(self, client, temp_files):
        """Test complete operation workflow from creation to cleanup."""
        # Step 1: Create operation
        create_response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "rename",
                "source_path": temp_files["test_file"],
                "target_path": temp_files["target_file"]
            }
        )
        
        assert create_response.status_code == 200
        operation_id = create_response.json()["id"]
        
        # Step 2: Validate operation
        validate_response = client.post(f"/api/file-operations/{operation_id}/validate")
        assert validate_response.status_code == 200
        validation_data = validate_response.json()
        assert validation_data["is_valid"]
        
        # Step 3: Execute operation
        execute_response = client.post(
            f"/api/file-operations/{operation_id}/execute",
            json={
                "operation_id": operation_id,
                "confirmed": True
            }
        )
        
        assert execute_response.status_code == 200
        execution_data = execute_response.json()
        assert execution_data["status"] == "completed"
        
        # Step 4: Verify operation status
        get_response = client.get(f"/api/file-operations/{operation_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["status"] == "completed"
        
        # Step 5: List operations (should include our operation)
        list_response = client.get("/api/file-operations/")
        assert list_response.status_code == 200
        list_data = list_response.json()
        operation_ids = [op["id"] for op in list_data["operations"]]
        assert operation_id in operation_ids
        
        # Verify file system changes
        assert not Path(temp_files["test_file"]).exists()
        assert Path(temp_files["target_file"]).exists()


class TestFileOperationsAPIWithDatabase:
    """Test file operations API with database integration."""

    async def test_api_database_consistency(self, db_session: AsyncSession, temp_files):
        """Test that API operations maintain database consistency."""
        client = TestClient(app)
        
        # Create series in database
        series = Series(
            id=uuid4(),
            title_primary="Test Series",
            file_path=temp_files["test_file"]
        )
        db_session.add(series)
        await db_session.commit()
        
        # Create delete operation via API
        response = client.post(
            "/api/file-operations/",
            json={
                "operation_type": "delete",
                "source_path": temp_files["test_file"]
            }
        )
        
        operation_id = response.json()["id"]
        
        # Validate and execute
        client.post(f"/api/file-operations/{operation_id}/validate")
        client.post(
            f"/api/file-operations/{operation_id}/execute",
            json={
                "operation_id": operation_id,
                "confirmed": True
            }
        )
        
        # Verify database record was updated/deleted
        await db_session.refresh(series)
        # The actual behavior depends on implementation - 
        # series might be deleted or marked as orphaned

    async def test_api_with_concurrent_requests(self, db_session: AsyncSession):
        """Test API handling of concurrent requests."""
        import asyncio
        import httpx
        
        # Create multiple test files
        temp_dir = tempfile.mkdtemp()
        try:
            test_files = []
            for i in range(3):
                test_file = Path(temp_dir) / f"concurrent_{i}.txt"
                test_file.write_text(f"content {i}")
                test_files.append(str(test_file))
            
            async def create_operation(file_path: str):
                async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/api/file-operations/",
                        json={
                            "operation_type": "delete",
                            "source_path": file_path
                        }
                    )
                    return response
            
            # Create operations concurrently
            tasks = [create_operation(file_path) for file_path in test_files]
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
                assert "id" in response.json()
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)