"""Service layer for filter preset management and business logic."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil

from app.models.filter_preset import FilterPreset
from app.repositories.filter_preset import FilterPresetRepository
from app.schemas.filters import (
    FilterPresetCreate, 
    FilterPresetUpdate, 
    FilterPresetResponse, 
    FilterPresetListResponse,
    SeriesFilterParams,
    SeriesSortParams
)


class FilterPresetService:
    """Service layer for filter preset management and business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.preset_repo = FilterPresetRepository(db)

    async def create_preset(
        self, 
        preset_data: FilterPresetCreate, 
        user_id: str
    ) -> FilterPreset:
        """Create a new filter preset with validation."""
        # Check if preset name already exists for user
        if await self.preset_repo.preset_name_exists(preset_data.name, user_id):
            raise ValueError(f"Preset with name '{preset_data.name}' already exists")
        
        # Validate filter parameters
        if not preset_data.filters:
            raise ValueError("Filter parameters are required")
        
        return await self.preset_repo.create_preset(preset_data, user_id)

    async def get_preset_by_id(self, preset_id: int, user_id: str) -> Optional[FilterPreset]:
        """Get filter preset by ID (only accessible by owner or if public)."""
        preset = await self.preset_repo.get_preset_by_id(preset_id)
        if not preset:
            return None
        
        # Check access permissions
        if preset.user_id != user_id and not preset.is_public:
            return None
        
        return preset

    async def get_user_presets_paginated(
        self, 
        user_id: str,
        page: int = 1, 
        size: int = 20,
        include_public: bool = True
    ) -> FilterPresetListResponse:
        """Get paginated list of user's filter presets."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        presets_list = await self.preset_repo.get_user_presets(
            user_id=user_id, 
            skip=skip, 
            limit=size,
            include_public=include_public
        )
        total_count = await self.preset_repo.get_user_presets_count(
            user_id=user_id,
            include_public=include_public
        )
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        preset_responses = [self._convert_to_response(preset) for preset in presets_list]

        return FilterPresetListResponse(
            items=preset_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    async def update_preset(
        self,
        preset_id: int,
        preset_data: FilterPresetUpdate,
        user_id: str,
    ) -> Optional[FilterPreset]:
        """Update filter preset (only by owner)."""
        # Check if new name already exists (if being changed)
        if preset_data.name:
            existing = await self.preset_repo.get_preset_by_id(preset_id)
            if existing and existing.name != preset_data.name:
                if await self.preset_repo.preset_name_exists(preset_data.name, user_id, exclude_id=preset_id):
                    raise ValueError(f"Preset with name '{preset_data.name}' already exists")
        
        return await self.preset_repo.update_preset(preset_id, preset_data, user_id)

    async def delete_preset(self, preset_id: int, user_id: str) -> bool:
        """Delete filter preset (only by owner)."""
        return await self.preset_repo.delete_preset(preset_id, user_id)

    async def get_public_presets_paginated(
        self, 
        page: int = 1, 
        size: int = 20
    ) -> FilterPresetListResponse:
        """Get paginated list of public filter presets."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        presets_list = await self.preset_repo.get_public_presets(skip=skip, limit=size)
        total_count = await self.preset_repo.get_public_presets_count()
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        preset_responses = [self._convert_to_response(preset) for preset in presets_list]

        return FilterPresetListResponse(
            items=preset_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    async def search_presets_paginated(
        self,
        query: str,
        user_id: str,
        page: int = 1,
        size: int = 20,
        include_public: bool = True
    ) -> FilterPresetListResponse:
        """Search filter presets with pagination."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        presets_list = await self.preset_repo.search_presets(
            query=query,
            user_id=user_id,
            include_public=include_public,
            skip=skip,
            limit=size
        )
        
        # For search count, we need to implement a search count method
        # For now, we'll use the current results count as an approximation
        total_count = len(presets_list)  # This is imperfect but functional
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        preset_responses = [self._convert_to_response(preset) for preset in presets_list]

        return FilterPresetListResponse(
            items=preset_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    async def get_preset_filters_and_sorting(
        self, 
        preset_id: int, 
        user_id: str
    ) -> tuple[Optional[SeriesFilterParams], Optional[SeriesSortParams]]:
        """Get filter and sorting parameters from a preset."""
        preset = await self.get_preset_by_id(preset_id, user_id)
        if not preset:
            return None, None
        
        # Convert JSON back to Pydantic models
        try:
            filters = SeriesFilterParams(**preset.filters_json) if preset.filters_json else None
            sorting = SeriesSortParams(**preset.sorting_json) if preset.sorting_json else None
            return filters, sorting
        except Exception as e:
            # Log the error and return None values
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error parsing preset {preset_id} parameters: {e}")
            return None, None

    def _convert_to_response(self, preset: FilterPreset) -> FilterPresetResponse:
        """Convert FilterPreset model to response schema."""
        return FilterPresetResponse(
            id=preset.id,
            name=preset.name,
            description=preset.description,
            filters=preset.filters_json,
            sorting=preset.sorting_json,
            is_public=preset.is_public,
            user_id=preset.user_id,
            created_at=preset.created_at,
            updated_at=preset.updated_at
        )