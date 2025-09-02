from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Series(Base):
    """Series model for manga series metadata and management."""

    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True, index=True)
    cover_path = Column(String(1000), nullable=True)
    metadata_json = Column(JSON().with_variant(JSONB(), 'postgresql'), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    chapters = relationship(
        "Chapter", back_populates="series", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Series(id={self.id}, title='{self.title}', author='{self.author}')>"

