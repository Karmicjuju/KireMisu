"""Service layer for reading progress tracking and management."""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc, and_, or_
from fastapi import HTTPException

from app.models.reading_progress import ReadingProgress, ReadingStatus
from app.models.reading_history import ReadingHistory, ReadingEventType
from app.models.chapter import Chapter
from app.models.series import Series
from app.models.user import User


class ProgressService:
    """Service for managing reading progress and statistics."""
    
    def __init__(self):
        pass
    
    async def update_chapter_progress(
        self,
        db: Session,
        user_id: uuid.UUID,
        chapter_id: int,
        current_page: int,
        total_pages: int,
        session_duration: Optional[int] = None,
        device_info: Optional[str] = None
    ) -> ReadingProgress:
        """
        Update reading progress for a chapter.
        
        Args:
            db: Database session
            user_id: ID of the user
            chapter_id: ID of the chapter
            current_page: Current page number (0-indexed)
            total_pages: Total number of pages in chapter
            session_duration: Optional session duration in seconds
            device_info: Optional device information
            
        Returns:
            Updated ReadingProgress object
        """
        # Get or create progress record
        progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id,
            ReadingProgress.chapter_id == chapter_id
        ).first()
        
        if not progress:
            # Get chapter for series_id
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            
            progress = ReadingProgress(
                user_id=user_id,
                chapter_id=chapter_id
            )
            db.add(progress)
        
        # Store previous state for history
        previous_page = progress.current_page
        was_just_started = progress.status == ReadingStatus.UNREAD.value
        
        # Update progress
        progress.update_progress(current_page, total_pages)
        
        # Add reading time if provided
        if session_duration:
            progress.add_reading_time(session_duration)
        
        # Create history entry
        await self._create_history_event(
            db, user_id, chapter_id, progress, previous_page, 
            session_duration, device_info, was_just_started
        )
        
        db.commit()
        return progress
    
    async def mark_chapter_read(
        self,
        db: Session,
        user_id: uuid.UUID,
        chapter_id: int,
        device_info: Optional[str] = None
    ) -> ReadingProgress:
        """Mark a chapter as read."""
        progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id,
            ReadingProgress.chapter_id == chapter_id
        ).first()
        
        if not progress:
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            
            progress = ReadingProgress(
                user_id=user_id,
                chapter_id=chapter_id
            )
            db.add(progress)
        
        progress.mark_completed()
        
        # Create history event
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        history_event = ReadingHistory.create_marked_read_event(
            user_id=user_id,
            chapter_id=chapter_id,
            series_id=chapter.series_id,
            device_info=device_info
        )
        db.add(history_event)
        
        db.commit()
        return progress
    
    async def mark_chapter_unread(
        self,
        db: Session,
        user_id: uuid.UUID,
        chapter_id: int,
        device_info: Optional[str] = None
    ) -> Optional[ReadingProgress]:
        """Mark a chapter as unread."""
        progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id,
            ReadingProgress.chapter_id == chapter_id
        ).first()
        
        if progress:
            progress.mark_unread()
            
            # Create history event
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            history_event = ReadingHistory(
                user_id=user_id,
                chapter_id=chapter_id,
                series_id=chapter.series_id,
                event_type=ReadingEventType.MARKED_UNREAD.value,
                progress_percentage=0,
                device_info=device_info
            )
            db.add(history_event)
            
            db.commit()
            return progress
        
        return None
    
    async def bulk_mark_read(
        self,
        db: Session,
        user_id: uuid.UUID,
        chapter_ids: List[int],
        device_info: Optional[str] = None
    ) -> int:
        """Mark multiple chapters as read."""
        count = 0
        
        for chapter_id in chapter_ids:
            try:
                await self.mark_chapter_read(db, user_id, chapter_id, device_info)
                count += 1
            except HTTPException:
                # Skip chapters that don't exist
                continue
        
        return count
    
    async def bulk_mark_unread(
        self,
        db: Session,
        user_id: uuid.UUID,
        chapter_ids: List[int],
        device_info: Optional[str] = None
    ) -> int:
        """Mark multiple chapters as unread."""
        count = 0
        
        for chapter_id in chapter_ids:
            result = await self.mark_chapter_unread(db, user_id, chapter_id, device_info)
            if result:
                count += 1
        
        return count
    
    async def get_series_progress(
        self,
        db: Session,
        user_id: uuid.UUID,
        series_id: int
    ) -> Dict[str, Any]:
        """Get reading progress for an entire series."""
        # Get all chapters in series
        chapters = db.query(Chapter).filter(
            Chapter.series_id == series_id
        ).order_by(Chapter.number.asc()).all()
        
        if not chapters:
            raise HTTPException(status_code=404, detail="Series not found or has no chapters")
        
        # Get progress for all chapters
        progress_records = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id,
            ReadingProgress.chapter_id.in_([ch.id for ch in chapters])
        ).all()
        
        # Create progress map
        progress_map = {p.chapter_id: p for p in progress_records}
        
        # Calculate statistics
        total_chapters = len(chapters)
        read_chapters = 0
        reading_chapters = 0
        total_reading_time = 0
        
        chapter_progress = []
        for chapter in chapters:
            progress = progress_map.get(chapter.id)
            
            if progress:
                total_reading_time += progress.reading_time_seconds
                if progress.is_completed:
                    read_chapters += 1
                elif progress.status == ReadingStatus.READING.value:
                    reading_chapters += 1
                
                chapter_progress.append({
                    'chapter_id': chapter.id,
                    'chapter_number': str(chapter.number),
                    'chapter_title': chapter.title,
                    'status': progress.status,
                    'current_page': progress.current_page,
                    'total_pages': progress.total_pages,
                    'progress_percentage': progress.progress_percentage,
                    'last_read_at': progress.last_read_at.isoformat() if progress.last_read_at else None
                })
            else:
                chapter_progress.append({
                    'chapter_id': chapter.id,
                    'chapter_number': str(chapter.number),
                    'chapter_title': chapter.title,
                    'status': ReadingStatus.UNREAD.value,
                    'current_page': 0,
                    'total_pages': 0,
                    'progress_percentage': 0.0,
                    'last_read_at': None
                })
        
        completion_percentage = (read_chapters / total_chapters) * 100 if total_chapters > 0 else 0
        
        return {
            'series_id': series_id,
            'total_chapters': total_chapters,
            'read_chapters': read_chapters,
            'reading_chapters': reading_chapters,
            'unread_chapters': total_chapters - read_chapters - reading_chapters,
            'completion_percentage': completion_percentage,
            'total_reading_time_seconds': total_reading_time,
            'chapters': chapter_progress
        }
    
    async def get_reading_history(
        self,
        db: Session,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        series_id: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get reading history timeline for user."""
        query = db.query(ReadingHistory).options(
            selectinload(ReadingHistory.chapter),
            selectinload(ReadingHistory.series)
        ).filter(
            ReadingHistory.user_id == user_id
        )
        
        if series_id:
            query = query.filter(ReadingHistory.series_id == series_id)
        
        if event_type:
            query = query.filter(ReadingHistory.event_type == event_type)
        
        history_records = query.order_by(
            desc(ReadingHistory.event_timestamp)
        ).offset(offset).limit(limit).all()
        
        return [
            {
                'id': record.id,
                'event_type': record.event_type,
                'series_title': record.series.title if record.series else None,
                'chapter_number': str(record.chapter.number) if record.chapter else None,
                'chapter_title': record.chapter.title if record.chapter else None,
                'page_number': record.page_number,
                'total_pages': record.total_pages,
                'progress_percentage': record.progress_percentage,
                'session_duration_seconds': record.session_duration_seconds,
                'reading_speed_pages_per_minute': record.reading_speed_pages_per_minute,
                'event_timestamp': record.event_timestamp.isoformat(),
                'notes': record.notes
            }
            for record in history_records
        ]
    
    async def get_reading_statistics(
        self,
        db: Session,
        user_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive reading statistics for user."""
        cutoff_date = datetime.now(datetime.UTC).replace(tzinfo=None) - timedelta(days=days)
        
        # Get recent reading history
        recent_history = db.query(ReadingHistory).filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.event_timestamp >= cutoff_date
        ).all()
        
        # Get all progress records
        all_progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == user_id
        ).all()
        
        # Calculate statistics
        total_reading_time = sum(p.reading_time_seconds for p in all_progress)
        total_chapters_completed = sum(1 for p in all_progress if p.is_completed)
        
        # Recent activity statistics
        recent_reading_time = sum(
            h.session_duration_seconds for h in recent_history 
            if h.session_duration_seconds
        )
        recent_chapters = len(set(
            h.chapter_id for h in recent_history 
            if h.event_type in [ReadingEventType.COMPLETED.value, ReadingEventType.MARKED_READ.value]
        ))
        
        # Reading streak calculation
        reading_streak = await self._calculate_reading_streak(db, user_id)
        
        # Average reading speed
        speed_records = [h.reading_speed_pages_per_minute for h in recent_history if h.reading_speed_pages_per_minute]
        avg_reading_speed = sum(speed_records) / len(speed_records) if speed_records else 0
        
        return {
            'period_days': days,
            'total_reading_time_seconds': total_reading_time,
            'total_chapters_completed': total_chapters_completed,
            'recent_reading_time_seconds': recent_reading_time,
            'recent_chapters_completed': recent_chapters,
            'current_reading_streak_days': reading_streak,
            'average_reading_speed_pages_per_minute': round(avg_reading_speed, 1),
            'activity_summary': {
                'chapters_per_day': recent_chapters / days if days > 0 else 0,
                'minutes_per_day': recent_reading_time / 60 / days if days > 0 else 0
            }
        }
    
    async def _create_history_event(
        self,
        db: Session,
        user_id: uuid.UUID,
        chapter_id: int,
        progress: ReadingProgress,
        previous_page: int,
        session_duration: Optional[int],
        device_info: Optional[str],
        was_just_started: bool
    ):
        """Create appropriate history event based on progress change."""
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return
        
        # Determine event type
        if was_just_started and progress.current_page > 0:
            event_type = ReadingEventType.STARTED.value
        elif progress.is_completed and previous_page < progress.total_pages - 1:
            event_type = ReadingEventType.COMPLETED.value
        else:
            event_type = ReadingEventType.PROGRESS_UPDATE.value
        
        # Calculate session stats
        pages_read = max(0, progress.current_page - previous_page)
        
        if event_type == ReadingEventType.STARTED.value:
            history_event = ReadingHistory.create_started_event(
                user_id=user_id,
                chapter_id=chapter_id,
                series_id=chapter.series_id,
                total_pages=progress.total_pages,
                device_info=device_info
            )
        elif event_type == ReadingEventType.COMPLETED.value:
            history_event = ReadingHistory.create_completed_event(
                user_id=user_id,
                chapter_id=chapter_id,
                series_id=chapter.series_id,
                total_pages=progress.total_pages,
                session_duration=session_duration,
                device_info=device_info
            )
        else:
            history_event = ReadingHistory.create_progress_event(
                user_id=user_id,
                chapter_id=chapter_id,
                series_id=chapter.series_id,
                page_number=progress.current_page,
                total_pages=progress.total_pages,
                session_duration=session_duration,
                pages_read=pages_read,
                device_info=device_info
            )
        
        db.add(history_event)
    
    async def _calculate_reading_streak(
        self,
        db: Session,
        user_id: uuid.UUID
    ) -> int:
        """Calculate current reading streak in days."""
        # Get daily reading activity for the last 365 days
        cutoff_date = datetime.now(datetime.UTC).replace(tzinfo=None) - timedelta(days=365)
        
        daily_activity = db.query(
            func.date(ReadingHistory.event_timestamp).label('date')
        ).filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.event_timestamp >= cutoff_date,
            ReadingHistory.event_type.in_([
                ReadingEventType.PROGRESS_UPDATE.value,
                ReadingEventType.COMPLETED.value,
                ReadingEventType.MARKED_READ.value
            ])
        ).group_by(
            func.date(ReadingHistory.event_timestamp)
        ).order_by(
            desc(func.date(ReadingHistory.event_timestamp))
        ).all()
        
        if not daily_activity:
            return 0
        
        # Calculate consecutive days
        streak = 0
        current_date = datetime.now(datetime.UTC).replace(tzinfo=None).date()
        
        for activity_date, in daily_activity:
            if isinstance(activity_date, str):
                activity_date = datetime.strptime(activity_date, '%Y-%m-%d').date()
            
            days_diff = (current_date - activity_date).days
            
            if streak == 0 and days_diff <= 1:
                # Start of streak (today or yesterday)
                streak = 1
                current_date = activity_date - timedelta(days=1)
            elif days_diff == 1:
                # Consecutive day
                streak += 1
                current_date = activity_date - timedelta(days=1)
            else:
                # Break in streak
                break
        
        return streak