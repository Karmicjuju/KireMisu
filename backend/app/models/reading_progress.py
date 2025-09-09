import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime, 
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Float,
    Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class ReadingStatus(str, Enum):
    """Enum for reading status values."""
    UNREAD = "unread"
    READING = "reading"
    COMPLETED = "completed"


class ReadingProgress(Base):
    """Reading progress tracking for user chapters."""
    
    __tablename__ = "reading_progress"
    
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
    
    # Page-level progress
    current_page = Column(Integer, default=0, nullable=False)
    total_pages = Column(Integer, default=0, nullable=False)
    
    # Reading status
    status = Column(String(20), default=ReadingStatus.UNREAD.value, nullable=False, index=True)
    
    # Progress percentage (0.0 to 1.0)
    progress_percentage = Column(Float, default=0.0, nullable=False, index=True)
    
    # Completion tracking
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    
    # Reading time tracking (in seconds)
    reading_time_seconds = Column(Integer, default=0, nullable=False, server_default='0')
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_read_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user = relationship("User")
    chapter = relationship("Chapter")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'chapter_id', name='uq_reading_progress_user_chapter'),
    )
    
    def __repr__(self):
        return (
            f"<ReadingProgress(user_id={self.user_id}, chapter_id={self.chapter_id}, "
            f"status='{self.status}', progress={self.progress_percentage:.2%})>"
        )
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on current page."""
        if self.total_pages <= 0:
            return 0.0
        return min(self.current_page / self.total_pages, 1.0)
    
    def update_progress(self, current_page: int, total_pages: int) -> None:
        """Update reading progress and calculate derived fields."""
        self.current_page = max(0, current_page)
        self.total_pages = max(0, total_pages)
        self.progress_percentage = self.completion_percentage
        
        # Update status based on progress  
        if self.current_page == 0 and self.total_pages > 0:
            self.status = ReadingStatus.UNREAD.value
            self.is_completed = False
            self.started_at = None
        elif self.current_page >= self.total_pages - 1 and self.total_pages > 0:
            self.status = ReadingStatus.COMPLETED.value
            self.is_completed = True
            if not self.completed_at:
                self.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            self.status = ReadingStatus.READING.value
            self.is_completed = False
            if not self.started_at:
                self.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        self.last_read_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def add_reading_time(self, seconds: int) -> None:
        """Add reading time to the total."""
        if seconds > 0:
            if self.reading_time_seconds is None:
                self.reading_time_seconds = 0
            self.reading_time_seconds += seconds
    
    def mark_completed(self) -> None:
        """Mark chapter as completed."""
        self.status = ReadingStatus.COMPLETED.value
        self.is_completed = True
        self.progress_percentage = 1.0
        if self.total_pages and self.total_pages > 0:
            self.current_page = self.total_pages
        else:
            self.current_page = 1
            self.total_pages = 1
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not self.completed_at:
            self.completed_at = now
        if not self.started_at:
            self.started_at = now
        self.last_read_at = now
    
    def mark_unread(self) -> None:
        """Reset progress to unread state."""
        self.status = ReadingStatus.UNREAD.value
        self.is_completed = False
        self.progress_percentage = 0.0
        self.current_page = 0
        self.completed_at = None
        self.started_at = None
        self.last_read_at = datetime.now(timezone.utc).replace(tzinfo=None)