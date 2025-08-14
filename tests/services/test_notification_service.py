"""Comprehensive tests for NotificationService functionality."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Notification, Series
from kiremisu.services.notification_service import NotificationService


class TestNotificationService:
    """Test suite for NotificationService functionality."""

    async def test_create_chapter_notifications_single_chapter(
        self, db_session: AsyncSession, sample_series: Series, sample_chapter: Chapter
    ):
        """Test creating notifications for a single new chapter."""
        new_chapters = [sample_chapter]

        notifications = await NotificationService.create_chapter_notifications(
            db=db_session, series=sample_series, new_chapters=new_chapters
        )

        assert len(notifications) == 1
        notification = notifications[0]

        assert notification.notification_type == "new_chapter"
        assert sample_series.title_primary in notification.title
        assert f"Chapter {sample_chapter.chapter_number}" in notification.message
        assert notification.series_id == sample_series.id
        assert notification.chapter_id == sample_chapter.id
        assert not notification.is_read
        assert notification.read_at is None

        # Verify persistence
        db_notification = await db_session.get(Notification, notification.id)
        assert db_notification is not None

    async def test_create_chapter_notifications_multiple_chapters(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test creating notifications for multiple new chapters."""
        # Create multiple chapters
        chapters = []
        for i in range(3):
            chapter = Chapter(
                title=f"Chapter {i+1} Title",
                chapter_number=float(i + 1),
                volume_number=1,
                series_id=sample_series.id,
                file_path=f"/test/path/chapter_{i+1}.cbz",
                file_size=1000000,
                page_count=20
            )
            db_session.add(chapter)
            chapters.append(chapter)

        await db_session.commit()

        notifications = await NotificationService.create_chapter_notifications(
            db=db_session, series=sample_series, new_chapters=chapters
        )

        assert len(notifications) == 3

        # Verify each notification
        for i, notification in enumerate(notifications):
            assert notification.notification_type == "new_chapter"
            assert notification.series_id == sample_series.id
            assert notification.chapter_id == chapters[i].id
            assert f"Chapter {i+1}" in notification.message

    async def test_create_chapter_notifications_with_volume_and_title(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test creating notifications for chapters with volume and title."""
        chapter = Chapter(
            title="The Great Battle",
            chapter_number=15.5,
            volume_number=3,
            series_id=sample_series.id,
            file_path="/test/path/special_chapter.cbz",
            file_size=1000000,
            page_count=25
        )
        db_session.add(chapter)
        await db_session.commit()

        notifications = await NotificationService.create_chapter_notifications(
            db=db_session, series=sample_series, new_chapters=[chapter]
        )

        notification = notifications[0]
        expected_chapter_title = "Vol. 3, Chapter 15.5 - The Great Battle"
        assert expected_chapter_title in notification.message

    async def test_create_chapter_notifications_no_chapters(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test creating notifications with empty chapter list."""
        notifications = await NotificationService.create_chapter_notifications(
            db=db_session, series=sample_series, new_chapters=[]
        )

        assert notifications == []

    async def test_get_unread_count_empty(
        self, db_session: AsyncSession
    ):
        """Test getting unread count when no notifications exist."""
        count = await NotificationService.get_unread_count(db_session)
        assert count == 0

    async def test_get_unread_count_with_data(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test getting unread count with mixed read/unread notifications."""
        # Create notifications with mixed read status
        notifications = []
        for i in range(5):
            notification = Notification(
                notification_type="new_chapter",
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                series_id=sample_series.id,
                is_read=i % 2 == 0,  # Alternate read/unread
            )
            if notification.is_read:
                notification.read_at = datetime.now(UTC).replace(tzinfo=None)
            db_session.add(notification)
            notifications.append(notification)

        await db_session.commit()

        unread_count = await NotificationService.get_unread_count(db_session)
        expected_unread = len([n for n in notifications if not n.is_read])
        assert unread_count == expected_unread

    async def test_get_notifications_empty(
        self, db_session: AsyncSession
    ):
        """Test getting notifications when none exist."""
        notifications = await NotificationService.get_notifications(db_session)
        assert notifications == []

    async def test_get_notifications_with_data(
        self, db_session: AsyncSession, sample_series: Series, sample_chapter: Chapter
    ):
        """Test getting notifications with data including relationships."""
        # Create a notification
        notification = Notification(
            notification_type="new_chapter",
            title="Test Notification",
            message="Test message",
            series_id=sample_series.id,
            chapter_id=sample_chapter.id,
        )
        db_session.add(notification)
        await db_session.commit()

        notifications = await NotificationService.get_notifications(db_session)

        assert len(notifications) == 1
        retrieved_notification = notifications[0]

        # Verify relationships are loaded
        assert retrieved_notification.series is not None
        assert retrieved_notification.series.id == sample_series.id
        assert retrieved_notification.chapter is not None
        assert retrieved_notification.chapter.id == sample_chapter.id

    async def test_get_notifications_pagination(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test notification pagination."""
        # Create multiple notifications
        notification_count = 10
        for i in range(notification_count):
            notification = Notification(
                notification_type="new_chapter",
                title=f"Notification {i}",
                message=f"Message {i}",
                series_id=sample_series.id,
            )
            db_session.add(notification)

        await db_session.commit()

        # Test first page
        page1 = await NotificationService.get_notifications(
            db_session, skip=0, limit=5
        )
        assert len(page1) == 5

        # Test second page
        page2 = await NotificationService.get_notifications(
            db_session, skip=5, limit=5
        )
        assert len(page2) == 5

        # Ensure different notifications
        page1_ids = {n.id for n in page1}
        page2_ids = {n.id for n in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_get_notifications_unread_only(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test filtering notifications to unread only."""
        # Create mixed read/unread notifications
        unread_count = 0
        for i in range(5):
            is_read = i % 2 == 0
            notification = Notification(
                notification_type="new_chapter",
                title=f"Notification {i}",
                message=f"Message {i}",
                series_id=sample_series.id,
                is_read=is_read,
            )
            if is_read:
                notification.read_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                unread_count += 1

            db_session.add(notification)

        await db_session.commit()

        unread_notifications = await NotificationService.get_notifications(
            db_session, unread_only=True
        )

        assert len(unread_notifications) == unread_count
        for notification in unread_notifications:
            assert not notification.is_read

    async def test_get_notifications_ordering(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test that notifications are ordered by creation date (newest first)."""
        # Create notifications with different creation times
        notifications = []
        for i in range(3):
            notification = Notification(
                notification_type="new_chapter",
                title=f"Notification {i}",
                message=f"Message {i}",
                series_id=sample_series.id,
                created_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=i)
            )
            db_session.add(notification)
            notifications.append(notification)

        await db_session.commit()

        retrieved_notifications = await NotificationService.get_notifications(db_session)

        # Should be ordered by created_at descending (newest first)
        for i in range(len(retrieved_notifications) - 1):
            assert retrieved_notifications[i].created_at >= retrieved_notifications[i + 1].created_at

    async def test_mark_notification_read_success(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test successfully marking a notification as read."""
        # Create unread notification
        notification = Notification(
            notification_type="new_chapter",
            title="Test Notification",
            message="Test message",
            series_id=sample_series.id,
            is_read=False,
            read_at=None,
        )
        db_session.add(notification)
        await db_session.commit()

        # Mark as read
        updated_notification = await NotificationService.mark_notification_read(
            db_session, notification.id
        )

        assert updated_notification is not None
        assert updated_notification.is_read is True
        assert updated_notification.read_at is not None

        # Verify persistence
        await db_session.refresh(notification)
        assert notification.is_read is True
        assert notification.read_at is not None

    async def test_mark_notification_read_not_found(
        self, db_session: AsyncSession
    ):
        """Test marking non-existent notification as read."""
        fake_id = uuid4()

        result = await NotificationService.mark_notification_read(db_session, fake_id)

        assert result is None

    async def test_mark_notification_read_already_read(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test marking already read notification (idempotent)."""
        # Create read notification
        original_read_at = datetime.now(UTC).replace(tzinfo=None)
        notification = Notification(
            notification_type="new_chapter",
            title="Test Notification",
            message="Test message",
            series_id=sample_series.id,
            is_read=True,
            read_at=original_read_at,
        )
        db_session.add(notification)
        await db_session.commit()

        # Mark as read again
        updated_notification = await NotificationService.mark_notification_read(
            db_session, notification.id
        )

        assert updated_notification is not None
        assert updated_notification.is_read is True
        # read_at should remain unchanged
        assert updated_notification.read_at == original_read_at

    async def test_mark_all_read_success(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test marking all notifications as read."""
        # Create mixed read/unread notifications
        unread_count = 0
        for i in range(5):
            is_read = i % 2 == 0
            notification = Notification(
                notification_type="new_chapter",
                title=f"Notification {i}",
                message=f"Message {i}",
                series_id=sample_series.id,
                is_read=is_read,
            )
            if is_read:
                notification.read_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                unread_count += 1

            db_session.add(notification)

        await db_session.commit()

        marked_count = await NotificationService.mark_all_read(db_session)

        assert marked_count == unread_count

        # Verify all notifications are now read
        all_notifications = await NotificationService.get_notifications(db_session)
        for notification in all_notifications:
            assert notification.is_read is True
            assert notification.read_at is not None

    async def test_mark_all_read_empty(
        self, db_session: AsyncSession
    ):
        """Test marking all read when no notifications exist."""
        marked_count = await NotificationService.mark_all_read(db_session)
        assert marked_count == 0

    async def test_get_notification_by_id_success(
        self, db_session: AsyncSession, sample_series: Series, sample_chapter: Chapter
    ):
        """Test getting notification by ID with relationships loaded."""
        # Create notification
        notification = Notification(
            notification_type="new_chapter",
            title="Test Notification",
            message="Test message",
            series_id=sample_series.id,
            chapter_id=sample_chapter.id,
        )
        db_session.add(notification)
        await db_session.commit()

        retrieved_notification = await NotificationService.get_notification_by_id(
            db_session, notification.id
        )

        assert retrieved_notification is not None
        assert retrieved_notification.id == notification.id

        # Verify relationships are loaded
        assert retrieved_notification.series is not None
        assert retrieved_notification.series.id == sample_series.id
        assert retrieved_notification.chapter is not None
        assert retrieved_notification.chapter.id == sample_chapter.id

    async def test_get_notification_by_id_not_found(
        self, db_session: AsyncSession
    ):
        """Test getting non-existent notification by ID."""
        fake_id = uuid4()

        result = await NotificationService.get_notification_by_id(db_session, fake_id)

        assert result is None

    async def test_create_system_notification_basic(
        self, db_session: AsyncSession
    ):
        """Test creating basic system notification."""
        title = "System Alert"
        message = "A system event occurred."

        notification = await NotificationService.create_system_notification(
            db=db_session, title=title, message=message
        )

        assert notification.notification_type == "system_alert"
        assert notification.title == title
        assert notification.message == message
        assert notification.series_id is None
        assert notification.chapter_id is None
        assert not notification.is_read

    async def test_create_system_notification_with_references(
        self, db_session: AsyncSession, sample_series: Series, sample_chapter: Chapter
    ):
        """Test creating system notification with series/chapter references."""
        title = "Import Complete"
        message = "Chapter import completed successfully."

        notification = await NotificationService.create_system_notification(
            db=db_session,
            title=title,
            message=message,
            notification_type="import_complete",
            series_id=sample_series.id,
            chapter_id=sample_chapter.id,
        )

        assert notification.notification_type == "import_complete"
        assert notification.series_id == sample_series.id
        assert notification.chapter_id == sample_chapter.id

    async def test_cleanup_old_notifications_basic(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test cleaning up old read notifications."""
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create old read notification
        old_notification = Notification(
            notification_type="new_chapter",
            title="Old Notification",
            message="This is old",
            series_id=sample_series.id,
            is_read=True,
            read_at=now - timedelta(days=40),
            created_at=now - timedelta(days=40),
        )

        # Create recent read notification
        recent_notification = Notification(
            notification_type="new_chapter",
            title="Recent Notification",
            message="This is recent",
            series_id=sample_series.id,
            is_read=True,
            read_at=now - timedelta(days=10),
            created_at=now - timedelta(days=10),
        )

        db_session.add(old_notification)
        db_session.add(recent_notification)
        await db_session.commit()

        deleted_count = await NotificationService.cleanup_old_notifications(
            db_session, days=30, keep_unread=True
        )

        assert deleted_count == 1  # Only old read notification should be deleted

        # Verify only recent notification remains
        remaining_notifications = await NotificationService.get_notifications(db_session)
        assert len(remaining_notifications) == 1
        assert remaining_notifications[0].id == recent_notification.id

    async def test_cleanup_old_notifications_keep_unread(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test cleanup keeps unread notifications regardless of age."""
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create old unread notification
        old_unread_notification = Notification(
            notification_type="new_chapter",
            title="Old Unread Notification",
            message="This is old but unread",
            series_id=sample_series.id,
            is_read=False,
            created_at=now - timedelta(days=60),
        )

        # Create old read notification
        old_read_notification = Notification(
            notification_type="new_chapter",
            title="Old Read Notification",
            message="This is old and read",
            series_id=sample_series.id,
            is_read=True,
            read_at=now - timedelta(days=40),
            created_at=now - timedelta(days=60),
        )

        db_session.add(old_unread_notification)
        db_session.add(old_read_notification)
        await db_session.commit()

        deleted_count = await NotificationService.cleanup_old_notifications(
            db_session, days=30, keep_unread=True
        )

        assert deleted_count == 1  # Only old read notification should be deleted

        # Verify unread notification remains
        remaining_notifications = await NotificationService.get_notifications(db_session)
        assert len(remaining_notifications) == 1
        assert remaining_notifications[0].id == old_unread_notification.id
        assert not remaining_notifications[0].is_read

    async def test_cleanup_old_notifications_delete_all_old(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test cleanup deletes all old notifications when keep_unread=False."""
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create old notifications with different read status
        old_notifications = []
        for i in range(3):
            notification = Notification(
                notification_type="new_chapter",
                title=f"Old Notification {i}",
                message=f"This is old {i}",
                series_id=sample_series.id,
                is_read=i % 2 == 0,
                created_at=now - timedelta(days=40),
            )
            if notification.is_read:
                notification.read_at = now - timedelta(days=40)

            db_session.add(notification)
            old_notifications.append(notification)

        await db_session.commit()

        deleted_count = await NotificationService.cleanup_old_notifications(
            db_session, days=30, keep_unread=False
        )

        assert deleted_count == len(old_notifications)  # All should be deleted

        # Verify no notifications remain
        remaining_notifications = await NotificationService.get_notifications(db_session)
        assert len(remaining_notifications) == 0

    async def test_get_notification_stats_comprehensive(
        self, db_session: AsyncSession, sample_series: Series
    ):
        """Test getting comprehensive notification statistics."""
        # Create notifications with different types and read status
        notification_data = [
            ("new_chapter", True),
            ("new_chapter", False),
            ("system_alert", True),
            ("import_complete", False),
            ("import_complete", False),
        ]

        for notification_type, is_read in notification_data:
            notification = Notification(
                notification_type=notification_type,
                title=f"Test {notification_type}",
                message=f"Test message for {notification_type}",
                series_id=sample_series.id,
                is_read=is_read,
            )
            if is_read:
                notification.read_at = datetime.now(UTC).replace(tzinfo=None)

            db_session.add(notification)

        await db_session.commit()

        stats = await NotificationService.get_notification_stats(db_session)

        assert stats["total_notifications"] == len(notification_data)
        assert stats["read_notifications"] == 2
        assert stats["unread_notifications"] == 3

        # Verify type counts
        expected_type_counts = {"new_chapter": 2, "system_alert": 1, "import_complete": 2}
        assert stats["notifications_by_type"] == expected_type_counts

    async def test_get_notification_stats_empty(
        self, db_session: AsyncSession
    ):
        """Test getting stats when no notifications exist."""
        stats = await NotificationService.get_notification_stats(db_session)

        assert stats["total_notifications"] == 0
        assert stats["read_notifications"] == 0
        assert stats["unread_notifications"] == 0
        assert stats["notifications_by_type"] == {}


# Additional test fixtures
@pytest.fixture
async def sample_chapter(db_session: AsyncSession, sample_series: Series) -> Chapter:
    """Create a sample chapter for testing."""
    chapter = Chapter(
        title="Test Chapter",
        chapter_number=1.0,
        volume_number=1,
        series_id=sample_series.id,
        file_path="/test/path/chapter_001.cbz",
        file_size=1000000,
        page_count=20
    )
    db_session.add(chapter)
    await db_session.commit()
    return chapter
