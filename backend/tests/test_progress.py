"""Tests for reading progress tracking functionality."""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.db.database import Base
from app.models.user import User
from app.models.series import Series
from app.models.chapter import Chapter
from app.models.reading_progress import ReadingProgress, ReadingStatus
from app.models.reading_history import ReadingHistory, ReadingEventType
from app.services.progress import ProgressService


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_progress.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_user(db_session):
    """Create sample user for testing."""
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpassword",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_series(db_session):
    """Create sample series for testing."""
    series = Series(
        title="Test Manga",
        description="A test manga series",
        author="Test Author"
    )
    db_session.add(series)
    db_session.commit()
    return series


@pytest.fixture
def sample_chapters(db_session, sample_series):
    """Create sample chapters for testing."""
    chapters = []
    for i in range(3):
        chapter = Chapter(
            series_id=sample_series.id,
            number=i + 1,
            title=f"Chapter {i + 1}",
            file_path=f"/test/chapter{i+1}.cbz"
        )
        db_session.add(chapter)
        chapters.append(chapter)
    
    db_session.commit()
    return chapters


@pytest.fixture
def progress_service():
    """Create ProgressService instance."""
    return ProgressService()


class TestProgressService:
    """Tests for ProgressService functionality."""
    
    @pytest.mark.asyncio
    async def test_update_chapter_progress_new(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test updating progress for a new chapter."""
        chapter = sample_chapters[0]
        
        # Update progress
        progress = await progress_service.update_chapter_progress(
            db_session,
            sample_user.id,
            chapter.id,
            current_page=5,
            total_pages=20,
            session_duration=300
        )
        
        # Assertions
        assert progress.user_id == sample_user.id
        assert progress.chapter_id == chapter.id
        assert progress.current_page == 5
        assert progress.total_pages == 20
        assert progress.status == ReadingStatus.READING.value
        assert progress.progress_percentage == 0.25  # 5/20
        assert not progress.is_completed
        assert progress.reading_time_seconds == 300
        assert progress.started_at is not None
        assert progress.completed_at is None
        
        # Check history was created
        history_count = db_session.query(ReadingHistory).filter(
            ReadingHistory.user_id == sample_user.id,
            ReadingHistory.chapter_id == chapter.id
        ).count()
        assert history_count == 1
    
    @pytest.mark.asyncio
    async def test_update_chapter_progress_completion(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test completing a chapter."""
        chapter = sample_chapters[0]
        
        # Complete chapter
        progress = await progress_service.update_chapter_progress(
            db_session,
            sample_user.id,
            chapter.id,
            current_page=19,  # Last page
            total_pages=20,
            session_duration=1200
        )
        
        # Assertions
        assert progress.status == ReadingStatus.COMPLETED.value
        assert progress.is_completed
        assert progress.progress_percentage == 0.95  # 19/20
        assert progress.completed_at is not None
        assert progress.reading_time_seconds == 1200
    
    @pytest.mark.asyncio
    async def test_mark_chapter_read(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test marking a chapter as read."""
        chapter = sample_chapters[0]
        
        progress = await progress_service.mark_chapter_read(
            db_session,
            sample_user.id,
            chapter.id
        )
        
        # Assertions
        assert progress.status == ReadingStatus.COMPLETED.value
        assert progress.is_completed
        assert progress.progress_percentage == 1.0
        assert progress.completed_at is not None
        
        # Check history event
        history = db_session.query(ReadingHistory).filter(
            ReadingHistory.user_id == sample_user.id,
            ReadingHistory.chapter_id == chapter.id,
            ReadingHistory.event_type == ReadingEventType.MARKED_READ.value
        ).first()
        assert history is not None
    
    @pytest.mark.asyncio
    async def test_mark_chapter_unread(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test marking a chapter as unread."""
        chapter = sample_chapters[0]
        
        # First mark as read
        await progress_service.mark_chapter_read(
            db_session,
            sample_user.id,
            chapter.id
        )
        
        # Then mark as unread
        progress = await progress_service.mark_chapter_unread(
            db_session,
            sample_user.id,
            chapter.id
        )
        
        # Assertions
        assert progress.status == ReadingStatus.UNREAD.value
        assert not progress.is_completed
        assert progress.progress_percentage == 0.0
        assert progress.current_page == 0
        assert progress.completed_at is None
        assert progress.started_at is None
    
    @pytest.mark.asyncio
    async def test_bulk_mark_read(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test bulk marking chapters as read."""
        chapter_ids = [ch.id for ch in sample_chapters]
        
        count = await progress_service.bulk_mark_read(
            db_session,
            sample_user.id,
            chapter_ids
        )
        
        # Assertions
        assert count == len(sample_chapters)
        
        # Check all chapters are marked as read
        progress_records = db_session.query(ReadingProgress).filter(
            ReadingProgress.user_id == sample_user.id,
            ReadingProgress.chapter_id.in_(chapter_ids)
        ).all()
        
        assert len(progress_records) == len(sample_chapters)
        for progress in progress_records:
            assert progress.is_completed
            assert progress.status == ReadingStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_bulk_mark_unread(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test bulk marking chapters as unread."""
        chapter_ids = [ch.id for ch in sample_chapters]
        
        # First mark all as read
        await progress_service.bulk_mark_read(
            db_session,
            sample_user.id,
            chapter_ids
        )
        
        # Then mark as unread
        count = await progress_service.bulk_mark_unread(
            db_session,
            sample_user.id,
            chapter_ids
        )
        
        # Assertions
        assert count == len(sample_chapters)
        
        # Check all chapters are unread
        progress_records = db_session.query(ReadingProgress).filter(
            ReadingProgress.user_id == sample_user.id,
            ReadingProgress.chapter_id.in_(chapter_ids)
        ).all()
        
        for progress in progress_records:
            assert not progress.is_completed
            assert progress.status == ReadingStatus.UNREAD.value
    
    @pytest.mark.asyncio
    async def test_get_series_progress(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_series,
        sample_chapters
    ):
        """Test getting series progress summary."""
        # Mark first chapter as read, second as reading
        await progress_service.mark_chapter_read(
            db_session,
            sample_user.id,
            sample_chapters[0].id
        )
        
        await progress_service.update_chapter_progress(
            db_session,
            sample_user.id,
            sample_chapters[1].id,
            current_page=5,
            total_pages=15,
            session_duration=600
        )
        
        # Get series progress
        series_progress = await progress_service.get_series_progress(
            db_session,
            sample_user.id,
            sample_series.id
        )
        
        # Assertions
        assert series_progress['series_id'] == sample_series.id
        assert series_progress['total_chapters'] == 3
        assert series_progress['read_chapters'] == 1
        assert series_progress['reading_chapters'] == 1
        assert series_progress['unread_chapters'] == 1
        assert series_progress['completion_percentage'] == pytest.approx(33.33, rel=1e-2)
        assert series_progress['total_reading_time_seconds'] == 600
        assert len(series_progress['chapters']) == 3
    
    @pytest.mark.asyncio
    async def test_get_reading_history(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test getting reading history."""
        # Create some reading activity
        await progress_service.update_chapter_progress(
            db_session,
            sample_user.id,
            sample_chapters[0].id,
            current_page=10,
            total_pages=20
        )
        
        await progress_service.mark_chapter_read(
            db_session,
            sample_user.id,
            sample_chapters[1].id
        )
        
        # Get history
        history = await progress_service.get_reading_history(
            db_session,
            sample_user.id,
            limit=10
        )
        
        # Assertions
        assert len(history) >= 2  # At least 2 events
        
        # Check history entries have required fields
        for entry in history:
            assert 'event_type' in entry
            assert 'series_title' in entry
            assert 'chapter_number' in entry
            assert 'event_timestamp' in entry
    
    @pytest.mark.asyncio
    async def test_get_reading_statistics(
        self, 
        db_session, 
        progress_service, 
        sample_user, 
        sample_chapters
    ):
        """Test getting reading statistics."""
        # Create reading activity
        for i, chapter in enumerate(sample_chapters):
            await progress_service.update_chapter_progress(
                db_session,
                sample_user.id,
                chapter.id,
                current_page=19,
                total_pages=20,
                session_duration=300 * (i + 1)
            )
        
        # Get statistics
        stats = await progress_service.get_reading_statistics(
            db_session,
            sample_user.id,
            days=30
        )
        
        # Assertions
        assert stats['period_days'] == 30
        assert stats['total_reading_time_seconds'] >= 1800  # 300 + 600 + 900
        assert stats['total_chapters_completed'] == 3
        assert 'recent_reading_time_seconds' in stats
        assert 'current_reading_streak_days' in stats
        assert 'activity_summary' in stats


class TestReadingProgressModel:
    """Tests for ReadingProgress model."""
    
    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        progress = ReadingProgress(
            user_id=uuid.uuid4(),
            chapter_id=1
        )
        
        # Test with valid pages
        progress.update_progress(5, 20)
        assert progress.completion_percentage == 0.25
        assert progress.progress_percentage == 0.25
        assert progress.status == ReadingStatus.READING.value
        
        # Test completion
        progress.update_progress(19, 20)
        assert progress.status == ReadingStatus.COMPLETED.value
        assert progress.is_completed
        
        # Test edge cases
        progress.update_progress(0, 20)
        assert progress.status == ReadingStatus.UNREAD.value
        assert not progress.is_completed
    
    def test_mark_completed(self):
        """Test mark_completed method."""
        progress = ReadingProgress(
            user_id=uuid.uuid4(),
            chapter_id=1
        )
        
        progress.update_progress(0, 20)  # Start as unread
        progress.mark_completed()
        
        assert progress.status == ReadingStatus.COMPLETED.value
        assert progress.is_completed
        assert progress.progress_percentage == 1.0
        assert progress.completed_at is not None
        assert progress.started_at is not None
    
    def test_mark_unread(self):
        """Test mark_unread method."""
        progress = ReadingProgress(
            user_id=uuid.uuid4(),
            chapter_id=1
        )
        
        # Start as completed
        progress.mark_completed()
        assert progress.is_completed
        
        # Mark as unread
        progress.mark_unread()
        
        assert progress.status == ReadingStatus.UNREAD.value
        assert not progress.is_completed
        assert progress.progress_percentage == 0.0
        assert progress.current_page == 0
        assert progress.completed_at is None
        assert progress.started_at is None
    
    def test_reading_time_tracking(self):
        """Test reading time accumulation."""
        progress = ReadingProgress(
            user_id=uuid.uuid4(),
            chapter_id=1
        )
        
        # Add reading time
        progress.add_reading_time(300)  # 5 minutes
        assert progress.reading_time_seconds == 300
        
        progress.add_reading_time(420)  # 7 more minutes
        assert progress.reading_time_seconds == 720  # 12 minutes total
        
        # Test invalid time
        progress.add_reading_time(-100)  # Should be ignored
        assert progress.reading_time_seconds == 720


class TestReadingHistoryModel:
    """Tests for ReadingHistory model."""
    
    def test_create_started_event(self):
        """Test creating started reading event."""
        user_id = uuid.uuid4()
        event = ReadingHistory.create_started_event(
            user_id=user_id,
            chapter_id=1,
            series_id=1,
            total_pages=20,
            device_info="test_device"
        )
        
        assert event.user_id == user_id
        assert event.chapter_id == 1
        assert event.series_id == 1
        assert event.event_type == ReadingEventType.STARTED.value
        assert event.page_number == 0
        assert event.total_pages == 20
        assert event.progress_percentage == 0
        assert event.device_info == "test_device"
    
    def test_create_progress_event(self):
        """Test creating progress update event."""
        user_id = uuid.uuid4()
        event = ReadingHistory.create_progress_event(
            user_id=user_id,
            chapter_id=1,
            series_id=1,
            page_number=10,
            total_pages=20,
            session_duration=600,
            pages_read=5
        )
        
        assert event.event_type == ReadingEventType.PROGRESS_UPDATE.value
        assert event.page_number == 10
        assert event.progress_percentage == 50  # 10/20 * 100
        assert event.session_duration_seconds == 600
        assert event.pages_read_in_session == 5
        assert event.reading_speed_pages_per_minute == 0  # 5 pages in 10 minutes
    
    def test_create_completed_event(self):
        """Test creating completed reading event."""
        user_id = uuid.uuid4()
        event = ReadingHistory.create_completed_event(
            user_id=user_id,
            chapter_id=1,
            series_id=1,
            total_pages=20,
            session_duration=1200
        )
        
        assert event.event_type == ReadingEventType.COMPLETED.value
        assert event.page_number == 20
        assert event.progress_percentage == 100
        assert event.session_duration_seconds == 1200
    
    def test_is_recent_event(self):
        """Test recent event detection."""
        # Create recent event
        recent_event = ReadingHistory(
            user_id=uuid.uuid4(),
            chapter_id=1,
            series_id=1,
            event_type=ReadingEventType.PROGRESS_UPDATE.value,
            event_timestamp=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
        )
        
        # Create old event  
        old_event = ReadingHistory(
            user_id=uuid.uuid4(),
            chapter_id=1,
            series_id=1,
            event_type=ReadingEventType.PROGRESS_UPDATE.value,
            event_timestamp=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        )
        
        assert recent_event.is_recent_event(minutes=30)
        assert not old_event.is_recent_event(minutes=30)


if __name__ == "__main__":
    pytest.main([__file__])