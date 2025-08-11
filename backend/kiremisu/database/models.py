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
    Table,
    Column,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # User profile
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_failed_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # API tokens (for future use)
    api_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    api_key_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Preferences
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        "PushSubscription", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    reading_progress: Mapped[list["ReadingProgress"]] = relationship(
        "ReadingProgress", back_populates="user", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        # Index for login lookups
        Index("ix_users_username_active", "username", "is_active"),
        Index("ix_users_email_active", "email", "is_active"),
        # Index for admin queries
        Index("ix_users_admin_active", "is_admin", "is_active"),
        # Check constraints
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'",
            name="ck_users_email_format",
        ),
        CheckConstraint(
            "length(username) >= 3",
            name="ck_users_username_length",
        ),
    )


class ReadingProgress(Base):
    """User-specific reading progress tracking."""

    __tablename__ = "reading_progress"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    
    # Reading state
    last_page_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reading_progress")
    chapter: Mapped["Chapter"] = relationship("Chapter")
    
    __table_args__ = (
        # Unique constraint for user-chapter combination
        UniqueConstraint("user_id", "chapter_id", name="uq_reading_progress_user_chapter"),
        # Indexes for querying
        Index("ix_reading_progress_user_id", "user_id"),
        Index("ix_reading_progress_chapter_id", "chapter_id"),
        Index("ix_reading_progress_user_completed", "user_id", "is_completed"),
        Index("ix_reading_progress_last_read", "user_id", "last_read_at"),
    )


# Association table for many-to-many relationship between Series and Tags
series_tags = Table(
    "series_tags",
    Base.metadata,
    Column(
        "series_id",
        UUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    ),
    # Composite index for efficient querying
    Index("ix_series_tags_series_id", "series_id"),
    Index("ix_series_tags_tag_id", "tag_id"),
)


class Tag(Base):
    """User-defined tags for organizing series."""

    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint(
            "color IS NULL OR (color ~ '^#[0-9A-Fa-f]{6}$')", name="ck_tag_color_format"
        ),
    )

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color code #RRGGBB

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    series: Mapped[list["Series"]] = relationship(
        "Series", secondary=series_tags, back_populates="user_tags", lazy="select"
    )

    __table_args__ = (
        # Case-insensitive unique constraint for tag names
        Index("ix_tags_name_lower", "name", postgresql_ops={"name": "varchar_ops"}),
        # Index for searching tags by usage
        Index("ix_tags_usage_name", "usage_count", "name"),
    )


class Series(Base):
    """Manga series model."""

    __tablename__ = "series"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
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
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="series", cascade="all, delete-orphan"
    )
    user_tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=series_tags, back_populates="series", lazy="select"
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
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_reading_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
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
        # Index for started reading tracking (for progress queries)
        Index("ix_chapters_started_reading_at", "started_reading_at"),
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
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
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
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    series_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
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
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
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
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
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
        CheckConstraint(
            "job_type IN ('library_scan', 'download', 'chapter_update_check')",
            name="ck_job_queue_job_type",
        ),
        CheckConstraint("priority >= 1 AND priority <= 10", name="ck_job_queue_priority_range"),
        CheckConstraint("retry_count >= 0", name="ck_job_queue_retry_count"),
        CheckConstraint("max_retries >= 0", name="ck_job_queue_max_retries"),
    )


class FileOperation(Base):
    """Track file operations for safety and audit purposes."""

    __tablename__ = "file_operations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    operation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # rename, delete, move
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending, validated, in_progress, completed, failed, rolled_back

    # File paths
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    backup_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Affected database records
    affected_series_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    affected_chapter_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    # Operation metadata
    operation_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    validation_results: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rollback_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    __table_args__ = (
        # Index for operation monitoring and cleanup
        Index("ix_file_operations_status_created", "status", "created_at"),
        # Index for operation type filtering
        Index("ix_file_operations_type_status", "operation_type", "status"),
        # Constraints for data validation
        CheckConstraint(
            "operation_type IN ('rename', 'delete', 'move')", name="ck_file_operations_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'validated', 'in_progress', 'completed', 'failed', 'rolled_back')",
            name="ck_file_operations_status",
        ),
        CheckConstraint("retry_count >= 0", name="ck_file_operations_retry_count"),
        CheckConstraint("max_retries >= 0", name="ck_file_operations_max_retries"),
    )


class Notification(Base):
    """User notification model for system events and updates."""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new_chapter"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional relationships to series and chapter
    series_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("series.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )

    # Read status tracking
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    series: Mapped[Optional["Series"]] = relationship("Series", foreign_keys=[series_id])
    chapter: Mapped[Optional["Chapter"]] = relationship("Chapter", foreign_keys=[chapter_id])

    __table_args__ = (
        # Compound index for efficient unread notification queries per user
        Index("ix_notifications_user_unread_created", "user_id", "is_read", "created_at"),
        # Index for querying notifications by series
        Index("ix_notifications_series", "series_id", "created_at"),
        # Index for user notifications
        Index("ix_notifications_user_created", "user_id", "created_at"),
        # Check constraint for notification type
        CheckConstraint(
            "notification_type IN ('new_chapter', 'chapter_available', 'download_complete', 'download_failed', 'series_complete', 'library_update', 'system_alert', 'series_update')",
            name="ck_notification_type",
        ),
    )


class PushSubscription(Base):
    """Push notification subscriptions for web push."""

    __tablename__ = "push_subscriptions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    
    # User relationship
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Push subscription endpoint URL (unique per user, not globally)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)

    # Encryption keys for push messages
    keys: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # User agent of the subscribing browser
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Subscription status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Failure tracking
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Subscription expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False
    )
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="push_subscriptions")
    
    __table_args__ = (
        # Unique constraint on user_id + endpoint combination
        UniqueConstraint("user_id", "endpoint", name="uq_push_subscription_user_endpoint"),
        # Index for active subscriptions per user
        Index("ix_push_subscriptions_user_active", "user_id", "is_active"),
        # Index for endpoint lookup
        Index("ix_push_subscriptions_endpoint", "endpoint"),
        # Check constraint on endpoint
        CheckConstraint(
            "endpoint IS NOT NULL AND endpoint != ''",
            name="ck_push_subscription_endpoint_not_empty",
        ),
    )
