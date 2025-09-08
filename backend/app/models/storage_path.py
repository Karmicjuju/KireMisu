"""Storage path model for managing library storage locations."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class StoragePath(Base):
    """Model for manga library storage paths."""
    
    __tablename__ = "storage_paths"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)  # User-friendly name
    path = Column(String(500), nullable=False, unique=True, index=True)  # Filesystem path
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_network = Column(Boolean, nullable=False, default=False)  # Network-mounted storage flag
    priority = Column(Integer, nullable=False, default=0)  # Scan priority (higher first)
    
    # Storage metrics (updated during scans)
    total_space_bytes = Column(BigInteger, nullable=True)  # Total storage space
    used_space_bytes = Column(BigInteger, nullable=True)   # Used storage space
    file_count = Column(Integer, nullable=False, default=0)  # Number of manga files
    series_count = Column(Integer, nullable=False, default=0)  # Number of series
    
    # Validation status
    is_accessible = Column(Boolean, nullable=False, default=False)  # Path accessibility
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_error = Column(Text, nullable=True)  # Last validation error message
    
    # Additional metadata (renamed to avoid conflict with SQLAlchemy's metadata)
    extra_metadata = Column(
        JSON().with_variant(JSONB(), 'postgresql'),
        nullable=False,
        default=dict
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<StoragePath(id={self.id}, name='{self.name}', path='{self.path}')>"