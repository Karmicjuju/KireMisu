from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, or_, func, update, delete
from sqlalchemy.future import select

from app.models.series import Series
from app.schemas.series import SeriesCreate, SeriesUpdate

# Setup logging for database operations
logger = logging.getLogger(__name__)


class AsyncSeriesRepository:
    """Async repository layer for series data access operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_series(self, series_data: SeriesCreate) -> Series:
        """Create a new series in the database."""
        db_series = Series(
            title=series_data.title,
            description=series_data.description,
            author=series_data.author,
            artist=series_data.artist,
            status=series_data.status,
            cover_path=series_data.cover_path,
            metadata_json=series_data.metadata_json,
        )

        try:
            self.db.add(db_series)
            await self.db.commit()
            await self.db.refresh(db_series)
            return db_series
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Series creation failed with integrity error: {str(e)}")
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()
            if 'duplicate' in error_msg or 'unique' in error_msg:
                raise ValueError("Series with this title already exists")
            elif 'foreign key' in error_msg:
                raise ValueError("Invalid reference to related data")
            else:
                raise ValueError("Series creation failed due to data constraints")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error during series creation: {str(e)}")
            raise ValueError("Series creation failed due to database error")

    async def get_series_by_id(self, series_id: int) -> Optional[Series]:
        """Get series by ID."""
        query = select(Series).where(Series.id == series_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_series_by_title(self, title: str) -> Optional[Series]:
        """Get series by exact title."""
        query = select(Series).where(Series.title == title)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_series(self, skip: int = 0, limit: int = 100) -> List[Series]:
        """Get all series with pagination."""
        query = (
            select(Series)
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_series_count(self) -> int:
        """Get total count of series."""
        query = select(func.count(Series.id))
        result = await self.db.execute(query)
        return result.scalar()

    async def search_series(
        self, 
        query_str: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Series]:
        """Search series by title, author, or artist."""
        search_filter = or_(
            Series.title.ilike(f"%{query_str}%"),
            Series.author.ilike(f"%{query_str}%"),
            Series.artist.ilike(f"%{query_str}%")
        )
        
        query = (
            select(Series)
            .where(search_filter)
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_series_count(self, query_str: str) -> int:
        """Get count of series matching search query."""
        search_filter = or_(
            Series.title.ilike(f"%{query_str}%"),
            Series.author.ilike(f"%{query_str}%"),
            Series.artist.ilike(f"%{query_str}%")
        )
        query = select(func.count(Series.id)).where(search_filter)
        result = await self.db.execute(query)
        return result.scalar()

    async def get_series_by_status(
        self, 
        status: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Series]:
        """Get series by status."""
        query = (
            select(Series)
            .where(Series.status == status)
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_series_by_status_count(self, status: str) -> int:
        """Get count of series by status."""
        query = select(func.count(Series.id)).where(Series.status == status)
        result = await self.db.execute(query)
        return result.scalar()

    async def get_series_by_author(
        self, 
        author: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Series]:
        """Get series by author."""
        query = (
            select(Series)
            .where(Series.author.ilike(f"%{author}%"))
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_series(self, series_id: int, series_data: SeriesUpdate) -> Optional[Series]:
        """Update series information using partial updates."""
        # Get current series first
        existing_series = await self.get_series_by_id(series_id)
        if not existing_series:
            return None

        # Get only the fields that are actually set in the update data
        update_dict = series_data.model_dump(exclude_unset=True)
        if not update_dict:
            return existing_series

        try:
            # Use SQLAlchemy update statement for efficiency
            query = (
                update(Series)
                .where(Series.id == series_id)
                .values(**update_dict)
                .returning(Series)
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            updated_series = result.scalar_one_or_none()
            
            if updated_series:
                await self.db.refresh(updated_series)
            
            return updated_series
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Series update failed with integrity error: {str(e)}")
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()
            if 'duplicate' in error_msg or 'unique' in error_msg:
                raise ValueError("Series with this title already exists")
            else:
                raise ValueError("Series update failed due to data constraints")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error during series update: {str(e)}")
            raise ValueError("Series update failed due to database error")

    async def delete_series(self, series_id: int) -> bool:
        """Delete a series and all related data."""
        try:
            query = delete(Series).where(Series.id == series_id)
            result = await self.db.execute(query)
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error during series deletion: {str(e)}")
            raise ValueError("Series deletion failed due to database error")

    async def is_title_taken(self, title: str, exclude_id: Optional[int] = None) -> bool:
        """Check if a title is already taken by another series."""
        query = select(func.count(Series.id)).where(Series.title == title)
        if exclude_id:
            query = query.where(Series.id != exclude_id)
        
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0

    async def get_recent_series(self, limit: int = 10) -> List[Series]:
        """Get recently created series."""
        query = (
            select(Series)
            .order_by(desc(Series.created_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_updated_series(self, limit: int = 10) -> List[Series]:
        """Get recently updated series."""
        query = (
            select(Series)
            .order_by(desc(Series.updated_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def bulk_update_series(
        self, 
        series_ids: List[int], 
        update_data: Dict[str, Any]
    ) -> List[Series]:
        """Update multiple series with the same data."""
        try:
            query = (
                update(Series)
                .where(Series.id.in_(series_ids))
                .values(**update_data)
                .returning(Series)
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            updated_series = result.scalars().all()
            
            # Refresh all updated series
            for series in updated_series:
                await self.db.refresh(series)
            
            return updated_series
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Bulk series update failed with integrity error: {str(e)}")
            raise ValueError("Bulk update failed due to data constraints")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error during bulk series update: {str(e)}")
            raise ValueError("Bulk update failed due to database error")