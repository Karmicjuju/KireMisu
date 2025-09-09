from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, func, update

from app.models.chapter import Chapter
from app.models.series import Series


class ChapterRepository:
    """Repository for Chapter database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, chapter_data: Dict[str, Any]) -> Chapter:
        """Create a new chapter."""
        chapter = Chapter(**chapter_data)
        self.db.add(chapter)
        await self.db.commit()
        await self.db.refresh(chapter)
        return chapter

    async def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        """Get a chapter by ID."""
        query = select(Chapter).where(Chapter.id == chapter_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_with_series(self, chapter_id: int) -> Optional[Chapter]:
        """Get a chapter by ID with series information."""
        query = (
            select(Chapter)
            .options(selectinload(Chapter.series))
            .where(Chapter.id == chapter_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_series_and_number(
        self, series_id: int, number: Decimal
    ) -> Optional[Chapter]:
        """Get a chapter by series ID and chapter number."""
        query = select(Chapter).where(
            and_(Chapter.series_id == series_id, Chapter.number == number)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_series(
        self, 
        series_id: int, 
        limit: int = 50, 
        offset: int = 0,
        order_by_number: bool = True
    ) -> List[Chapter]:
        """Get all chapters for a series."""
        query = select(Chapter).where(Chapter.series_id == series_id)
        
        if order_by_number:
            query = query.order_by(Chapter.number.asc())
        else:
            query = query.order_by(Chapter.created_at.desc())
            
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_paginated(
        self, 
        page: int = 1, 
        size: int = 20,
        series_id: Optional[int] = None,
        volume: Optional[Decimal] = None,
        read_status: Optional[bool] = None
    ) -> tuple[List[Chapter], int]:
        """Get paginated chapters with optional filtering."""
        query = select(Chapter)
        count_query = select(func.count(Chapter.id))
        
        # Apply filters
        if series_id:
            query = query.where(Chapter.series_id == series_id)
            count_query = count_query.where(Chapter.series_id == series_id)
        
        if volume is not None:
            query = query.where(Chapter.volume == volume)
            count_query = count_query.where(Chapter.volume == volume)
            
        if read_status is not None:
            query = query.where(Chapter.read_status == read_status)
            count_query = count_query.where(Chapter.read_status == read_status)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        # Get paginated results
        query = query.order_by(Chapter.series_id.asc(), Chapter.number.asc())
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.db.execute(query)
        chapters = result.scalars().all()
        
        return chapters, total

    async def update(
        self, chapter_id: int, update_data: Dict[str, Any]
    ) -> Optional[Chapter]:
        """Update a chapter."""
        # Remove None values to avoid overwriting with nulls
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        
        if not filtered_data:
            return await self.get_by_id(chapter_id)
        
        query = (
            update(Chapter)
            .where(Chapter.id == chapter_id)
            .values(**filtered_data)
            .returning(Chapter)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        updated_chapter = result.scalar_one_or_none()
        
        if updated_chapter:
            await self.db.refresh(updated_chapter)
        
        return updated_chapter

    async def bulk_update(
        self, chapter_ids: List[int], update_data: Dict[str, Any]
    ) -> List[Chapter]:
        """Update multiple chapters with the same data."""
        # Remove None values to avoid overwriting with nulls
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        
        if not filtered_data:
            # Return existing chapters without changes
            query = select(Chapter).where(Chapter.id.in_(chapter_ids))
            result = await self.db.execute(query)
            return result.scalars().all()
        
        # Perform bulk update
        query = (
            update(Chapter)
            .where(Chapter.id.in_(chapter_ids))
            .values(**filtered_data)
            .returning(Chapter)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        updated_chapters = result.scalars().all()
        
        # Refresh all updated chapters
        for chapter in updated_chapters:
            await self.db.refresh(chapter)
        
        return updated_chapters

    async def delete(self, chapter_id: int) -> bool:
        """Delete a chapter."""
        chapter = await self.get_by_id(chapter_id)
        if not chapter:
            return False
        
        await self.db.delete(chapter)
        await self.db.commit()
        return True

    async def count_by_series(self, series_id: int) -> int:
        """Count chapters in a series."""
        query = select(func.count(Chapter.id)).where(Chapter.series_id == series_id)
        result = await self.db.execute(query)
        return result.scalar()

    async def get_latest_by_series(
        self, series_id: int, limit: int = 5
    ) -> List[Chapter]:
        """Get the latest chapters for a series."""
        query = (
            select(Chapter)
            .where(Chapter.series_id == series_id)
            .order_by(Chapter.number.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unread_count(self, series_id: Optional[int] = None) -> int:
        """Get count of unread chapters, optionally filtered by series."""
        query = select(func.count(Chapter.id)).where(Chapter.read_status == False)
        
        if series_id:
            query = query.where(Chapter.series_id == series_id)
        
        result = await self.db.execute(query)
        return result.scalar()

    async def mark_all_read(self, series_id: int) -> int:
        """Mark all chapters in a series as read."""
        query = (
            update(Chapter)
            .where(Chapter.series_id == series_id)
            .values(read_status=True)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount