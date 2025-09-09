import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metadata_history import MetadataHistory
from app.services.metadata_history import MetadataHistoryService
from app.repositories.metadata_history import MetadataHistoryRepository


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def metadata_history_service(mock_db):
    """MetadataHistoryService instance with mocked dependencies."""
    return MetadataHistoryService(mock_db)


@pytest.fixture
def sample_metadata_history():
    """Sample metadata history entry."""
    return MetadataHistory(
        id=1,
        entity_type="series",
        entity_id=1,
        user_id=str(uuid.uuid4()),
        action="update",
        previous_data={"title": "Old Title", "author": "Old Author"},
        new_data={"title": "New Title", "author": "Old Author"},
        changed_fields=["title"],
        description="Updated series title",
        created_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_record_change_with_diff(metadata_history_service, mock_db):
    """Test recording a change with automatic diff calculation."""
    # Mock the repository create method
    mock_entry = MagicMock()
    mock_entry.id = 1
    mock_entry.entity_type = "series"
    mock_entry.changed_fields = ["title"]
    
    metadata_history_service.repository.create_history_entry = AsyncMock(return_value=mock_entry)
    
    # Test recording change
    previous_data = {"title": "Old Title", "author": "Author Name"}
    new_data = {"title": "New Title", "author": "Author Name"}
    test_user_id = str(uuid.uuid4())
    
    result = await metadata_history_service.record_change(
        entity_type="series",
        entity_id=1,
        user_id=test_user_id,
        action="update",
        previous_data=previous_data,
        new_data=new_data,
        description="Updated title",
    )
    
    # Verify the repository was called with calculated changed fields
    metadata_history_service.repository.create_history_entry.assert_called_once()
    call_args = metadata_history_service.repository.create_history_entry.call_args[1]
    
    assert call_args["entity_type"] == "series"
    assert call_args["entity_id"] == 1
    assert call_args["user_id"] == uuid.UUID(test_user_id)
    assert call_args["action"] == "update"
    assert call_args["previous_data"] == previous_data
    assert call_args["new_data"] == new_data
    assert call_args["changed_fields"] == ["title"]
    assert call_args["description"] == "Updated title"
    
    assert result == mock_entry


@pytest.mark.asyncio
async def test_get_entity_history(metadata_history_service):
    """Test retrieving entity history."""
    # Mock repository response
    mock_history = [MagicMock(), MagicMock()]
    metadata_history_service.repository.get_entity_history = AsyncMock(return_value=mock_history)
    
    result = await metadata_history_service.get_entity_history(
        entity_type="series",
        entity_id=1,
        limit=10,
        offset=0,
    )
    
    metadata_history_service.repository.get_entity_history.assert_called_once_with(
        entity_type="series",
        entity_id=1,
        limit=10,
        offset=0,
    )
    assert result == mock_history


@pytest.mark.asyncio
async def test_get_restore_data(metadata_history_service, sample_metadata_history):
    """Test getting restore data from history."""
    metadata_history_service.repository.get_history_by_id = AsyncMock(
        return_value=sample_metadata_history
    )
    
    result = await metadata_history_service.get_restore_data(1)
    
    metadata_history_service.repository.get_history_by_id.assert_called_once_with(1)
    assert result == sample_metadata_history.previous_data


@pytest.mark.asyncio
async def test_get_restore_data_not_found(metadata_history_service):
    """Test getting restore data when history entry not found."""
    metadata_history_service.repository.get_history_by_id = AsyncMock(return_value=None)
    
    result = await metadata_history_service.get_restore_data(999)
    
    assert result is None


@pytest.mark.asyncio
async def test_create_diff_preview(metadata_history_service):
    """Test creating a diff preview."""
    current_data = {
        "title": "Original Title",
        "author": "Original Author",
        "status": "ongoing",
    }
    
    new_data = {
        "title": "Updated Title",
        "artist": "New Artist",
        "status": "ongoing",
    }
    
    result = await metadata_history_service.create_diff_preview(current_data, new_data)
    
    expected_diff = {
        "changes": {
            "title": {
                "old": "Original Title",
                "new": "Updated Title",
            }
        },
        "additions": {
            "artist": "New Artist",
        },
        "removals": {
            "author": "Original Author",
        },
    }
    
    assert result == expected_diff


@pytest.mark.asyncio
async def test_cleanup_old_history(metadata_history_service):
    """Test cleaning up old history entries."""
    metadata_history_service.repository.delete_old_history = AsyncMock(return_value=5)
    
    result = await metadata_history_service.cleanup_old_history(
        entity_type="series",
        entity_id=1,
        keep_count=10,
    )
    
    metadata_history_service.repository.delete_old_history.assert_called_once_with(
        entity_type="series",
        entity_id=1,
        keep_count=10,
    )
    assert result == 5


@pytest.mark.asyncio
async def test_get_entity_statistics(metadata_history_service):
    """Test getting entity statistics."""
    # Mock history entries
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    mock_entries = [
        MagicMock(action="create", user_id=user1_id, changed_fields=["title"]),
        MagicMock(action="update", user_id=user1_id, changed_fields=["author", "status"]),
        MagicMock(action="update", user_id=user2_id, changed_fields=["title"]),
    ]
    
    metadata_history_service.repository.get_entity_history = AsyncMock(
        return_value=mock_entries
    )
    
    result = await metadata_history_service.get_entity_statistics("series", 1)
    
    expected_stats = {
        "total_changes": 3,
        "change_types": {"create": 1, "update": 2},
        "most_active_users": [(user1_id, 2), (user2_id, 1)],
        "most_changed_fields": [("title", 2), ("author", 1), ("status", 1)],
    }
    
    assert result == expected_stats


@pytest.mark.asyncio
async def test_get_entity_statistics_empty(metadata_history_service):
    """Test getting entity statistics when no history exists."""
    metadata_history_service.repository.get_entity_history = AsyncMock(return_value=[])
    
    result = await metadata_history_service.get_entity_statistics("series", 1)
    
    expected_stats = {
        "total_changes": 0,
        "change_types": {},
        "most_active_users": [],
        "most_changed_fields": [],
    }
    
    assert result == expected_stats


class TestMetadataHistoryRepository:
    """Test MetadataHistoryRepository methods."""

    @pytest.fixture
    def repository(self, mock_db):
        return MetadataHistoryRepository(mock_db)

    @pytest.mark.asyncio
    async def test_create_history_entry(self, repository, mock_db):
        """Test creating a history entry."""
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        test_user_uuid = uuid.uuid4()
        result = await repository.create_history_entry(
            entity_type="series",
            entity_id=1,
            user_id=test_user_uuid,
            action="create",
            new_data={"title": "Test Series"},
            description="Created series",
        )
        
        # Verify database operations were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the created object has correct attributes
        assert result.entity_type == "series"
        assert result.entity_id == 1
        assert result.user_id == test_user_uuid
        assert result.action == "create"
        assert result.new_data == {"title": "Test Series"}
        assert result.description == "Created series"

    @pytest.mark.asyncio
    async def test_count_entity_history(self, repository, mock_db):
        """Test counting entity history entries."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.count_entity_history("series", 1)
        
        assert result == 15
        mock_db.execute.assert_called_once()