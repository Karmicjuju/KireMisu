"""
Reading progress service for managing user reading statistics and progress tracking.

This service provides comprehensive reading progress functionality including:
- Chapter reading progress updates with automatic completion detection
- Series progress calculation and statistics
- User reading statistics and streak tracking
- Integration with existing chapter and series models
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kiremisu.database.models import Chapter, Series
from kiremisu.database.schemas import (
    ChapterResponse,
    ReadingProgressResponse,
    ReadingProgressUpdateRequest,
    SeriesProgressResponse,
    UserReadingStatsResponse,
)

logger = logging.getLogger(__name__)


class ReadingProgressService:
    """Service for managing reading progress and statistics."""

    @staticmethod
    async def update_chapter_progress(
        db: AsyncSession, chapter_id: str, progress: ReadingProgressUpdateRequest
    ) -> ReadingProgressResponse:
        """
        Update reading progress for a chapter.

        Args:
            db: Database session
            chapter_id: Chapter UUID
            progress: Progress update data

        Returns:
            Updated reading progress response

        Raises:
            ValueError: If chapter not found or invalid progress data
        """
        # Get chapter with series relationship
        result = await db.execute(
            select(Chapter).options(selectinload(Chapter.series)).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise ValueError(f"Chapter with ID {chapter_id} not found")

        if progress.current_page >= chapter.page_count:
            raise ValueError(
                f"Invalid page number {progress.current_page}. Chapter has {chapter.page_count} pages."
            )

        # Prepare update data
        update_data = {
            "last_read_page": progress.current_page,
            "updated_at": datetime.utcnow(),
        }

        # Track when reading started if this is the first progress update
        if chapter.last_read_page == 0 and progress.current_page > 0:
            update_data["started_reading_at"] = datetime.utcnow()

        # Determine if chapter should be marked as read
        is_complete = False
        if progress.is_complete is not None:
            is_complete = progress.is_complete
        else:
            # Auto-complete if user has reached the last page
            is_complete = progress.current_page >= chapter.page_count - 1

        if is_complete and not chapter.is_read:
            update_data["is_read"] = True
            update_data["read_at"] = datetime.utcnow()

        # Update chapter
        await db.execute(update(Chapter).where(Chapter.id == chapter_id).values(**update_data))

        # Update series read_chapters count if chapter was completed
        if is_complete and not chapter.is_read:
            # Manual count tracking - increment series read count
            series_result = await db.execute(select(Series).where(Series.id == chapter.series_id))
            series = series_result.scalar_one()
            new_read_count = series.read_chapters + 1

            await db.execute(
                update(Series)
                .where(Series.id == chapter.series_id)
                .values(read_chapters=new_read_count, updated_at=datetime.utcnow())
            )

        # Commit changes
        await db.commit()

        # Refresh chapter data
        await db.refresh(chapter)

        logger.info(
            "Chapter reading progress updated: chapter_id=%s, page=%d, complete=%s",
            chapter_id,
            progress.current_page,
            is_complete,
            extra={"series_id": str(chapter.series_id)},
        )

        # Calculate progress percentage
        progress_percentage = (
            (progress.current_page + 1) / chapter.page_count * 100 if chapter.page_count > 0 else 0
        )

        return ReadingProgressResponse(
            chapter_id=chapter.id,
            series_id=chapter.series_id,
            current_page=progress.current_page,
            total_pages=chapter.page_count,
            progress_percentage=progress_percentage,
            is_read=chapter.is_read,
            started_at=getattr(chapter, "started_reading_at", None),
            read_at=chapter.read_at,
            updated_at=chapter.updated_at,
        )

    @staticmethod
    async def toggle_chapter_read_status(
        db: AsyncSession, chapter_id: str
    ) -> Tuple[bool, datetime]:
        """
        Toggle the read status of a chapter.

        Args:
            db: Database session
            chapter_id: Chapter UUID

        Returns:
            Tuple of (new_read_status, read_at_timestamp)

        Raises:
            ValueError: If chapter not found
        """
        # Get chapter (fresh from database) - ensure we don't use cached data
        # Use execution_options to disable the identity map cache for this query
        result = await db.execute(
            select(Chapter)
            .where(Chapter.id == chapter_id)
            .execution_options(populate_existing=True)
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise ValueError(f"Chapter with ID {chapter_id} not found")

        # Store original read status to determine if change is needed
        original_read_status = chapter.is_read
        new_read_status = not original_read_status

        # Debug logging
        logger.info(
            "Toggle chapter read status: chapter_id=%s, current_status=%s, new_status=%s",
            chapter_id,
            original_read_status,
            new_read_status,
        )
        now = datetime.utcnow()

        update_data = {
            "is_read": new_read_status,
            "updated_at": now,
        }

        if new_read_status:
            # Mark as read - set read timestamp and complete page
            update_data["read_at"] = now
            update_data["last_read_page"] = max(0, chapter.page_count - 1)
            # Set started_reading_at if not already set
            if not getattr(chapter, "started_reading_at", None):
                update_data["started_reading_at"] = now
        else:
            # Mark as unread - clear read timestamp but keep progress
            update_data["read_at"] = None

        # Update chapter
        await db.execute(update(Chapter).where(Chapter.id == chapter_id).values(**update_data))

        # Update series read count manually - only if status actually changed
        if original_read_status != new_read_status:
            series_result = await db.execute(select(Series).where(Series.id == chapter.series_id))
            series = series_result.scalar_one()

            if new_read_status:
                # Chapter was marked as read - increment count
                new_read_count = series.read_chapters + 1
            else:
                # Chapter was marked as unread - decrement count
                new_read_count = max(0, series.read_chapters - 1)

            await db.execute(
                update(Series)
                .where(Series.id == chapter.series_id)
                .values(read_chapters=new_read_count, updated_at=datetime.utcnow())
            )

        await db.commit()

        logger.info(
            "Chapter read status toggled: chapter_id=%s, status=%s",
            chapter_id,
            new_read_status,
            extra={"series_id": str(chapter.series_id)},
        )

        return new_read_status, update_data.get("read_at")

    @staticmethod
    async def get_series_progress(db: AsyncSession, series_id: str) -> SeriesProgressResponse:
        """
        Get reading progress for a series.

        Args:
            db: Database session
            series_id: Series UUID

        Returns:
            Series progress information

        Raises:
            ValueError: If series not found
        """
        # Get series (fresh from database)
        series_result = await db.execute(
            select(Series).where(Series.id == series_id).execution_options(populate_existing=True)
        )
        series = series_result.scalar_one_or_none()

        if not series:
            raise ValueError(f"Series with ID {series_id} not found")

        # Get recent read chapters (up to 5)
        recent_chapters_result = await db.execute(
            select(Chapter)
            .where(Chapter.series_id == series_id, Chapter.is_read == True)
            .order_by(Chapter.read_at.desc().nulls_last())
            .limit(5)
        )
        recent_chapters = recent_chapters_result.scalars().all()

        # Get most recent read timestamp
        last_read_result = await db.execute(
            select(func.max(Chapter.read_at)).where(
                Chapter.series_id == series_id, Chapter.is_read == True
            )
        )
        last_read_at = last_read_result.scalar()

        # Calculate progress percentage
        progress_percentage = (
            (series.read_chapters / series.total_chapters * 100) if series.total_chapters > 0 else 0
        )

        return SeriesProgressResponse(
            series_id=series.id,
            total_chapters=series.total_chapters,
            read_chapters=series.read_chapters,
            progress_percentage=progress_percentage,
            recent_chapters=[ChapterResponse.from_model(chapter) for chapter in recent_chapters],
            last_read_at=last_read_at,
        )

    @staticmethod
    async def get_user_reading_stats(db: AsyncSession) -> UserReadingStatsResponse:
        """
        Get comprehensive user reading statistics.

        Args:
            db: Database session

        Returns:
            User reading statistics
        """
        # Get total counts
        total_series_result = await db.execute(select(func.count(Series.id)))
        total_series = total_series_result.scalar() or 0

        total_chapters_result = await db.execute(select(func.count(Chapter.id)))
        total_chapters = total_chapters_result.scalar() or 0

        read_chapters_result = await db.execute(
            select(func.count(Chapter.id)).where(Chapter.is_read == True)
        )
        read_chapters = read_chapters_result.scalar() or 0

        # Get chapters with partial progress (started but not completed)
        # Note: Using last_read_page > 0 as indicator since started_reading_at is temporarily disabled
        in_progress_result = await db.execute(
            select(func.count(Chapter.id)).where(
                and_(
                    Chapter.last_read_page > 0,
                    Chapter.is_read == False,
                )
            )
        )
        in_progress_chapters = in_progress_result.scalar() or 0

        # Calculate overall progress
        overall_progress = (read_chapters / total_chapters * 100) if total_chapters > 0 else 0

        # Get reading streak (consecutive days with reading activity)
        reading_streak = await ReadingProgressService._calculate_reading_streak(db)

        # Get reading activity for this week and month
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        chapters_this_week_result = await db.execute(
            select(func.count(Chapter.id)).where(
                and_(Chapter.is_read == True, Chapter.read_at >= week_start)
            )
        )
        chapters_this_week = chapters_this_week_result.scalar() or 0

        chapters_this_month_result = await db.execute(
            select(func.count(Chapter.id)).where(
                and_(Chapter.is_read == True, Chapter.read_at >= month_start)
            )
        )
        chapters_this_month = chapters_this_month_result.scalar() or 0

        # Get favorite genres (most read)
        favorite_genres = await ReadingProgressService._get_favorite_genres(db)

        # Get recent activity (up to 10)
        recent_activity_result = await db.execute(
            select(Chapter)
            .options(selectinload(Chapter.series))
            .where(Chapter.is_read == True)
            .order_by(Chapter.read_at.desc().nulls_last())
            .limit(10)
        )
        recent_activity = [
            ChapterResponse.from_model(chapter, include_series=True)
            for chapter in recent_activity_result.scalars().all()
        ]

        return UserReadingStatsResponse(
            total_series=total_series,
            total_chapters=total_chapters,
            read_chapters=read_chapters,
            in_progress_chapters=in_progress_chapters,
            overall_progress_percentage=overall_progress,
            reading_streak_days=reading_streak,
            chapters_read_this_week=chapters_this_week,
            chapters_read_this_month=chapters_this_month,
            favorite_genres=favorite_genres,
            recent_activity=recent_activity,
        )

    @staticmethod
    async def mark_series_read(db: AsyncSession, series_id: str) -> int:
        """
        Mark all chapters in a series as read.

        Args:
            db: Database session
            series_id: Series UUID

        Returns:
            Number of chapters updated

        Raises:
            ValueError: If series not found
        """
        # Verify series exists
        series_result = await db.execute(select(Series).where(Series.id == series_id))
        series = series_result.scalar_one_or_none()

        if not series:
            raise ValueError(f"Series with ID {series_id} not found")

        now = datetime.utcnow()

        # Update all unread chapters in the series
        result = await db.execute(
            update(Chapter)
            .where(and_(Chapter.series_id == series_id, Chapter.is_read == False))
            .values(
                is_read=True,
                read_at=now,
                updated_at=now,
                last_read_page=Chapter.page_count - 1,
            )
            .execution_options(synchronize_session="fetch", populate_existing=True)
        )

        chapters_updated = result.rowcount

        # Update series read_chapters count manually - add the number of chapters we just marked as read
        new_read_count = series.read_chapters + chapters_updated

        await db.execute(
            update(Series)
            .where(Series.id == series_id)
            .values(read_chapters=new_read_count, updated_at=datetime.utcnow())
        )

        await db.commit()

        logger.info(
            "Series marked as read: series_id=%s, chapters_updated=%d",
            series_id,
            chapters_updated,
        )

        return chapters_updated

    @staticmethod
    async def mark_series_unread(db: AsyncSession, series_id: str) -> int:
        """
        Mark all chapters in a series as unread.

        Args:
            db: Database session
            series_id: Series UUID

        Returns:
            Number of chapters updated

        Raises:
            ValueError: If series not found
        """
        # Verify series exists
        series_result = await db.execute(select(Series).where(Series.id == series_id))
        series = series_result.scalar_one_or_none()

        if not series:
            raise ValueError(f"Series with ID {series_id} not found")

        now = datetime.utcnow()

        # Update all read chapters in the series
        result = await db.execute(
            update(Chapter)
            .where(and_(Chapter.series_id == series_id, Chapter.is_read == True))
            .values(
                is_read=False,
                read_at=None,
                updated_at=now,
                # Keep progress but don't reset to 0
            )
            .execution_options(synchronize_session="fetch", populate_existing=True)
        )

        chapters_updated = result.rowcount

        # Update series read_chapters count manually - subtract the chapters we just marked as unread
        new_read_count = max(0, series.read_chapters - chapters_updated)

        await db.execute(
            update(Series)
            .where(Series.id == series_id)
            .values(read_chapters=new_read_count, updated_at=datetime.utcnow())
        )

        await db.commit()

        logger.info(
            "Series marked as unread: series_id=%s, chapters_updated=%d",
            series_id,
            chapters_updated,
        )

        return chapters_updated

    @staticmethod
    async def reconcile_series_counts(db: AsyncSession, series_id: str = None) -> Dict[str, int]:
        """
        Reconcile series read counts with actual chapter counts.

        Args:
            db: Database session
            series_id: Optional specific series ID to reconcile, or None for all series

        Returns:
            Dictionary with reconciliation results
        """
        results = {"series_checked": 0, "discrepancies_found": 0, "series_fixed": 0}

        # Get series to check
        if series_id:
            series_query = select(Series).where(Series.id == series_id)
        else:
            series_query = select(Series)

        series_result = await db.execute(series_query)
        series_list = series_result.scalars().all()

        for series in series_list:
            results["series_checked"] += 1

            # Count actual read chapters
            actual_count_result = await db.execute(
                select(func.count(Chapter.id)).where(
                    and_(Chapter.series_id == series.id, Chapter.is_read == True)
                )
            )
            actual_count = actual_count_result.scalar() or 0

            # Check for discrepancy
            if series.read_chapters != actual_count:
                results["discrepancies_found"] += 1

                logger.warning(
                    "Series count discrepancy found: series_id=%s, stored=%d, actual=%d",
                    series.id,
                    series.read_chapters,
                    actual_count,
                )

                # Fix the discrepancy
                await db.execute(
                    update(Series)
                    .where(Series.id == series.id)
                    .values(read_chapters=actual_count, updated_at=datetime.utcnow())
                )
                results["series_fixed"] += 1

        await db.commit()

        logger.info("Series count reconciliation completed: %s", results)

        return results

    @staticmethod
    async def validate_series_count(db: AsyncSession, series_id: str) -> bool:
        """
        Validate that a series count matches the actual chapter count.

        Args:
            db: Database session
            series_id: Series UUID

        Returns:
            True if counts match, False if there's a discrepancy
        """
        # Get series
        series_result = await db.execute(select(Series).where(Series.id == series_id))
        series = series_result.scalar_one_or_none()

        if not series:
            raise ValueError(f"Series with ID {series_id} not found")

        # Count actual read chapters
        actual_count_result = await db.execute(
            select(func.count(Chapter.id)).where(
                and_(Chapter.series_id == series_id, Chapter.is_read == True)
            )
        )
        actual_count = actual_count_result.scalar() or 0

        is_valid = series.read_chapters == actual_count

        if not is_valid:
            logger.warning(
                "Series count validation failed: series_id=%s, stored=%d, actual=%d",
                series_id,
                series.read_chapters,
                actual_count,
            )

        return is_valid

    @staticmethod
    async def _calculate_reading_streak(db: AsyncSession) -> int:
        """
        Calculate the current reading streak in days.

        Args:
            db: Database session

        Returns:
            Current reading streak in days
        """
        now = datetime.utcnow()
        current_date = now.date()
        streak = 0

        # Check each day going backwards until we find a day with no reading
        for days_back in range(365):  # Limit to 1 year max
            check_date = current_date - timedelta(days=days_back)
            next_date = check_date + timedelta(days=1)

            # Count chapters read on this date
            result = await db.execute(
                select(func.count(Chapter.id)).where(
                    and_(
                        Chapter.is_read == True,
                        Chapter.read_at >= check_date,
                        Chapter.read_at < next_date,
                    )
                )
            )
            chapters_read = result.scalar() or 0

            if chapters_read > 0:
                streak += 1
            else:
                # If this is the first day (today) and no reading, streak is 0
                # If this is a later day, we've reached the end of the streak
                break

        return streak

    @staticmethod
    async def _get_favorite_genres(db: AsyncSession, limit: int = 5) -> List[str]:
        """
        Get the user's favorite genres based on read chapters.

        Args:
            db: Database session
            limit: Maximum number of genres to return

        Returns:
            List of favorite genre names
        """
        # Get all read chapters with series data
        result = await db.execute(
            select(Chapter, Series.genres)
            .join(Series, Chapter.series_id == Series.id)
            .where(Chapter.is_read == True)
        )

        # Count genre occurrences
        genre_counts = defaultdict(int)
        for chapter, genres in result.fetchall():
            for genre in genres or []:
                genre_counts[genre] += 1

        # Sort by count and return top genres
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)

        return [genre for genre, _ in sorted_genres[:limit]]
