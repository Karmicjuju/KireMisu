"""Test library path API endpoints."""

import os
import tempfile
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath
from kiremisu.services.library_path import LibraryPathService


@pytest.fixture
async def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def sample_library_path(db_session: AsyncSession, temp_directory: str):
    """Create a sample library path for testing."""
    library_path = LibraryPath(
        path=temp_directory,
        enabled=True,
        scan_interval_hours=24,
    )
    db_session.add(library_path)
    await db_session.commit()
    await db_session.refresh(library_path)
    return library_path


class TestLibraryPathAPI:
    """Test library path API endpoints."""

    @pytest.mark.asyncio
    async def test_get_library_paths_empty(self, client: AsyncClient):
        """Test getting library paths when none exist."""
        response = await client.get("/api/library/paths")
        assert response.status_code == 200
        data = response.json()
        assert data["paths"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_library_paths(self, client: AsyncClient, sample_library_path: LibraryPath):
        """Test getting library paths."""
        response = await client.get("/api/library/paths")
        assert response.status_code == 200
        data = response.json()
        assert len(data["paths"]) == 1
        assert data["total"] == 1
        assert data["paths"][0]["id"] == str(sample_library_path.id)
        assert data["paths"][0]["path"] == sample_library_path.path

    @pytest.mark.asyncio
    async def test_get_library_path_by_id(
        self, client: AsyncClient, sample_library_path: LibraryPath
    ):
        """Test getting a specific library path by ID."""
        response = await client.get(f"/api/library/paths/{sample_library_path.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_library_path.id)
        assert data["path"] == sample_library_path.path
        assert data["enabled"] == sample_library_path.enabled

    @pytest.mark.asyncio
    async def test_get_library_path_not_found(self, client: AsyncClient):
        """Test getting a non-existent library path."""
        fake_id = uuid4()
        response = await client.get(f"/api/library/paths/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_library_path(self, client: AsyncClient, temp_directory: str):
        """Test creating a new library path."""
        data = {
            "path": temp_directory,
            "enabled": True,
            "scan_interval_hours": 12,
        }
        response = await client.post("/api/library/paths", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["path"] == temp_directory
        assert result["enabled"] is True
        assert result["scan_interval_hours"] == 12

    @pytest.mark.asyncio
    async def test_create_library_path_invalid_path(self, client: AsyncClient):
        """Test creating a library path with an invalid directory."""
        data = {
            "path": "/non/existent/path",
            "enabled": True,
            "scan_interval_hours": 24,
        }
        response = await client.post("/api/library/paths", json=data)
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_library_path_duplicate(
        self, client: AsyncClient, sample_library_path: LibraryPath
    ):
        """Test creating a library path with a duplicate path."""
        data = {
            "path": sample_library_path.path,
            "enabled": True,
            "scan_interval_hours": 24,
        }
        response = await client.post("/api/library/paths", json=data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_library_path(self, client: AsyncClient, sample_library_path: LibraryPath):
        """Test updating a library path."""
        data = {
            "enabled": False,
            "scan_interval_hours": 48,
        }
        response = await client.put(f"/api/library/paths/{sample_library_path.id}", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["enabled"] is False
        assert result["scan_interval_hours"] == 48
        assert result["path"] == sample_library_path.path  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_library_path_not_found(self, client: AsyncClient):
        """Test updating a non-existent library path."""
        fake_id = uuid4()
        data = {"enabled": False}
        response = await client.put(f"/api/library/paths/{fake_id}", json=data)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_library_path(self, client: AsyncClient, sample_library_path: LibraryPath):
        """Test deleting a library path."""
        response = await client.delete(f"/api/library/paths/{sample_library_path.id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(f"/api/library/paths/{sample_library_path.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_library_path_not_found(self, client: AsyncClient):
        """Test deleting a non-existent library path."""
        fake_id = uuid4()
        response = await client.delete(f"/api/library/paths/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_scan(self, client: AsyncClient, sample_library_path: LibraryPath):
        """Test triggering a library scan."""
        response = await client.post("/api/library/scan", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "message" in data
        assert "stats" in data
        assert data["stats"]["series_found"] >= 0
        assert data["stats"]["series_created"] >= 0
