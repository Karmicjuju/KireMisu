from typing import Dict, List, Optional, Any, Union
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.metadata_history import MetadataHistory

# Setup logging for database operations
logger = logging.getLogger(__name__)


class MetadataHistoryRepository:
    """Repository for MetadataHistory database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_history_entry(
        self,
        entity_type: str,
        entity_id: int,
        user_id: Optional[uuid.UUID],
        action: str,
        previous_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> MetadataHistory:
        """Create a new metadata history entry."""
        try:
            history = MetadataHistory(
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                action=action,
                previous_data=previous_data,
                new_data=new_data,
                changed_fields=changed_fields,
                description=description,
            )
            
            self.db.add(history)
            await self.db.commit()
            await self.db.refresh(history)
            return history
        except IntegrityError as e:
            await self.db.rollback()
            # Log the actual error for debugging but don't expose sensitive details
            logger.error(f"History entry creation failed with integrity error: {str(e)}")
            # Check for common integrity violations and provide safe error messages
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()
            if 'foreign key' in error_msg:
                raise ValueError("Invalid entity or user reference for history entry")
            else:
                raise ValueError("History entry creation failed due to data constraints")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error during history entry creation: {str(e)}")
            raise ValueError("History entry creation failed due to database error")

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MetadataHistory]:
        """Get history entries for a specific entity."""
        query = (
            select(MetadataHistory)
            .options(selectinload(MetadataHistory.user))
            .where(
                MetadataHistory.entity_type == entity_type,
                MetadataHistory.entity_id == entity_id,
            )
            .order_by(MetadataHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_history_by_id(self, history_id: int) -> Optional[MetadataHistory]:
        """Get a specific history entry by ID."""
        query = (
            select(MetadataHistory)
            .options(selectinload(MetadataHistory.user))
            .where(MetadataHistory.id == history_id)
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_history(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
        entity_type: Optional[str] = None,
    ) -> List[MetadataHistory]:
        """Get history entries for a specific user."""
        query = (
            select(MetadataHistory)
            .options(selectinload(MetadataHistory.user))
            .where(MetadataHistory.user_id == user_id)
            .order_by(MetadataHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        if entity_type:
            query = query.where(MetadataHistory.entity_type == entity_type)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_entity_history(self, entity_type: str, entity_id: int) -> int:
        """Count history entries for a specific entity."""
        query = (
            select(func.count(MetadataHistory.id))
            .where(
                MetadataHistory.entity_type == entity_type,
                MetadataHistory.entity_id == entity_id,
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar()

    async def delete_old_history(
        self,
        entity_type: str,
        entity_id: int,
        keep_count: int = 100,
    ) -> int:
        """Delete old history entries, keeping only the most recent ones."""
        try:
            # First get the IDs of entries to keep
            keep_query = (
                select(MetadataHistory.id)
                .where(
                    MetadataHistory.entity_type == entity_type,
                    MetadataHistory.entity_id == entity_id,
                )
                .order_by(MetadataHistory.created_at.desc())
                .limit(keep_count)
            )
            
            result = await self.db.execute(keep_query)
            keep_ids = [row[0] for row in result.fetchall()]
            
            if not keep_ids:
                return 0
            
            # Delete entries not in the keep list
            delete_query = (
                delete(MetadataHistory)
                .where(
                    MetadataHistory.entity_type == entity_type,
                    MetadataHistory.entity_id == entity_id,
                    ~MetadataHistory.id.in_(keep_ids),
                )
            )
            
            result = await self.db.execute(delete_query)
            await self.db.commit()
            return result.rowcount
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"History deletion failed with integrity error: {str(e)}")
            raise ValueError("Cannot delete history entries: there may be dependencies that prevent deletion")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error during history deletion: {str(e)}")
            raise ValueError("History deletion failed due to database error")