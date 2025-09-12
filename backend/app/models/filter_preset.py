"""SQLAlchemy model for filter presets."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.database import Base


class FilterPreset(Base):
    """Filter preset model for saving and reusing filter combinations."""

    __tablename__ = "filter_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    user_id = Column(String(36), nullable=False, index=True)  # UUID as string
    
    # Store filter and sort parameters as JSONB for flexibility
    filters_json = Column(JSONB, nullable=False)
    sorting_json = Column(JSONB, nullable=True)
    
    # Public presets can be shared across users
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Indexes for performance
    __table_args__ = (
        # Composite index for user's presets
        Index('ix_filter_presets_user_name', 'user_id', 'name'),
        # Index for public presets
        Index('ix_filter_presets_public', 'is_public', 'name'),
        # GIN index for filter JSON queries
        Index(
            'ix_filter_presets_filters_gin',
            'filters_json',
            postgresql_using='gin'
        ),
    )

    def __repr__(self):
        return f"<FilterPreset(id={self.id}, name='{self.name}', user_id='{self.user_id}', public={self.is_public})>"