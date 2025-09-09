import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.services.chapter import ChapterService
from app.schemas.chapter import ChapterCreate, ChapterUpdate, BulkChapterUpdate


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def chapter_service(mock_db):
    """ChapterService instance with mocked dependencies."""
    service = ChapterService(mock_db)
    # Mock the repository and history service
    service.repository = AsyncMock()
    service.history_service = AsyncMock()
    return service


@pytest.fixture
def sample_chapter():
    """Sample chapter object."""
    return Chapter(
        id=1,
        series_id=1,
        number=Decimal("1.0"),
        title="Chapter 1: The Beginning",
        file_path="series1/chapter1.zip",
        volume=Decimal("1.0"),
        description="The first chapter",
        page_count=20,
        file_size=1024000,
        read_status=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def chapter_create_data():
    """Sample chapter creation data."""
    return ChapterCreate(
        series_id=1,
        number=Decimal("1.0"),
        title="Chapter 1: The Beginning",
        file_path="series1/chapter1.zip",
        volume=Decimal("1.0"),
        description="The first chapter",
        page_count=20,
        file_size=1024000,
    )


@pytest.mark.asyncio
async def test_create_chapter_success(chapter_service, chapter_create_data, sample_chapter):
    """Test successful chapter creation."""
    # Mock no existing chapter
    chapter_service.repository.get_by_series_and_number = AsyncMock(return_value=None)
    # Mock successful creation
    chapter_service.repository.create = AsyncMock(return_value=sample_chapter)
    # Mock history recording
    chapter_service.history_service.record_change = AsyncMock()
    
    result = await chapter_service.create_chapter(chapter_create_data, user_id="user123")
    
    # Verify repository calls
    chapter_service.repository.get_by_series_and_number.assert_called_once_with(
        1, Decimal("1.0")
    )
    chapter_service.repository.create.assert_called_once()
    
    # Verify history recording
    chapter_service.history_service.record_change.assert_called_once()
    history_call_args = chapter_service.history_service.record_change.call_args[1]
    assert history_call_args["entity_type"] == "chapter"
    assert history_call_args["entity_id"] == 1
    assert history_call_args["user_id"] == "user123"
    assert history_call_args["action"] == "create"
    
    assert result == sample_chapter


@pytest.mark.asyncio
async def test_create_chapter_duplicate_number(chapter_service, chapter_create_data, sample_chapter):
    """Test chapter creation with duplicate number fails."""
    # Mock existing chapter with same number
    chapter_service.repository.get_by_series_and_number = AsyncMock(
        return_value=sample_chapter
    )
    
    with pytest.raises(ValueError, match="Chapter 1.0 already exists for series 1"):
        await chapter_service.create_chapter(chapter_create_data, user_id="user123")
    
    # Verify create was not called
    chapter_service.repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_chapter_by_id(chapter_service, sample_chapter):
    """Test getting chapter by ID."""
    chapter_service.repository.get_by_id = AsyncMock(return_value=sample_chapter)
    
    result = await chapter_service.get_chapter_by_id(1)
    
    chapter_service.repository.get_by_id.assert_called_once_with(1)
    assert result == sample_chapter


@pytest.mark.asyncio
async def test_get_chapter_by_id_with_series(chapter_service, sample_chapter):
    """Test getting chapter by ID with series information."""
    chapter_service.repository.get_by_id_with_series = AsyncMock(return_value=sample_chapter)
    
    result = await chapter_service.get_chapter_by_id(1, include_series=True)
    
    chapter_service.repository.get_by_id_with_series.assert_called_once_with(1)
    assert result == sample_chapter


@pytest.mark.asyncio
async def test_update_chapter_success(chapter_service, sample_chapter):
    """Test successful chapter update."""
    update_data = ChapterUpdate(title="Updated Title", description="Updated description")
    
    # Mock existing chapter
    chapter_service.repository.get_by_id = AsyncMock(return_value=sample_chapter)
    # Mock successful update
    updated_chapter = Chapter(
        id=sample_chapter.id,
        series_id=sample_chapter.series_id,
        number=sample_chapter.number,
        title="Updated Title",
        file_path=sample_chapter.file_path,
        volume=sample_chapter.volume,
        description="Updated description",
        page_count=sample_chapter.page_count,
        file_size=sample_chapter.file_size,
        read_status=sample_chapter.read_status,
        created_at=sample_chapter.created_at,
        updated_at=sample_chapter.updated_at,
    )
    chapter_service.repository.update = AsyncMock(return_value=updated_chapter)
    # Mock history service
    chapter_service.history_service.record_change = AsyncMock()
    
    result = await chapter_service.update_chapter(
        chapter_id=1,
        update_data=update_data,
        user_id="user123",
        preview_mode=False,
    )
    
    # Verify calls
    chapter_service.repository.get_by_id.assert_called_once_with(1)
    chapter_service.repository.update.assert_called_once()
    chapter_service.history_service.record_change.assert_called_once()
    
    assert result == updated_chapter


@pytest.mark.asyncio
async def test_update_chapter_preview_mode(chapter_service, sample_chapter):
    """Test chapter update in preview mode."""
    update_data = ChapterUpdate(title="Updated Title")
    
    # Mock existing chapter
    chapter_service.repository.get_by_id = AsyncMock(return_value=sample_chapter)
    # Mock preview generation
    mock_preview = {"changes": {"title": {"old": "Chapter 1: The Beginning", "new": "Updated Title"}}}
    chapter_service.history_service.create_diff_preview = AsyncMock(return_value=mock_preview)
    
    result = await chapter_service.update_chapter(
        chapter_id=1,
        update_data=update_data,
        user_id="user123",
        preview_mode=True,
    )
    
    # Verify no update was made
    chapter_service.repository.update.assert_not_called()
    chapter_service.history_service.record_change.assert_not_called()
    
    # Verify preview was returned
    assert result["preview"] == mock_preview
    assert result["current"] == sample_chapter


@pytest.mark.asyncio
async def test_update_chapter_not_found(chapter_service):
    """Test updating non-existent chapter."""
    update_data = ChapterUpdate(title="Updated Title")
    
    # Mock chapter not found
    chapter_service.repository.get_by_id = AsyncMock(return_value=None)
    
    result = await chapter_service.update_chapter(
        chapter_id=999,
        update_data=update_data,
        user_id="user123",
    )
    
    assert result is None
    chapter_service.repository.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_chapter_number_conflict(chapter_service, sample_chapter):
    """Test updating chapter number to existing number fails."""
    update_data = ChapterUpdate(number=Decimal("2.0"))
    
    # Mock existing chapter
    chapter_service.repository.get_by_id = AsyncMock(return_value=sample_chapter)
    # Mock conflicting chapter exists
    conflicting_chapter = Chapter(
        id=2,
        series_id=sample_chapter.series_id,
        number=Decimal("2.0"),
        title=sample_chapter.title,
        file_path=sample_chapter.file_path,
        volume=sample_chapter.volume,
        description=sample_chapter.description,
        page_count=sample_chapter.page_count,
        file_size=sample_chapter.file_size,
        read_status=sample_chapter.read_status,
        created_at=sample_chapter.created_at,
        updated_at=sample_chapter.updated_at,
    )
    chapter_service.repository.get_by_series_and_number = AsyncMock(
        return_value=conflicting_chapter
    )
    
    with pytest.raises(ValueError, match="Chapter 2.0 already exists for this series"):
        await chapter_service.update_chapter(
            chapter_id=1,
            update_data=update_data,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_bulk_update_chapters_success(chapter_service):
    """Test successful bulk update of chapters."""
    chapter_ids = [1, 2, 3]
    update_data = ChapterUpdate(read_status=True)
    bulk_data = BulkChapterUpdate(chapter_ids=chapter_ids, updates=update_data)
    
    # Mock existing chapters
    chapters = [
        Chapter(id=1, series_id=1, number=Decimal("1"), title="Ch1", file_path="ch1.zip"),
        Chapter(id=2, series_id=1, number=Decimal("2"), title="Ch2", file_path="ch2.zip"),
        Chapter(id=3, series_id=1, number=Decimal("3"), title="Ch3", file_path="ch3.zip"),
    ]
    
    chapter_service.repository.get_by_id = AsyncMock(side_effect=chapters)
    chapter_service.repository.bulk_update = AsyncMock(return_value=chapters)
    chapter_service.history_service.record_change = AsyncMock()
    
    result = await chapter_service.bulk_update_chapters(bulk_data, user_id="user123")
    
    # Verify all chapters were checked to exist
    assert chapter_service.repository.get_by_id.call_count == 3
    
    # Verify bulk update was called
    chapter_service.repository.bulk_update.assert_called_once_with(
        chapter_ids, {"read_status": True}
    )
    
    # Verify history was recorded for each chapter
    assert chapter_service.history_service.record_change.call_count == 3
    
    assert result == chapters


@pytest.mark.asyncio
async def test_bulk_update_chapters_not_found(chapter_service):
    """Test bulk update fails when chapter not found."""
    chapter_ids = [1, 999]
    update_data = ChapterUpdate(read_status=True)
    bulk_data = BulkChapterUpdate(chapter_ids=chapter_ids, updates=update_data)
    
    # Mock first chapter exists, second doesn't
    chapter_service.repository.get_by_id = AsyncMock(side_effect=[
        Chapter(id=1, series_id=1, number=Decimal("1"), title="Ch1", file_path="ch1.zip"),
        None
    ])
    
    with pytest.raises(ValueError, match="Chapter with ID 999 not found"):
        await chapter_service.bulk_update_chapters(bulk_data, user_id="user123")


@pytest.mark.asyncio
async def test_delete_chapter_success(chapter_service, sample_chapter):
    """Test successful chapter deletion."""
    # Mock existing chapter
    chapter_service.repository.get_by_id = AsyncMock(return_value=sample_chapter)
    # Mock successful deletion
    chapter_service.repository.delete = AsyncMock(return_value=True)
    # Mock history recording
    chapter_service.history_service.record_change = AsyncMock()
    
    result = await chapter_service.delete_chapter(1, user_id="user123")
    
    # Verify calls
    chapter_service.repository.get_by_id.assert_called_once_with(1)
    chapter_service.repository.delete.assert_called_once_with(1)
    chapter_service.history_service.record_change.assert_called_once()
    
    # Verify history recorded deletion
    history_call_args = chapter_service.history_service.record_change.call_args[1]
    assert history_call_args["action"] == "delete"
    
    assert result is True


@pytest.mark.asyncio
async def test_delete_chapter_not_found(chapter_service):
    """Test deleting non-existent chapter."""
    chapter_service.repository.get_by_id = AsyncMock(return_value=None)
    
    result = await chapter_service.delete_chapter(999, user_id="user123")
    
    # Verify delete was not called
    chapter_service.repository.delete.assert_not_called()
    chapter_service.history_service.record_change.assert_not_called()
    
    assert result is False


@pytest.mark.asyncio
async def test_restore_chapter_from_history(chapter_service):
    """Test restoring chapter from history."""
    restore_data = {
        "title": "Original Title",
        "description": "Original Description",
        "read_status": False,
    }
    
    # Mock history service
    chapter_service.history_service.get_restore_data = AsyncMock(return_value=restore_data)
    
    # Mock update_chapter method
    restored_chapter = MagicMock()
    with patch.object(chapter_service, 'update_chapter', return_value=restored_chapter) as mock_update:
        result = await chapter_service.restore_chapter_from_history(
            chapter_id=1,
            history_id=10,
            user_id="user123",
        )
    
    # Verify restore data was retrieved
    chapter_service.history_service.get_restore_data.assert_called_once_with(10)
    
    # Verify update was called with restore data
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[1]["chapter_id"] == 1
    assert call_args[1]["user_id"] == "user123"
    assert call_args[1]["preview_mode"] is False
    
    assert result == restored_chapter


@pytest.mark.asyncio
async def test_restore_chapter_history_not_found(chapter_service):
    """Test restoring from non-existent history."""
    chapter_service.history_service.get_restore_data = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="History entry 999 not found"):
        await chapter_service.restore_chapter_from_history(
            chapter_id=1,
            history_id=999,
            user_id="user123",
        )


@pytest.mark.asyncio
async def test_get_series_statistics(chapter_service):
    """Test getting series statistics."""
    # Mock repository calls
    chapter_service.repository.count_by_series = AsyncMock(return_value=10)
    chapter_service.repository.get_unread_count = AsyncMock(return_value=3)
    
    latest_chapters = [
        MagicMock(id=1, number=Decimal("10"), title="Chapter 10", created_at=datetime.now()),
        MagicMock(id=2, number=Decimal("9"), title="Chapter 9", created_at=datetime.now()),
    ]
    chapter_service.repository.get_latest_by_series = AsyncMock(return_value=latest_chapters)
    
    result = await chapter_service.get_series_statistics(1)
    
    expected_stats = {
        "total_chapters": 10,
        "read_count": 7,  # 10 - 3
        "unread_count": 3,
        "latest_chapters": [
            {
                "id": 1,
                "number": 10.0,
                "title": "Chapter 10",
                "created_at": latest_chapters[0].created_at,
            },
            {
                "id": 2,
                "number": 9.0,
                "title": "Chapter 9",
                "created_at": latest_chapters[1].created_at,
            },
        ],
    }
    
    assert result == expected_stats


@pytest.mark.asyncio
async def test_get_chapters_paginated_validation(chapter_service):
    """Test pagination validation."""
    # Test invalid page
    with pytest.raises(ValueError, match="Page must be >= 1"):
        await chapter_service.get_chapters_paginated(page=0)
    
    # Test invalid size
    with pytest.raises(ValueError, match="Size must be between 1 and 100"):
        await chapter_service.get_chapters_paginated(size=0)
    
    with pytest.raises(ValueError, match="Size must be between 1 and 100"):
        await chapter_service.get_chapters_paginated(size=101)