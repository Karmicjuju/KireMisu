import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.series import Series
from app.services.series import SeriesService
from app.schemas.series import SeriesCreate, SeriesUpdate


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def series_service(mock_db):
    """SeriesService instance with mocked dependencies."""
    service = SeriesService(mock_db)
    # Mock the repository and history service
    service.series_repo = AsyncMock()
    service.history_service = AsyncMock()
    return service


@pytest.fixture
def sample_series():
    """Sample series object."""
    return Series(
        id=1,
        title="Test Manga",
        description="A test manga series",
        author="Test Author",
        artist="Test Artist",
        status="ongoing",
        cover_path="covers/test-manga.jpg",
        metadata_json={"genre": "action", "tags": ["adventure"]},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def series_create_data():
    """Sample series creation data."""
    return SeriesCreate(
        title="Test Manga",
        description="A test manga series",
        author="Test Author",
        artist="Test Artist",
        status="ongoing",
        cover_path="covers/test-manga.jpg",
        metadata_json={"genre": "action", "tags": ["adventure"]},
    )


@pytest.mark.asyncio
async def test_create_series_with_history(series_service, series_create_data, sample_series):
    """Test creating series with history tracking."""
    # Mock no existing series with same title
    series_service.series_repo.is_title_taken = AsyncMock(return_value=False)
    # Mock successful creation
    series_service.series_repo.create_series = AsyncMock(return_value=sample_series)
    # Mock history recording
    series_service.history_service.record_change = AsyncMock()
    
    result = await series_service.create_series(series_create_data, user_id="user123")
    
    # Verify repository calls
    series_service.series_repo.is_title_taken.assert_called_once_with("Test Manga")
    series_service.series_repo.create_series.assert_called_once_with(series_create_data)
    
    # Verify history recording
    series_service.history_service.record_change.assert_called_once()
    history_call_args = series_service.history_service.record_change.call_args[1]
    assert history_call_args["entity_type"] == "series"
    assert history_call_args["entity_id"] == 1
    assert history_call_args["user_id"] == "user123"
    assert history_call_args["action"] == "create"
    assert "Created series 'Test Manga'" in history_call_args["description"]
    
    assert result == sample_series


@pytest.mark.asyncio
async def test_create_series_duplicate_title(series_service, series_create_data):
    """Test creating series with duplicate title fails."""
    # Mock existing series with same title
    series_service.series_repo.is_title_taken = AsyncMock(return_value=True)
    
    with pytest.raises(ValueError, match="Series with title 'Test Manga' already exists"):
        await series_service.create_series(series_create_data, user_id="user123")
    
    # Verify create was not called
    series_service.series_repo.create_series.assert_not_called()


@pytest.mark.asyncio
async def test_update_series_with_history(series_service, sample_series):
    """Test updating series with history tracking."""
    update_data = SeriesUpdate(
        title="Updated Title",
        description="Updated description"
    )
    
    # Mock existing series
    series_service.series_repo.get_series_by_id = AsyncMock(return_value=sample_series)
    # Mock no title conflict
    series_service.series_repo.is_title_taken = AsyncMock(return_value=False)
    # Mock successful update
    updated_series = Series(**sample_series.__dict__)
    updated_series.title = "Updated Title"
    updated_series.description = "Updated description"
    series_service.series_repo.update_series = AsyncMock(return_value=updated_series)
    # Mock history recording
    series_service.history_service.record_change = AsyncMock()
    
    result = await series_service.update_series(
        series_id=1,
        series_data=update_data,
        user_id="user123",
        preview_mode=False,
    )
    
    # Verify calls
    series_service.series_repo.get_series_by_id.assert_called_once_with(1)
    series_service.series_repo.update_series.assert_called_once_with(1, update_data)
    series_service.history_service.record_change.assert_called_once()
    
    # Verify history recorded the change
    history_call_args = series_service.history_service.record_change.call_args[1]
    assert history_call_args["entity_type"] == "series"
    assert history_call_args["entity_id"] == 1
    assert history_call_args["action"] == "update"
    assert history_call_args["previous_data"]["title"] == "Test Manga"
    assert history_call_args["new_data"]["title"] == "Updated Title"
    
    assert result == updated_series


@pytest.mark.asyncio
async def test_update_series_preview_mode(series_service, sample_series):
    """Test updating series in preview mode."""
    update_data = SeriesUpdate(title="Updated Title")
    
    # Mock existing series
    series_service.series_repo.get_series_by_id = AsyncMock(return_value=sample_series)
    # Mock preview generation
    mock_preview = {
        "changes": {"title": {"old": "Test Manga", "new": "Updated Title"}},
        "additions": {},
        "removals": {}
    }
    series_service.history_service.create_diff_preview = AsyncMock(return_value=mock_preview)
    
    result = await series_service.update_series(
        series_id=1,
        series_data=update_data,
        user_id="user123",
        preview_mode=True,
    )
    
    # Verify no actual update was made
    series_service.series_repo.update_series.assert_not_called()
    series_service.history_service.record_change.assert_not_called()
    
    # Verify preview was returned
    assert result["preview"] == mock_preview
    assert result["current"] == sample_series


@pytest.mark.asyncio
async def test_update_series_title_conflict(series_service, sample_series):
    """Test updating series title to existing title fails."""
    update_data = SeriesUpdate(title="Existing Title")
    
    # Mock existing series
    series_service.series_repo.get_series_by_id = AsyncMock(return_value=sample_series)
    # Mock title conflict
    series_service.series_repo.is_title_taken = AsyncMock(return_value=True)
    
    with pytest.raises(ValueError, match="Series with title 'Existing Title' already exists"):
        await series_service.update_series(
            series_id=1,
            series_data=update_data,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_update_series_not_found(series_service):
    """Test updating non-existent series."""
    update_data = SeriesUpdate(title="Updated Title")
    
    # Mock series not found
    series_service.series_repo.get_series_by_id = AsyncMock(return_value=None)
    
    result = await series_service.update_series(
        series_id=999,
        series_data=update_data,
        user_id="user123",
    )
    
    assert result is None
    series_service.series_repo.update_series.assert_not_called()


@pytest.mark.asyncio
async def test_update_series_empty_data(series_service, sample_series):
    """Test updating series with empty data returns existing series."""
    update_data = SeriesUpdate()  # No fields set
    
    # Mock existing series
    series_service.series_repo.get_series_by_id = AsyncMock(return_value=sample_series)
    
    result = await series_service.update_series(
        series_id=1,
        series_data=update_data,
        user_id="user123",
    )
    
    # Verify no update or history recording was made
    series_service.series_repo.update_series.assert_not_called()
    series_service.history_service.record_change.assert_not_called()
    
    assert result == sample_series


@pytest.mark.asyncio
async def test_get_series_history(series_service):
    """Test getting series change history."""
    mock_history = [MagicMock(), MagicMock()]
    series_service.history_service.get_entity_history = AsyncMock(return_value=mock_history)
    
    result = await series_service.get_series_history(series_id=1, limit=10, offset=0)
    
    series_service.history_service.get_entity_history.assert_called_once_with(
        entity_type="series",
        entity_id=1,
        limit=10,
        offset=0,
    )
    assert result == mock_history


@pytest.mark.asyncio
async def test_restore_series_from_history(series_service):
    """Test restoring series from history."""
    restore_data = {
        "title": "Original Title",
        "description": "Original Description",
        "author": "Original Author",
    }
    
    # Mock history service
    series_service.history_service.get_restore_data = AsyncMock(return_value=restore_data)
    
    # Mock update_series method
    restored_series = MagicMock()
    with patch.object(series_service, 'update_series', return_value=restored_series) as mock_update:
        result = await series_service.restore_series_from_history(
            series_id=1,
            history_id=10,
            user_id="user123",
        )
    
    # Verify restore data was retrieved
    series_service.history_service.get_restore_data.assert_called_once_with(10)
    
    # Verify update was called with restore data
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[1]["series_id"] == 1
    assert call_args[1]["user_id"] == "user123"
    assert call_args[1]["preview_mode"] is False
    
    assert result == restored_series


@pytest.mark.asyncio
async def test_restore_series_history_not_found(series_service):
    """Test restoring from non-existent history."""
    series_service.history_service.get_restore_data = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="History entry 999 not found"):
        await series_service.restore_series_from_history(
            series_id=1,
            history_id=999,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_bulk_update_series_success(series_service):
    """Test successful bulk update of series."""
    series_ids = [1, 2, 3]
    update_data = SeriesUpdate(status="completed")
    
    # Mock existing series
    series_list = [
        Series(id=1, title="Series 1", status="ongoing"),
        Series(id=2, title="Series 2", status="ongoing"),
        Series(id=3, title="Series 3", status="ongoing"),
    ]
    
    # Mock repository calls for individual updates
    series_service.series_repo.get_series_by_id = AsyncMock(side_effect=series_list)
    series_service.series_repo.get_series_by_title = AsyncMock(return_value=None)  # No conflicts
    
    # Mock successful updates
    updated_series = []
    for i, series in enumerate(series_list):
        updated = Series(**series.__dict__)
        updated.status = "completed"
        updated_series.append(updated)
    
    with patch.object(series_service, 'update_series', side_effect=updated_series) as mock_update:
        result = await series_service.bulk_update_series(
            series_ids=series_ids,
            update_data=update_data,
            user_id="user123",
        )
    
    # Verify all series were updated individually
    assert mock_update.call_count == 3
    
    assert result == updated_series


@pytest.mark.asyncio
async def test_bulk_update_series_too_many(series_service):
    """Test bulk update fails with too many series."""
    series_ids = list(range(1, 102))  # 101 series
    update_data = SeriesUpdate(status="completed")
    
    with pytest.raises(ValueError, match="Cannot update more than 100 series at once"):
        await series_service.bulk_update_series(
            series_ids=series_ids,
            update_data=update_data,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_bulk_update_series_duplicate_ids(series_service):
    """Test bulk update fails with duplicate IDs."""
    series_ids = [1, 2, 1]  # Duplicate ID
    update_data = SeriesUpdate(status="completed")
    
    with pytest.raises(ValueError, match="Series IDs must be unique"):
        await series_service.bulk_update_series(
            series_ids=series_ids,
            update_data=update_data,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_bulk_update_series_title_conflict(series_service):
    """Test bulk update fails with title conflict."""
    series_ids = [1, 2]
    update_data = SeriesUpdate(title="Existing Title")
    
    # Mock existing series with conflicting title
    conflicting_series = Series(id=999, title="Existing Title")
    series_service.series_repo.get_series_by_title = AsyncMock(return_value=conflicting_series)
    
    with pytest.raises(ValueError, match="Series with title 'Existing Title' already exists"):
        await series_service.bulk_update_series(
            series_ids=series_ids,
            update_data=update_data,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_bulk_update_series_empty_data(series_service):
    """Test bulk update with empty data returns existing series."""
    series_ids = [1, 2]
    update_data = SeriesUpdate()  # No fields set
    
    # Mock existing series
    series_list = [
        Series(id=1, title="Series 1"),
        Series(id=2, title="Series 2"),
    ]
    series_service.series_repo.get_series_by_id = AsyncMock(side_effect=series_list)
    
    result = await series_service.bulk_update_series(
        series_ids=series_ids,
        update_data=update_data,
        user_id="user123",
    )
    
    # Verify existing series were returned without changes
    assert result == series_list
    # Verify no individual updates were called
    with patch.object(series_service, 'update_series') as mock_update:
        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_update_series_partial_failure(series_service):
    """Test bulk update with some failures continues processing."""
    series_ids = [1, 2, 3]
    update_data = SeriesUpdate(status="completed")
    
    # Mock existing series
    series_list = [
        Series(id=1, title="Series 1"),
        Series(id=2, title="Series 2"),
        Series(id=3, title="Series 3"),
    ]
    
    # Mock successful updates for 1st and 3rd, failure for 2nd
    successful_updates = [series_list[0], None, series_list[2]]
    
    with patch.object(series_service, 'update_series', side_effect=successful_updates) as mock_update:
        result = await series_service.bulk_update_series(
            series_ids=series_ids,
            update_data=update_data,
            user_id="user123",
        )
    
    # Verify all updates were attempted
    assert mock_update.call_count == 3
    
    # Verify only successful updates were returned
    assert len(result) == 2
    assert result[0] == series_list[0]
    assert result[1] == series_list[2]