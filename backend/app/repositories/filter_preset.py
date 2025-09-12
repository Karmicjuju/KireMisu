"""Repository for filter preset database operations."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.filter_preset import FilterPreset
from app.schemas.filters import FilterPresetCreate, FilterPresetUpdate


class FilterPresetRepository:
    """Repository class for filter preset database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_preset(self, preset_data: FilterPresetCreate, user_id: str) -> FilterPreset:
        """Create a new filter preset."""
        # Convert Pydantic models to dict for JSON storage
        filters_dict = preset_data.filters.model_dump(exclude_unset=True, exclude_none=True)
        sorting_dict = None
        if preset_data.sorting:
            sorting_dict = preset_data.sorting.model_dump(exclude_unset=True, exclude_none=True)

        db_preset = FilterPreset(
            name=preset_data.name,
            description=preset_data.description,
            user_id=user_id,
            filters_json=filters_dict,
            sorting_json=sorting_dict,
            is_public=preset_data.is_public,
        )
        
        self.db.add(db_preset)
        await self.db.commit()
        await self.db.refresh(db_preset)
        return db_preset

    async def get_preset_by_id(self, preset_id: int) -> Optional[FilterPreset]:
        """Get filter preset by ID."""
        result = await self.db.execute(
            select(FilterPreset).where(FilterPreset.id == preset_id)
        )
        return result.scalar_one_or_none()

    async def get_user_presets(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50,
        include_public: bool = True
    ) -> List[FilterPreset]:
        """Get filter presets for a user with optional public presets."""
        query = select(FilterPreset)
        
        if include_public:
            query = query.where(
                or_(
                    FilterPreset.user_id == user_id,
                    FilterPreset.is_public == True
                )
            )
        else:
            query = query.where(FilterPreset.user_id == user_id)
        
        query = query.order_by(FilterPreset.name).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_presets_count(self, user_id: str, include_public: bool = True) -> int:
        """Get count of filter presets for a user."""
        query = select(func.count(FilterPreset.id))
        
        if include_public:
            query = query.where(
                or_(
                    FilterPreset.user_id == user_id,
                    FilterPreset.is_public == True
                )
            )
        else:
            query = query.where(FilterPreset.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar()

    async def update_preset(
        self, 
        preset_id: int, 
        preset_data: FilterPresetUpdate,
        user_id: str
    ) -> Optional[FilterPreset]:
        """Update filter preset (only by owner)."""
        # First get the preset to ensure it exists and user owns it
        preset = await self.get_preset_by_id(preset_id)
        if not preset or preset.user_id != user_id:
            return None

        # Update fields
        update_dict = preset_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if 'filters' in update_dict:
            preset.filters_json = update_dict['filters'].model_dump(exclude_unset=True, exclude_none=True)
            del update_dict['filters']
        
        if 'sorting' in update_dict:
            if update_dict['sorting']:
                preset.sorting_json = update_dict['sorting'].model_dump(exclude_unset=True, exclude_none=True)
            else:
                preset.sorting_json = None
            del update_dict['sorting']
        
        # Update other fields
        for field, value in update_dict.items():
            if hasattr(preset, field):
                setattr(preset, field, value)

        await self.db.commit()
        await self.db.refresh(preset)
        return preset

    async def delete_preset(self, preset_id: int, user_id: str) -> bool:
        """Delete filter preset (only by owner)."""
        preset = await self.get_preset_by_id(preset_id)
        if not preset or preset.user_id != user_id:
            return False

        await self.db.delete(preset)
        await self.db.commit()
        return True

    async def get_public_presets(self, skip: int = 0, limit: int = 50) -> List[FilterPreset]:
        """Get public filter presets."""
        result = await self.db.execute(
            select(FilterPreset)
            .where(FilterPreset.is_public == True)
            .order_by(FilterPreset.name)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_public_presets_count(self) -> int:
        """Get count of public filter presets."""
        result = await self.db.execute(
            select(func.count(FilterPreset.id))
            .where(FilterPreset.is_public == True)
        )
        return result.scalar()

    async def preset_name_exists(self, name: str, user_id: str, exclude_id: Optional[int] = None) -> bool:
        """Check if a preset name already exists for a user."""
        query = select(FilterPreset.id).where(
            and_(
                FilterPreset.name == name,
                FilterPreset.user_id == user_id
            )
        )
        
        if exclude_id:
            query = query.where(FilterPreset.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def search_presets(
        self, 
        query: str, 
        user_id: str, 
        include_public: bool = True,
        skip: int = 0, 
        limit: int = 50
    ) -> List[FilterPreset]:
        """Search filter presets by name or description."""
        search_query = select(FilterPreset)
        
        # User's presets and public presets
        user_filter = FilterPreset.user_id == user_id
        if include_public:
            user_filter = or_(user_filter, FilterPreset.is_public == True)
        
        # Text search in name and description
        text_filter = or_(
            FilterPreset.name.ilike(f"%{query}%"),
            FilterPreset.description.ilike(f"%{query}%")
        )
        
        search_query = search_query.where(
            and_(user_filter, text_filter)
        ).order_by(FilterPreset.name).offset(skip).limit(limit)
        
        result = await self.db.execute(search_query)
        return result.scalars().all()