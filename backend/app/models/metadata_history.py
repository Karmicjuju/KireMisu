from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class MetadataHistory(Base):
    """Track changes to series and chapter metadata for audit and undo functionality."""

    __tablename__ = "metadata_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to the entity being tracked
    entity_type = Column(String(50), nullable=False, index=True)  # 'series' or 'chapter'
    entity_id = Column(Integer, nullable=False, index=True)
    
    # User who made the change
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Change details
    action = Column(String(50), nullable=False, index=True)  # 'create', 'update', 'delete'
    
    # Store before and after states as JSON
    previous_data = Column(JSON().with_variant(JSONB(), 'postgresql'), nullable=True)
    new_data = Column(JSON().with_variant(JSONB(), 'postgresql'), nullable=True)
    
    # Fields that were changed
    changed_fields = Column(JSON().with_variant(JSONB(), 'postgresql'), nullable=True)
    
    # Optional description of the change
    description = Column(Text, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="metadata_changes")

    def __repr__(self):
        return (
            f"<MetadataHistory(id={self.id}, entity_type='{self.entity_type}', "
            f"entity_id={self.entity_id}, action='{self.action}')>"
        )