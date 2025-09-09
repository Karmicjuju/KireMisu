import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class ReadingEventType(str, Enum):
    """Enum for different types of reading events."""
    STARTED = "started"
    PROGRESS_UPDATE = "progress_update"
    RESUMED = "resumed" 
    COMPLETED = "completed"
    MARKED_READ = "marked_read"
    MARKED_UNREAD = "marked_unread"
    SESSION_END = "session_end"


class ReadingHistory(Base):
    """History of reading events for tracking user activity timeline."""
    
    __tablename__ = "reading_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    series_id = Column(
        Integer,
        ForeignKey("series.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Event details
    event_type = Column(String(30), nullable=False, index=True)
    
    # Progress snapshot at time of event
    page_number = Column(Integer, nullable=True)
    total_pages = Column(Integer, nullable=True)
    progress_percentage = Column(Integer, nullable=True)  # Store as 0-100
    
    # Session information
    session_duration_seconds = Column(Integer, nullable=True)
    pages_read_in_session = Column(Integer, nullable=True)
    
    # Additional context
    notes = Column(Text, nullable=True)
    
    # Device/client information (for cross-device sync)
    device_info = Column(String(255), nullable=True)
    
    # Reading statistics for this event
    reading_speed_pages_per_minute = Column(Integer, nullable=True)
    
    # Timestamps
    event_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user = relationship("User")
    chapter = relationship("Chapter")
    series = relationship("Series")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_reading_history_user_timestamp', 'user_id', 'event_timestamp'),
        Index('ix_reading_history_series_timestamp', 'series_id', 'event_timestamp'),
        Index('ix_reading_history_chapter_timestamp', 'chapter_id', 'event_timestamp'),
        Index('ix_reading_history_user_event_type', 'user_id', 'event_type'),
    )
    
    def __repr__(self):
        return (
            f"<ReadingHistory(user_id={self.user_id}, chapter_id={self.chapter_id}, "
            f"event_type='{self.event_type}', timestamp={self.event_timestamp})>"
        )
    
    @classmethod
    def create_started_event(
        cls,
        user_id: uuid.UUID,
        chapter_id: int,
        series_id: int,
        total_pages: int = 0,
        device_info: str = None
    ) -> "ReadingHistory":
        """Create a 'started reading' event."""
        return cls(
            user_id=user_id,
            chapter_id=chapter_id,
            series_id=series_id,
            event_type=ReadingEventType.STARTED.value,
            page_number=0,
            total_pages=total_pages,
            progress_percentage=0,
            device_info=device_info
        )
    
    @classmethod
    def create_progress_event(
        cls,
        user_id: uuid.UUID,
        chapter_id: int,
        series_id: int,
        page_number: int,
        total_pages: int,
        session_duration: int = None,
        pages_read: int = None,
        device_info: str = None
    ) -> "ReadingHistory":
        """Create a progress update event."""
        progress_pct = int((page_number / total_pages * 100)) if total_pages > 0 else 0
        
        # Calculate reading speed if we have session data
        reading_speed = None
        if session_duration and pages_read and session_duration > 0:
            reading_speed = int((pages_read / (session_duration / 60)))  # pages per minute
        
        return cls(
            user_id=user_id,
            chapter_id=chapter_id,
            series_id=series_id,
            event_type=ReadingEventType.PROGRESS_UPDATE.value,
            page_number=page_number,
            total_pages=total_pages,
            progress_percentage=progress_pct,
            session_duration_seconds=session_duration,
            pages_read_in_session=pages_read,
            reading_speed_pages_per_minute=reading_speed,
            device_info=device_info
        )
    
    @classmethod
    def create_completed_event(
        cls,
        user_id: uuid.UUID,
        chapter_id: int,
        series_id: int,
        total_pages: int,
        session_duration: int = None,
        device_info: str = None
    ) -> "ReadingHistory":
        """Create a chapter completed event."""
        return cls(
            user_id=user_id,
            chapter_id=chapter_id,
            series_id=series_id,
            event_type=ReadingEventType.COMPLETED.value,
            page_number=total_pages,
            total_pages=total_pages,
            progress_percentage=100,
            session_duration_seconds=session_duration,
            device_info=device_info
        )
    
    @classmethod
    def create_marked_read_event(
        cls,
        user_id: uuid.UUID,
        chapter_id: int,
        series_id: int,
        device_info: str = None
    ) -> "ReadingHistory":
        """Create a 'marked as read' event."""
        return cls(
            user_id=user_id,
            chapter_id=chapter_id,
            series_id=series_id,
            event_type=ReadingEventType.MARKED_READ.value,
            progress_percentage=100,
            device_info=device_info
        )
    
    def is_recent_event(self, minutes: int = 30) -> bool:
        """Check if this event happened within the specified minutes."""
        if not self.event_timestamp:
            return False
        
        time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - self.event_timestamp.replace(tzinfo=None)
        return time_diff.total_seconds() < (minutes * 60)