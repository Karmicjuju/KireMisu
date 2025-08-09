"""Notification service for managing user notifications."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kiremisu.database.models import Notification, Series, Chapter

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing user notifications."""

    @staticmethod
    async def create_chapter_notifications(
        db: AsyncSession, series: Series, new_chapters: List[Chapter]
    ) -> List[Notification]:
        """Create notifications for new chapters.

        Args:
            db: Database session
            series: Series model
            new_chapters: List of new Chapter models

        Returns:
            List of created Notification models
        """
        notifications = []

        for chapter in new_chapters:
            # Format notification title and message
            title = f"New chapter available: {series.title_primary}"
            
            chapter_title = f"Chapter {chapter.chapter_number}"
            if chapter.volume_number:
                chapter_title = f"Vol. {chapter.volume_number}, {chapter_title}"
            if chapter.title:
                chapter_title += f" - {chapter.title}"
            
            message = f"New chapter '{chapter_title}' is now available for reading."

            # Create notification
            notification = Notification(
                notification_type="new_chapter",
                title=title,
                message=message,
                series_id=series.id,
                chapter_id=chapter.id,
            )

            db.add(notification)
            notifications.append(notification)

            logger.info(
                f"Created notification for new chapter: {series.title_primary} - {chapter_title}"
            )

        if notifications:
            await db.commit()
            logger.info(f"Created {len(notifications)} notifications for series: {series.title_primary}")

        return notifications

    @staticmethod
    async def get_unread_count(db: AsyncSession) -> int:
        """Get count of unread notifications.

        Args:
            db: Database session

        Returns:
            Number of unread notifications
        """
        result = await db.execute(
            select(func.count(Notification.id)).where(Notification.is_read == False)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_notifications(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 50, 
        unread_only: bool = False
    ) -> List[Notification]:
        """Get paginated list of notifications.

        Args:
            db: Database session
            skip: Number of notifications to skip
            limit: Maximum number of notifications to return
            unread_only: If True, only return unread notifications

        Returns:
            List of Notification models with relationships loaded
        """
        query = select(Notification).options(
            selectinload(Notification.series),
            selectinload(Notification.chapter),
        )

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def mark_notification_read(db: AsyncSession, notification_id: UUID) -> Optional[Notification]:
        """Mark a single notification as read.

        Args:
            db: Database session
            notification_id: Notification UUID to mark as read

        Returns:
            Updated Notification model or None if not found
        """
        logger.info(f"Marking notification {notification_id} as read")

        # Get the notification
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if not notification:
            logger.warning(f"Notification not found: {notification_id}")
            return None

        if notification.is_read:
            logger.debug(f"Notification {notification_id} is already read")
            return notification

        # Mark as read
        await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        await db.commit()

        # Refresh to get updated values
        await db.refresh(notification)

        logger.info(f"Successfully marked notification {notification_id} as read")
        return notification

    @staticmethod
    async def mark_all_read(db: AsyncSession) -> int:
        """Mark all notifications as read.

        Args:
            db: Database session

        Returns:
            Number of notifications that were marked as read
        """
        logger.info("Marking all notifications as read")

        # Update all unread notifications
        result = await db.execute(
            update(Notification)
            .where(Notification.is_read == False)
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        await db.commit()

        marked_count = result.rowcount
        logger.info(f"Successfully marked {marked_count} notifications as read")
        return marked_count

    @staticmethod
    async def get_notification_by_id(
        db: AsyncSession, notification_id: UUID
    ) -> Optional[Notification]:
        """Get a notification by ID with relationships loaded.

        Args:
            db: Database session
            notification_id: Notification UUID

        Returns:
            Notification model or None if not found
        """
        result = await db.execute(
            select(Notification)
            .options(
                selectinload(Notification.series),
                selectinload(Notification.chapter),
            )
            .where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_system_notification(
        db: AsyncSession,
        title: str,
        message: str,
        notification_type: str = "system_alert",
        series_id: Optional[UUID] = None,
        chapter_id: Optional[UUID] = None,
    ) -> Notification:
        """Create a system notification.

        Args:
            db: Database session
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            series_id: Optional series ID
            chapter_id: Optional chapter ID

        Returns:
            Created Notification model
        """
        logger.info(f"Creating system notification: {title}")

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            series_id=series_id,
            chapter_id=chapter_id,
        )

        db.add(notification)
        await db.commit()

        logger.info(f"Created system notification: {notification.id}")
        return notification

    @staticmethod
    async def cleanup_old_notifications(
        db: AsyncSession, days: int = 30, keep_unread: bool = True
    ) -> int:
        """Clean up old read notifications.

        Args:
            db: Database session
            days: Delete notifications older than this many days
            keep_unread: If True, keep unread notifications regardless of age

        Returns:
            Number of notifications deleted
        """
        from datetime import timedelta

        logger.info(f"Cleaning up notifications older than {days} days (keep_unread={keep_unread})")

        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

        # Build query conditions
        conditions = [Notification.created_at < cutoff_date]
        
        if keep_unread:
            conditions.append(Notification.is_read == True)

        # Delete notifications
        from sqlalchemy import delete

        result = await db.execute(
            delete(Notification).where(and_(*conditions))
        )

        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return deleted_count

    @staticmethod
    async def get_notification_stats(db: AsyncSession) -> dict:
        """Get statistics about notifications.

        Args:
            db: Database session

        Returns:
            Dict with notification statistics
        """
        # Count by read status
        total_result = await db.execute(select(func.count(Notification.id)))
        total_count = total_result.scalar() or 0

        unread_result = await db.execute(
            select(func.count(Notification.id)).where(Notification.is_read == False)
        )
        unread_count = unread_result.scalar() or 0

        read_count = total_count - unread_count

        # Count by type
        type_counts = {}
        type_result = await db.execute(
            select(Notification.notification_type, func.count(Notification.id))
            .group_by(Notification.notification_type)
        )
        
        for notification_type, count in type_result.all():
            type_counts[notification_type] = count

        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "read_notifications": read_count,
            "notifications_by_type": type_counts,
        }