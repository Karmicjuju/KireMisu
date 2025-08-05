"""Database models for KireMisu."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    DateTime,
    String,
    Text,
    Boolean,
    Integer,
    JSON,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Series(Base):
    """Manga series model."""

    __tablename__ = "series"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title_primary: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    title_alternative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    artist: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    genres: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    publication_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    content_rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    # File system information
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # External source information
    mangadx_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, unique=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # User customization
    user_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    custom_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Watching configuration
    watching_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    watching_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_watched_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Statistics
    total_chapters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_chapters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="series", cascade="all, delete-orphan"
    )


class Chapter(Base):
    """Manga chapter model."""

    __tablename__ = "chapters"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    series_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("series.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Chapter identification
    chapter_number: Mapped[float] = mapped_column(nullable=False, index=True)
    volume_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # File system information
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # External source information
    mangadx_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, unique=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Reading progress
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_read_page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    series: Mapped["Series"] = relationship("Series", back_populates="chapters")
    annotations: Mapped[list["Annotation"]] = relationship(
        "Annotation", back_populates="chapter", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Compound index for unique chapter per series
        Index("ix_chapters_series_chapter_volume", "series_id", "chapter_number", "volume_number"),
        # Index for ordering chapters within series
        Index("ix_chapters_series_ordering", "series_id", "volume_number", "chapter_number"),
        # Index for read chapters by series (for progress calculations)
        Index("ix_chapters_series_read", "series_id", "is_read"),
        # Index for recent read chapters (for dashboard and progress queries)
        Index("ix_chapters_read_at", "is_read", "read_at"),
    )


class Annotation(Base):
    """Chapter annotation model for user notes."""

    __tablename__ = "annotations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    chapter_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Annotation content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    annotation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="note"
    )  # note, bookmark, highlight

    # Position fields for page-specific placement (normalized 0-1)
    position_x: Mapped[Optional[float]] = mapped_column(nullable=True)
    position_y: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Color field for annotation customization (hex format)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="annotations")

    __table_args__ = (
        # Check constraints for position validation (0-1 normalized)
        CheckConstraint(
            "position_x IS NULL OR (position_x >= 0 AND position_x <= 1)",
            name="ck_annotations_position_x_range",
        ),
        CheckConstraint(
            "position_y IS NULL OR (position_y >= 0 AND position_y <= 1)",
            name="ck_annotations_position_y_range",
        ),
        # Check constraint for color format validation (hex color)
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_annotations_color_format",
        ),
    )


class UserList(Base):
    """User-created lists/collections."""

    __tablename__ = "user_lists"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    series_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class LibraryPath(Base):
    """Configured library paths for manga storage."""

    __tablename__ = "library_paths"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scan_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    last_scan: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class JobQueue(Base):
    """Background job queue using PostgreSQL."""

    __tablename__ = "job_queue"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending, running, completed, failed
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    # Execution tracking
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # Compound index for job processing queries (status + priority + scheduled_at)
        Index("ix_job_queue_processing", "status", "priority", "scheduled_at"),
        # Compound index for job type filtering with status
        Index("ix_job_queue_type_status", "job_type", "status"),
        # Index for cleanup queries (status + completed_at)
        Index("ix_job_queue_cleanup", "status", "completed_at"),
        # Index for retry logic (status + retry_count)
        Index("ix_job_queue_retry", "status", "retry_count"),
        # Constraints for data validation
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')", name="ck_job_queue_status"
        ),
        CheckConstraint("priority >= 1 AND priority <= 10", name="ck_job_queue_priority_range"),
        CheckConstraint("retry_count >= 0", name="ck_job_queue_retry_count"),
        CheckConstraint("max_retries >= 0", name="ck_job_queue_max_retries"),
    )
