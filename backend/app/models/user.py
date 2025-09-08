import uuid
from datetime import datetime
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Boolean, Column, DateTime, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class User(SQLAlchemyBaseUserTable[uuid.UUID], Base):
    """User model using FastAPI-Users with custom fields."""
    
    __tablename__ = "users"
    
    # Use UUID as primary key (FastAPI-Users default)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    
    # Custom fields
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Additional timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint('username', name='uq_users_username'),
        UniqueConstraint('email', name='uq_users_email'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
