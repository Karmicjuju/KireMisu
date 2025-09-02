from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Chapter(Base):
    """Chapter model for individual manga chapters."""

    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(
        Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number = Column(Numeric(10, 2), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    file_path = Column(String(1000), nullable=False)
    read_status = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    series = relationship("Series", back_populates="chapters")

    __table_args__ = (
        UniqueConstraint('series_id', 'number', name='uq_chapters_series_number'),
    )

    def __repr__(self):
        return (
            f"<Chapter(id={self.id}, series_id={self.series_id}, "
            f"number={self.number}, title='{self.title}')>"
        )

