from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint, Index
from sqlalchemy.sql import func

from app.db.database import Base


class LibraryPath(Base):
    """Library path model for managing multiple manga storage locations."""

    __tablename__ = "library_paths"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    path = Column(String(1000), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint('path', name='uq_library_paths_path'),
        UniqueConstraint('name', name='uq_library_paths_name'),
        Index('idx_library_paths_active_priority', 'is_active', 'priority'),
    )

    def __repr__(self):
        return f"<LibraryPath(id={self.id}, name='{self.name}', path='{self.path}', active={self.is_active})>"