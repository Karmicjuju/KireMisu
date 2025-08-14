"""Test library path service layer."""

import os
import tempfile

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath
from kiremisu.database.schemas import LibraryPathCreate, LibraryPathUpdate
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


@pytest.mark.unit
class TestLibraryPathService:
    """Test library path service functionality."""

    @pytest.mark.asyncio
    async def test_get_all_empty(self, db_session: AsyncSession):
        """Test getting all library paths when none exist."""
        paths = await LibraryPathService.get_all(db_session)
        assert paths == []

    @pytest.mark.asyncio
    async def test_get_all(self, db_session: AsyncSession, sample_library_path: LibraryPath):
        """Test getting all library paths."""
        paths = await LibraryPathService.get_all(db_session)
        assert len(paths) == 1
        assert paths[0].id == sample_library_path.id

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession, sample_library_path: LibraryPath):
        """Test getting a library path by ID."""
        path = await LibraryPathService.get_by_id(db_session, sample_library_path.id)
        assert path is not None
        assert path.id == sample_library_path.id
        assert path.path == sample_library_path.path

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent library path by ID."""
        from uuid import uuid4

        path = await LibraryPathService.get_by_id(db_session, uuid4())
        assert path is None

    @pytest.mark.asyncio
    async def test_get_by_path(self, db_session: AsyncSession, sample_library_path: LibraryPath):
        """Test getting a library path by path string."""
        path = await LibraryPathService.get_by_path(db_session, sample_library_path.path)
        assert path is not None
        assert path.id == sample_library_path.id

    @pytest.mark.asyncio
    async def test_get_by_path_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent library path by path."""
        path = await LibraryPathService.get_by_path(db_session, "/non/existent/path")
        assert path is None

    @pytest.mark.asyncio
    async def test_create_success(self, db_session: AsyncSession, temp_directory: str):
        """Test successfully creating a library path."""
        create_data = LibraryPathCreate(
            path=temp_directory,
            enabled=True,
            scan_interval_hours=12,
        )

        path = await LibraryPathService.create(db_session, create_data)
        assert path.path == temp_directory
        assert path.enabled is True
        assert path.scan_interval_hours == 12
        assert path.id is not None

    @pytest.mark.asyncio
    async def test_create_nonexistent_path(self, db_session: AsyncSession):
        """Test creating a library path with non-existent directory."""
        create_data = LibraryPathCreate(
            path="/non/existent/path",
            enabled=True,
            scan_interval_hours=24,
        )

        with pytest.raises(ValueError, match="Path does not exist"):
            await LibraryPathService.create(db_session, create_data)

    @pytest.mark.asyncio
    async def test_create_not_directory(self, db_session: AsyncSession):
        """Test creating a library path pointing to a file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            create_data = LibraryPathCreate(
                path=temp_file.name,
                enabled=True,
                scan_interval_hours=24,
            )

            with pytest.raises(ValueError, match="Path is not a directory"):
                await LibraryPathService.create(db_session, create_data)

    @pytest.mark.asyncio
    async def test_create_duplicate_path(
        self, db_session: AsyncSession, sample_library_path: LibraryPath
    ):
        """Test creating a library path with duplicate path."""
        create_data = LibraryPathCreate(
            path=sample_library_path.path,
            enabled=True,
            scan_interval_hours=24,
        )

        with pytest.raises(ValueError, match="Path already exists"):
            await LibraryPathService.create(db_session, create_data)

    @pytest.mark.asyncio
    async def test_update_success(self, db_session: AsyncSession, sample_library_path: LibraryPath):
        """Test successfully updating a library path."""
        update_data = LibraryPathUpdate(
            enabled=False,
            scan_interval_hours=48,
        )

        updated_path = await LibraryPathService.update(
            db_session, sample_library_path.id, update_data
        )
        assert updated_path is not None
        assert updated_path.enabled is False
        assert updated_path.scan_interval_hours == 48
        assert updated_path.path == sample_library_path.path  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_path(self, db_session: AsyncSession, sample_library_path: LibraryPath):
        """Test updating the path of a library path."""
        with tempfile.TemporaryDirectory() as new_temp_dir:
            update_data = LibraryPathUpdate(path=new_temp_dir)

            updated_path = await LibraryPathService.update(
                db_session, sample_library_path.id, update_data
            )
            assert updated_path is not None
            assert updated_path.path == new_temp_dir

    @pytest.mark.asyncio
    async def test_update_not_found(self, db_session: AsyncSession):
        """Test updating a non-existent library path."""
        from uuid import uuid4

        update_data = LibraryPathUpdate(enabled=False)

        result = await LibraryPathService.update(db_session, uuid4(), update_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session: AsyncSession, sample_library_path: LibraryPath):
        """Test successfully deleting a library path."""
        result = await LibraryPathService.delete(db_session, sample_library_path.id)
        assert result is True

        # Verify it's deleted
        path = await LibraryPathService.get_by_id(db_session, sample_library_path.id)
        assert path is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session: AsyncSession):
        """Test deleting a non-existent library path."""
        from uuid import uuid4

        result = await LibraryPathService.delete(db_session, uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_get_enabled_paths(self, db_session: AsyncSession, temp_directory: str):
        """Test getting only enabled library paths."""
        # Create enabled path
        enabled_path = LibraryPath(
            path=temp_directory + "/enabled",
            enabled=True,
            scan_interval_hours=24,
        )
        os.makedirs(enabled_path.path, exist_ok=True)

        # Create disabled path
        disabled_path = LibraryPath(
            path=temp_directory + "/disabled",
            enabled=False,
            scan_interval_hours=24,
        )
        os.makedirs(disabled_path.path, exist_ok=True)

        db_session.add_all([enabled_path, disabled_path])
        await db_session.commit()

        enabled_paths = await LibraryPathService.get_enabled_paths(db_session)
        assert len(enabled_paths) == 1
        assert enabled_paths[0].enabled is True

    @pytest.mark.asyncio
    async def test_update_last_scan(
        self, db_session: AsyncSession, sample_library_path: LibraryPath
    ):
        """Test updating the last scan timestamp."""
        original_last_scan = sample_library_path.last_scan

        updated_path = await LibraryPathService.update_last_scan(db_session, sample_library_path.id)
        assert updated_path is not None
        assert updated_path.last_scan is not None
        assert updated_path.last_scan != original_last_scan
