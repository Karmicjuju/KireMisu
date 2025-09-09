from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chapter import ChapterRepository
from app.services.metadata_history import MetadataHistoryService
from app.models.chapter import Chapter
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterListResponse,
    BulkChapterUpdate,
)


class ChapterService:
    """Service for managing chapter operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ChapterRepository(db)
        self.history_service = MetadataHistoryService(db)

    async def create_chapter(
        self, chapter_data: ChapterCreate, user_id: Optional[int] = None
    ) -> Chapter:
        """Create a new chapter with history tracking."""
        # Check if chapter with same series_id and number already exists
        existing = await self.repository.get_by_series_and_number(
            chapter_data.series_id, chapter_data.number
        )
        if existing:
            raise ValueError(
                f"Chapter {chapter_data.number} already exists for series {chapter_data.series_id}"
            )

        # Create the chapter
        chapter_dict = chapter_data.model_dump()
        chapter = await self.repository.create(chapter_dict)
        
        # Record creation in history
        await self.history_service.record_change(
            entity_type="chapter",
            entity_id=chapter.id,
            user_id=user_id,
            action="create",
            new_data=chapter_dict,
            description=f"Created chapter {chapter_data.number}",
        )

        return chapter

    async def get_chapter_by_id(
        self, chapter_id: int, include_series: bool = False
    ) -> Optional[Chapter]:
        """Get a chapter by ID."""
        if include_series:
            return await self.repository.get_by_id_with_series(chapter_id)
        return await self.repository.get_by_id(chapter_id)

    async def get_chapters_by_series(
        self, 
        series_id: int, 
        limit: int = 50, 
        offset: int = 0,
        order_by_number: bool = True
    ) -> List[Chapter]:
        """Get all chapters for a series."""
        return await self.repository.get_by_series(
            series_id=series_id,
            limit=limit,
            offset=offset,
            order_by_number=order_by_number,
        )

    async def get_chapters_paginated(
        self,
        page: int = 1,
        size: int = 20,
        series_id: Optional[int] = None,
        volume: Optional[Decimal] = None,
        read_status: Optional[bool] = None,
    ) -> ChapterListResponse:
        """Get paginated chapters with filtering."""
        if page < 1:
            raise ValueError("Page must be >= 1")
        if size < 1 or size > 100:
            raise ValueError("Size must be between 1 and 100")

        chapters, total = await self.repository.get_paginated(
            page=page,
            size=size,
            series_id=series_id,
            volume=volume,
            read_status=read_status,
        )

        pages = (total + size - 1) // size  # Ceiling division

        return ChapterListResponse(
            items=chapters,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def update_chapter(
        self,
        chapter_id: int,
        update_data: ChapterUpdate,
        user_id: Optional[int] = None,
        preview_mode: bool = False,
    ) -> Optional[Chapter]:
        """Update a chapter with history tracking."""
        existing_chapter = await self.repository.get_by_id(chapter_id)
        if not existing_chapter:
            return None

        # Get current data for history tracking
        current_data = {
            "number": float(existing_chapter.number) if existing_chapter.number else None,
            "title": existing_chapter.title,
            "volume": float(existing_chapter.volume) if existing_chapter.volume else None,
            "description": existing_chapter.description,
            "release_date": existing_chapter.release_date.isoformat() if existing_chapter.release_date else None,
            "page_count": existing_chapter.page_count,
            "file_size": existing_chapter.file_size,
            "read_status": existing_chapter.read_status,
            "metadata_json": existing_chapter.metadata_json,
        }

        # Prepare update data (excluding unset fields)
        update_dict = update_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            return existing_chapter

        # Preview mode - return preview without saving
        if preview_mode:
            preview = await self.history_service.create_diff_preview(
                current_data, update_dict
            )
            return {"preview": preview, "current": existing_chapter}

        # Check for conflicts (e.g., duplicate chapter number in same series)
        if "number" in update_dict:
            conflict = await self.repository.get_by_series_and_number(
                existing_chapter.series_id, Decimal(str(update_dict["number"]))
            )
            if conflict and conflict.id != chapter_id:
                raise ValueError(
                    f"Chapter {update_dict['number']} already exists for this series"
                )

        # Update the chapter
        updated_chapter = await self.repository.update(chapter_id, update_dict)
        if not updated_chapter:
            return None

        # Record change in history
        new_data = {**current_data, **update_dict}
        await self.history_service.record_change(
            entity_type="chapter",
            entity_id=chapter_id,
            user_id=user_id,
            action="update",
            previous_data=current_data,
            new_data=new_data,
            description=f"Updated chapter {updated_chapter.number}",
        )

        return updated_chapter

    async def bulk_update_chapters(
        self,
        bulk_data: BulkChapterUpdate,
        user_id: Optional[int] = None,
    ) -> List[Chapter]:
        """Update multiple chapters with the same data."""
        # Validate that all chapters exist
        existing_chapters = []
        for chapter_id in bulk_data.chapter_ids:
            chapter = await self.repository.get_by_id(chapter_id)
            if not chapter:
                raise ValueError(f"Chapter with ID {chapter_id} not found")
            existing_chapters.append(chapter)

        update_dict = bulk_data.updates.model_dump(exclude_unset=True)
        if not update_dict:
            return existing_chapters

        # Check for number conflicts if updating chapter numbers
        if "number" in update_dict:
            new_number = Decimal(str(update_dict["number"]))
            for chapter in existing_chapters:
                conflict = await self.repository.get_by_series_and_number(
                    chapter.series_id, new_number
                )
                if conflict and conflict.id != chapter.id:
                    raise ValueError(
                        f"Chapter {new_number} already exists for series {chapter.series_id}"
                    )

        # Perform bulk update
        updated_chapters = await self.repository.bulk_update(
            bulk_data.chapter_ids, update_dict
        )

        # Record history for each updated chapter
        for chapter in updated_chapters:
            current_data = {
                "number": float(chapter.number) if chapter.number else None,
                "title": chapter.title,
                "volume": float(chapter.volume) if chapter.volume else None,
                "description": chapter.description,
                "release_date": chapter.release_date.isoformat() if chapter.release_date else None,
                "page_count": chapter.page_count,
                "file_size": chapter.file_size,
                "read_status": chapter.read_status,
                "metadata_json": chapter.metadata_json,
            }
            
            new_data = {**current_data, **update_dict}
            
            await self.history_service.record_change(
                entity_type="chapter",
                entity_id=chapter.id,
                user_id=user_id,
                action="bulk_update",
                previous_data=current_data,
                new_data=new_data,
                description=f"Bulk update applied to chapter {chapter.number}",
            )

        return updated_chapters

    async def delete_chapter(
        self, chapter_id: int, user_id: Optional[int] = None
    ) -> bool:
        """Delete a chapter with history tracking."""
        chapter = await self.repository.get_by_id(chapter_id)
        if not chapter:
            return False

        # Record deletion in history before deleting
        current_data = {
            "number": float(chapter.number) if chapter.number else None,
            "title": chapter.title,
            "volume": float(chapter.volume) if chapter.volume else None,
            "description": chapter.description,
            "release_date": chapter.release_date.isoformat() if chapter.release_date else None,
            "page_count": chapter.page_count,
            "file_size": chapter.file_size,
            "read_status": chapter.read_status,
            "metadata_json": chapter.metadata_json,
        }

        await self.history_service.record_change(
            entity_type="chapter",
            entity_id=chapter_id,
            user_id=user_id,
            action="delete",
            previous_data=current_data,
            description=f"Deleted chapter {chapter.number}",
        )

        return await self.repository.delete(chapter_id)

    async def get_chapter_history(
        self, chapter_id: int, limit: int = 50, offset: int = 0
    ):
        """Get change history for a chapter."""
        return await self.history_service.get_entity_history(
            entity_type="chapter",
            entity_id=chapter_id,
            limit=limit,
            offset=offset,
        )

    async def restore_chapter_from_history(
        self, chapter_id: int, history_id: int, user_id: Optional[int] = None
    ) -> Optional[Chapter]:
        """Restore a chapter to a previous state from history."""
        restore_data = await self.history_service.get_restore_data(history_id)
        if not restore_data:
            raise ValueError(f"History entry {history_id} not found")

        # Convert restore data to update format
        update_data = ChapterUpdate(**restore_data)
        
        return await self.update_chapter(
            chapter_id=chapter_id,
            update_data=update_data,
            user_id=user_id,
            preview_mode=False,
        )

    async def get_series_statistics(self, series_id: int) -> Dict[str, Any]:
        """Get statistics about chapters in a series."""
        total_chapters = await self.repository.count_by_series(series_id)
        unread_count = await self.repository.get_unread_count(series_id)
        latest_chapters = await self.repository.get_latest_by_series(series_id, 3)

        return {
            "total_chapters": total_chapters,
            "read_count": total_chapters - unread_count,
            "unread_count": unread_count,
            "latest_chapters": [
                {
                    "id": ch.id,
                    "number": float(ch.number) if ch.number else None,
                    "title": ch.title,
                    "created_at": ch.created_at,
                }
                for ch in latest_chapters
            ],
        }

    async def mark_series_chapters_read(self, series_id: int) -> int:
        """Mark all chapters in a series as read."""
        return await self.repository.mark_all_read(series_id)