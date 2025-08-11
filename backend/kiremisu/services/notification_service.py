"""Notification service for managing user notifications."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kiremisu.database.models import Notification, Series, Chapter, PushSubscription
from kiremisu.core.metrics import metrics_collector

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
        # Start metrics tracking for notification creation
        async with metrics_collector.track_polling_operation(
            "notification_creation", series_id=series.id, series_count=1
        ) as tracker:
            notifications = []

            logger.info(
                f"Creating notifications for {len(new_chapters)} new chapters in series: {series.title_primary}"
            )

            for chapter in new_chapters:
                logger.debug(
                    f"Creating notification for chapter {chapter.chapter_number} of series {series.id}"
                )

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
                logger.info(
                    f"Created {len(notifications)} notifications for series: {series.title_primary}"
                )

                # Update metrics
                tracker.notifications_created = len(notifications)
                metrics_collector.increment_counter(
                    "notifications.sent.last_hour", len(notifications)
                )
                metrics_collector.increment_counter(
                    "notifications.total.created", len(notifications)
                )

                # Send push notifications in batch for better performance
                try:
                    await NotificationService._send_batch_push_notifications(
                        db, series, new_chapters, notifications
                    )
                except Exception as e:
                    logger.error(f"Failed to send push notifications: {e}")
                    # Don't fail the entire operation if push notifications fail
            else:
                logger.debug(f"No notifications created for series: {series.title_primary}")

            return notifications

    @staticmethod
    async def _send_batch_push_notifications(
        db: AsyncSession, 
        series: Series, 
        chapters: List[Chapter], 
        notifications: List[Notification]
    ) -> None:
        """Send push notifications in optimized batches.
        
        Args:
            db: Database session
            series: Series model
            chapters: List of Chapter models
            notifications: List of Notification models
        """
        try:
            # Import here to avoid circular dependency
            from kiremisu.api.push_notifications import send_push_to_multiple_background
            
            # Get all active push subscriptions once instead of per notification
            result = await db.execute(
                select(PushSubscription).where(PushSubscription.is_active == True)
            )
            subscriptions = result.scalars().all()
            
            if not subscriptions:
                logger.debug("No active push subscriptions found")
                return
                
            logger.info(
                f"Sending batch push notifications to {len(subscriptions)} subscribers "
                f"for {len(chapters)} new chapters in {series.title_primary}"
            )
            
            # Group chapters by series for better notification efficiency
            if len(chapters) == 1:
                # Single chapter - send individual notification
                chapter = chapters[0]
                title = f"New Chapter: {series.title_primary}"
                body = f"Chapter {chapter.chapter_number}: {chapter.title or 'Untitled'}"
                
                data = {
                    "type": "new_chapter",
                    "notificationId": str(notifications[0].id),
                    "seriesId": str(series.id),
                    "chapterId": str(chapter.id),
                    "chapterNumber": chapter.chapter_number,
                    "seriesTitle": series.title_primary,
                }
                
                # Send to all subscriptions in background
                subscription_ids = [str(sub.id) for sub in subscriptions]
                await send_push_to_multiple_background(
                    subscription_ids=subscription_ids,
                    title=title,
                    body=body,
                    notification_type="new_chapter",
                    icon=series.cover_url,
                    data=data,
                )
                
                logger.info(f"Sent push notification for chapter {chapter.chapter_number}")
                
            elif len(chapters) > 1:
                # Multiple chapters - send batch notification
                chapter_numbers = sorted([ch.chapter_number for ch in chapters])
                first_chapter = min(chapter_numbers)
                last_chapter = max(chapter_numbers)
                
                if len(chapters) <= 3:
                    # Few chapters - list them
                    chapter_list = ", ".join([f"Ch. {num}" for num in chapter_numbers])
                    title = f"New Chapters: {series.title_primary}"
                    body = f"New chapters available: {chapter_list}"
                else:
                    # Many chapters - summarize
                    title = f"New Chapters: {series.title_primary}"
                    body = f"{len(chapters)} new chapters (Ch. {first_chapter}-{last_chapter})"
                
                data = {
                    "type": "new_chapters_batch",
                    "seriesId": str(series.id),
                    "seriesTitle": series.title_primary,
                    "chapterCount": len(chapters),
                    "firstChapter": first_chapter,
                    "lastChapter": last_chapter,
                    "notificationIds": [str(notif.id) for notif in notifications],
                }
                
                # Send batch notification
                subscription_ids = [str(sub.id) for sub in subscriptions]
                await send_push_to_multiple_background(
                    subscription_ids=subscription_ids,
                    title=title,
                    body=body,
                    notification_type="new_chapters_batch",
                    icon=series.cover_url,
                    data=data,
                )
                
                logger.info(
                    f"Sent batch push notification for {len(chapters)} chapters "
                    f"(Ch. {first_chapter}-{last_chapter})"
                )
                
        except Exception as e:
            logger.error(f"Failed to send batch push notifications for {series.title_primary}: {e}")
            raise

    @staticmethod
    async def send_bulk_notifications(
        db: AsyncSession, 
        notifications: List[tuple[Series, List[Chapter]]], 
        batch_size: int = 50
    ) -> List[Notification]:
        """Send notifications for multiple series in optimized batches.
        
        This method is useful for bulk operations like library scans where many
        series might have new chapters at once.
        
        Args:
            db: Database session
            notifications: List of tuples (Series, List[Chapter])
            batch_size: Maximum notifications to process at once
            
        Returns:
            List of all created Notification models
        """
        all_notifications = []
        
        # Get all active push subscriptions once for the entire batch
        result = await db.execute(
            select(PushSubscription).where(PushSubscription.is_active == True)
        )
        subscriptions = result.scalars().all()
        subscription_ids = [str(sub.id) for sub in subscriptions]
        
        logger.info(
            f"Processing bulk notifications for {len(notifications)} series "
            f"with {len(subscriptions)} active subscribers"
        )
        
        # Process notifications in batches to avoid overwhelming the system
        for i in range(0, len(notifications), batch_size):
            batch = notifications[i:i + batch_size]
            batch_notifications = []
            push_tasks = []
            
            # Create database notifications first
            for series, chapters in batch:
                series_notifications = []
                
                for chapter in chapters:
                    title = f"New chapter available: {series.title_primary}"
                    chapter_title = f"Chapter {chapter.chapter_number}"
                    if chapter.title:
                        chapter_title += f" - {chapter.title}"
                    
                    message = f"New chapter '{chapter_title}' is now available for reading."
                    
                    notification = Notification(
                        notification_type="new_chapter",
                        title=title,
                        message=message,
                        series_id=series.id,
                        chapter_id=chapter.id,
                    )
                    
                    db.add(notification)
                    series_notifications.append(notification)
                
                batch_notifications.extend(series_notifications)
                
                # Prepare push notification task for this series
                if subscription_ids and chapters:
                    push_tasks.append((series, chapters, series_notifications))
            
            # Commit database notifications for this batch
            if batch_notifications:
                await db.commit()
                all_notifications.extend(batch_notifications)
                
                # Send push notifications for this batch
                if push_tasks:
                    try:
                        await NotificationService._send_batch_push_notifications_bulk(
                            subscription_ids, push_tasks
                        )
                    except Exception as e:
                        logger.error(f"Failed to send push notifications for batch: {e}")
                        # Continue processing other batches
            
            logger.info(f"Processed batch {i // batch_size + 1}/{(len(notifications) + batch_size - 1) // batch_size}")
        
        logger.info(f"Completed bulk notification processing: {len(all_notifications)} notifications created")
        return all_notifications

    @staticmethod
    async def _send_batch_push_notifications_bulk(
        subscription_ids: List[str], 
        push_tasks: List[tuple[Series, List[Chapter], List[Notification]]]
    ) -> None:
        """Send push notifications for multiple series in a single batch operation.
        
        Args:
            subscription_ids: List of subscription IDs to send to
            push_tasks: List of tuples (Series, Chapters, Notifications)
        """
        try:
            from kiremisu.api.push_notifications import send_push_to_multiple_background
            import asyncio
            
            # Group similar notification types for efficiency
            single_chapter_tasks = []
            multi_chapter_tasks = []
            
            for series, chapters, notifications in push_tasks:
                if len(chapters) == 1:
                    single_chapter_tasks.append((series, chapters[0], notifications[0]))
                else:
                    multi_chapter_tasks.append((series, chapters, notifications))
            
            # Send single chapter notifications in parallel batches
            single_tasks = []
            for series, chapter, notification in single_chapter_tasks:
                title = f"New Chapter: {series.title_primary}"
                body = f"Chapter {chapter.chapter_number}: {chapter.title or 'Untitled'}"
                
                data = {
                    "type": "new_chapter",
                    "notificationId": str(notification.id),
                    "seriesId": str(series.id),
                    "chapterId": str(chapter.id),
                    "chapterNumber": chapter.chapter_number,
                    "seriesTitle": series.title_primary,
                }
                
                task = send_push_to_multiple_background(
                    subscription_ids=subscription_ids,
                    title=title,
                    body=body,
                    notification_type="new_chapter",
                    icon=series.cover_url,
                    data=data,
                )
                single_tasks.append(task)
            
            # Send multi-chapter notifications
            multi_tasks = []
            for series, chapters, notifications in multi_chapter_tasks:
                chapter_numbers = sorted([ch.chapter_number for ch in chapters])
                first_chapter = min(chapter_numbers)
                last_chapter = max(chapter_numbers)
                
                title = f"New Chapters: {series.title_primary}"
                body = f"{len(chapters)} new chapters (Ch. {first_chapter}-{last_chapter})"
                
                data = {
                    "type": "new_chapters_batch",
                    "seriesId": str(series.id),
                    "seriesTitle": series.title_primary,
                    "chapterCount": len(chapters),
                    "firstChapter": first_chapter,
                    "lastChapter": last_chapter,
                    "notificationIds": [str(notif.id) for notif in notifications],
                }
                
                task = send_push_to_multiple_background(
                    subscription_ids=subscription_ids,
                    title=title,
                    body=body,
                    notification_type="new_chapters_batch",
                    icon=series.cover_url,
                    data=data,
                )
                multi_tasks.append(task)
            
            # Execute all push notification tasks concurrently with controlled batching
            all_tasks = single_tasks + multi_tasks
            if all_tasks:
                # Limit concurrent push operations to avoid overwhelming the push service
                semaphore = asyncio.Semaphore(5)  # Max 5 concurrent push operations
                
                async def limited_task(task):
                    async with semaphore:
                        return await task
                
                await asyncio.gather(*[limited_task(task) for task in all_tasks])
                logger.info(f"Sent {len(all_tasks)} bulk push notifications")
                
        except Exception as e:
            logger.error(f"Failed to send bulk push notifications: {e}")
            raise

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
        db: AsyncSession, skip: int = 0, limit: int = 50, unread_only: bool = False
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
    async def mark_notification_read(
        db: AsyncSession, notification_id: UUID
    ) -> Optional[Notification]:
        """Mark a single notification as read.

        Args:
            db: Database session
            notification_id: Notification UUID to mark as read

        Returns:
            Updated Notification model or None if not found
        """
        logger.info(f"Marking notification {notification_id} as read")

        # Get the notification
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
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

        result = await db.execute(delete(Notification).where(and_(*conditions)))

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
            select(Notification.notification_type, func.count(Notification.id)).group_by(
                Notification.notification_type
            )
        )

        for notification_type, count in type_result.all():
            type_counts[notification_type] = count

        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "read_notifications": read_count,
            "notifications_by_type": type_counts,
        }
