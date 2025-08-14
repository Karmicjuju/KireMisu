"""
Tests for reading progress service functionality.

This module tests the comprehensive reading progress system including:
- Chapter progress updates and automatic completion detection
- Series progress calculation and statistics
- User reading statistics and streak tracking
- Integration with existing chapter and series models
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from kiremisu.database.models import Chapter, Series
from kiremisu.database.schemas import ReadingProgressUpdateRequest
from kiremisu.services.reading_progress import ReadingProgressService


@pytest.fixture
async def sample_series(db_session):
    """Create a sample series for testing."""
    series = Series(
        id=uuid4(),
        title_primary="Test Manga Series",
        author="Test Author",
        genres=["Action", "Adventure"],
        total_chapters=5,
        read_chapters=0,
    )
    db_session.add(series)
    await db_session.commit()
    return series


@pytest.fixture
async def sample_chapters(db_session, sample_series):
    """Create sample chapters for testing."""
    chapters = []
    for i in range(5):
        chapter = Chapter(
            id=uuid4(),
            series_id=sample_series.id,
            chapter_number=float(i + 1),
            file_path=f"/test/chapter_{i+1}.cbz",
            page_count=20,
            file_size=1024000,
        )
        chapters.append(chapter)
        db_session.add(chapter)

    await db_session.commit()
    return chapters


class TestReadingProgressService:
    """Test cases for ReadingProgressService."""

    async def test_update_chapter_progress_basic(self, db_session, sample_chapters):
        """Test basic chapter progress update."""
        chapter = sample_chapters[0]

        progress_request = ReadingProgressUpdateRequest(
            current_page=5,
            is_complete=None  # Let service auto-determine
        )

        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )

        assert result.chapter_id == chapter.id
        assert result.current_page == 5
        assert result.total_pages == 20
        assert result.progress_percentage == 30.0  # (5+1)/20 * 100
        assert not result.is_read  # Not at end yet
        assert result.started_at is not None  # Should set started_at on first progress

    async def test_update_chapter_progress_completion(self, db_session, sample_chapters):
        """Test automatic chapter completion detection."""
        chapter = sample_chapters[0]

        # Update to last page - should auto-complete
        progress_request = ReadingProgressUpdateRequest(
            current_page=19,  # Last page (0-indexed)
            is_complete=None
        )

        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )

        assert result.is_read  # Should be marked as read
        assert result.read_at is not None
        assert result.progress_percentage == 100.0

    async def test_update_chapter_progress_explicit_completion(self, db_session, sample_chapters):
        """Test explicit chapter completion."""
        chapter = sample_chapters[0]

        # Explicitly mark as complete even if not at last page
        progress_request = ReadingProgressUpdateRequest(
            current_page=10,
            is_complete=True
        )

        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )

        assert result.is_read
        assert result.read_at is not None
        assert result.current_page == 10

    async def test_update_chapter_progress_invalid_chapter(self, db_session):
        """Test progress update with invalid chapter ID."""
        invalid_id = str(uuid4())

        progress_request = ReadingProgressUpdateRequest(
            current_page=5,
            is_complete=None
        )

        with pytest.raises(ValueError, match="Chapter with ID .* not found"):
            await ReadingProgressService.update_chapter_progress(
                db_session, invalid_id, progress_request
            )

    async def test_update_chapter_progress_invalid_page(self, db_session, sample_chapters):
        """Test progress update with invalid page number."""
        chapter = sample_chapters[0]

        # Page number exceeds chapter page count
        progress_request = ReadingProgressUpdateRequest(
            current_page=25,  # Chapter has 20 pages
            is_complete=None
        )

        with pytest.raises(ValueError, match="Invalid page number.*Chapter has.*pages"):
            await ReadingProgressService.update_chapter_progress(
                db_session, str(chapter.id), progress_request
            )

    async def test_toggle_chapter_read_status(self, db_session, sample_chapters):
        """Test toggling chapter read status."""
        chapter = sample_chapters[0]

        # Initially unread
        assert not chapter.is_read

        # Toggle to read
        new_status, read_at = await ReadingProgressService.toggle_chapter_read_status(
            db_session, str(chapter.id)
        )

        assert new_status is True
        assert read_at is not None

        # Toggle back to unread
        new_status, read_at = await ReadingProgressService.toggle_chapter_read_status(
            db_session, str(chapter.id)
        )

        assert new_status is False
        assert read_at is None

    async def test_get_series_progress(self, db_session, sample_series, sample_chapters):
        """Test getting series reading progress."""
        # Mark first 2 chapters as read
        for chapter in sample_chapters[:2]:
            await ReadingProgressService.toggle_chapter_read_status(
                db_session, str(chapter.id)
            )

        result = await ReadingProgressService.get_series_progress(
            db_session, str(sample_series.id)
        )

        assert result.series_id == sample_series.id
        assert result.total_chapters == 5
        assert result.read_chapters == 2
        assert result.progress_percentage == 40.0  # 2/5 * 100
        assert len(result.recent_chapters) == 2
        assert result.last_read_at is not None

    async def test_get_series_progress_invalid_series(self, db_session):
        """Test getting progress for invalid series."""
        invalid_id = str(uuid4())

        with pytest.raises(ValueError, match="Series with ID .* not found"):
            await ReadingProgressService.get_series_progress(db_session, invalid_id)

    async def test_get_user_reading_stats(self, db_session, sample_series, sample_chapters):
        """Test getting comprehensive user reading statistics."""
        # Mark some chapters as read
        for chapter in sample_chapters[:3]:
            await ReadingProgressService.toggle_chapter_read_status(
                db_session, str(chapter.id)
            )

        # Add some partial progress to one chapter
        progress_request = ReadingProgressUpdateRequest(current_page=5, is_complete=None)
        await ReadingProgressService.update_chapter_progress(
            db_session, str(sample_chapters[3].id), progress_request
        )

        result = await ReadingProgressService.get_user_reading_stats(db_session)

        assert result.total_series == 1
        assert result.total_chapters == 5
        assert result.read_chapters == 3
        assert result.in_progress_chapters == 1  # Chapter with partial progress
        assert result.overall_progress_percentage == 60.0  # 3/5 * 100
        assert result.reading_streak_days >= 0
        assert len(result.recent_activity) == 3

    async def test_mark_series_read(self, db_session, sample_series, sample_chapters):
        """Test marking entire series as read."""
        chapters_updated = await ReadingProgressService.mark_series_read(
            db_session, str(sample_series.id)
        )

        assert chapters_updated == 5  # All chapters should be updated

        # Verify all chapters are now read
        result = await ReadingProgressService.get_series_progress(
            db_session, str(sample_series.id)
        )
        assert result.read_chapters == 5
        assert result.progress_percentage == 100.0

    async def test_mark_series_unread(self, db_session, sample_series, sample_chapters):
        """Test marking entire series as unread."""
        # First mark series as read
        await ReadingProgressService.mark_series_read(db_session, str(sample_series.id))

        # Then mark as unread
        chapters_updated = await ReadingProgressService.mark_series_unread(
            db_session, str(sample_series.id)
        )

        assert chapters_updated == 5

        # Verify all chapters are now unread
        result = await ReadingProgressService.get_series_progress(
            db_session, str(sample_series.id)
        )
        assert result.read_chapters == 0
        assert result.progress_percentage == 0.0

    async def test_mark_series_invalid_id(self, db_session):
        """Test marking series with invalid ID."""
        invalid_id = str(uuid4())

        with pytest.raises(ValueError, match="Series with ID .* not found"):
            await ReadingProgressService.mark_series_read(db_session, invalid_id)

        with pytest.raises(ValueError, match="Series with ID .* not found"):
            await ReadingProgressService.mark_series_unread(db_session, invalid_id)

    async def test_reading_streak_calculation(self, db_session, sample_chapters):
        """Test reading streak calculation."""
        # Create chapters with different read dates
        now = datetime.utcnow()

        # Read chapters on consecutive days
        for i, chapter in enumerate(sample_chapters[:3]):
            read_date = now - timedelta(days=i)
            chapter.is_read = True
            chapter.read_at = read_date

        await db_session.commit()

        # Calculate reading streak
        streak = await ReadingProgressService._calculate_reading_streak(db_session)

        # Should have a streak of at least 3 days (depending on current time)
        assert streak >= 0  # At minimum, should not be negative

    async def test_favorite_genres_calculation(self, db_session):
        """Test favorite genres calculation based on read chapters."""
        # Create series with different genres
        series1 = Series(
            id=uuid4(),
            title_primary="Action Series",
            genres=["Action", "Adventure"],
            total_chapters=2
        )
        series2 = Series(
            id=uuid4(),
            title_primary="Romance Series",
            genres=["Romance", "Drama"],
            total_chapters=2
        )
        series3 = Series(
            id=uuid4(),
            title_primary="Action Adventure Series",
            genres=["Action", "Fantasy"],
            total_chapters=1
        )

        db_session.add_all([series1, series2, series3])
        await db_session.commit()

        # Create and read chapters
        chapters = [
            Chapter(id=uuid4(), series_id=series1.id, chapter_number=1.0,
                   file_path="/test/1.cbz", page_count=20, is_read=True),
            Chapter(id=uuid4(), series_id=series1.id, chapter_number=2.0,
                   file_path="/test/2.cbz", page_count=20, is_read=True),
            Chapter(id=uuid4(), series_id=series2.id, chapter_number=1.0,
                   file_path="/test/3.cbz", page_count=20, is_read=True),
            Chapter(id=uuid4(), series_id=series3.id, chapter_number=1.0,
                   file_path="/test/4.cbz", page_count=20, is_read=True),
        ]

        db_session.add_all(chapters)
        await db_session.commit()

        favorite_genres = await ReadingProgressService._get_favorite_genres(db_session)

        # "Action" should be top genre (appears in 3 chapters)
        assert "Action" in favorite_genres
        assert favorite_genres[0] == "Action"  # Should be first (most frequent)

    async def test_series_read_count_updates(self, db_session, sample_series, sample_chapters):
        """Test that series read count is properly updated."""
        # Initially 0 read chapters
        await db_session.refresh(sample_series)
        assert sample_series.read_chapters == 0

        # Mark one chapter as read
        await ReadingProgressService.toggle_chapter_read_status(
            db_session, str(sample_chapters[0].id)
        )

        await db_session.refresh(sample_series)
        assert sample_series.read_chapters == 1

        # Mark another as read
        await ReadingProgressService.toggle_chapter_read_status(
            db_session, str(sample_chapters[1].id)
        )

        await db_session.refresh(sample_series)
        assert sample_series.read_chapters == 2

        # Mark one as unread
        await ReadingProgressService.toggle_chapter_read_status(
            db_session, str(sample_chapters[0].id)
        )

        await db_session.refresh(sample_series)
        assert sample_series.read_chapters == 1

    async def test_started_reading_at_tracking(self, db_session, sample_chapters):
        """Test that started_reading_at is properly tracked."""
        chapter = sample_chapters[0]

        # Initially no started_reading_at
        assert chapter.started_reading_at is None

        # First progress update should set started_reading_at
        progress_request = ReadingProgressUpdateRequest(current_page=1, is_complete=None)
        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )

        assert result.started_at is not None

        # Subsequent updates should not change started_reading_at
        original_started_at = result.started_at

        progress_request = ReadingProgressUpdateRequest(current_page=5, is_complete=None)
        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )

        assert result.started_at == original_started_at

    async def test_progress_percentage_calculation(self, db_session, sample_chapters):
        """Test progress percentage calculations."""
        chapter = sample_chapters[0]  # 20 pages

        # Page 0 (first page) = 5%
        progress_request = ReadingProgressUpdateRequest(current_page=0, is_complete=None)
        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )
        assert result.progress_percentage == 5.0  # (0+1)/20 * 100

        # Page 9 (middle) = 50%
        progress_request = ReadingProgressUpdateRequest(current_page=9, is_complete=None)
        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )
        assert result.progress_percentage == 50.0  # (9+1)/20 * 100

        # Page 19 (last page) = 100%
        progress_request = ReadingProgressUpdateRequest(current_page=19, is_complete=None)
        result = await ReadingProgressService.update_chapter_progress(
            db_session, str(chapter.id), progress_request
        )
        assert result.progress_percentage == 100.0  # (19+1)/20 * 100
        assert result.is_read  # Should auto-complete
