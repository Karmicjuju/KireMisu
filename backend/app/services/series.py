from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil

from app.models.series import Series
from app.repositories.series_async import AsyncSeriesRepository
from app.services.metadata_history import MetadataHistoryService
from app.services.filter_preset import FilterPresetService
from app.schemas.series import SeriesCreate, SeriesUpdate, SeriesListResponse, SeriesResponse
from app.schemas.filters import (
    SeriesFilterParams, SeriesSortParams, SeriesFilterResponse
)


class SeriesService:
    """Service layer for series management and business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.series_repo = AsyncSeriesRepository(db)
        self.history_service = MetadataHistoryService(db)
        self.preset_service = FilterPresetService(db)

    async def create_series(
        self, series_data: SeriesCreate, user_id: Optional[str] = None
    ) -> Series:
        """Create a new series with validation and history tracking."""
        # Check if title already exists
        if await self.series_repo.is_title_taken(series_data.title):
            raise ValueError(f"Series with title '{series_data.title}' already exists")
        
        series = await self.series_repo.create_series(series_data)
        
        # Record creation in history
        series_dict = {
            "title": series.title,
            "description": series.description,
            "author": series.author,
            "artist": series.artist,
            "status": series.status,
            "cover_path": series.cover_path,
            "metadata_json": series.metadata_json,
        }
        
        await self.history_service.record_change(
            entity_type="series",
            entity_id=series.id,
            user_id=user_id,
            action="create",
            new_data=series_dict,
            description=f"Created series '{series.title}'",
        )
        
        return series

    async def get_series_by_id(self, series_id: int) -> Optional[Series]:
        """Get series by ID."""
        return await self.series_repo.get_series_by_id(series_id)

    async def get_all_series_paginated(
        self, 
        page: int = 1, 
        size: int = 20
    ) -> SeriesListResponse:
        """Get paginated list of all series."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        series_list = await self.series_repo.get_all_series(skip=skip, limit=size)
        total_count = await self.series_repo.get_series_count()
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        series_responses = [SeriesResponse.model_validate(series) for series in series_list]

        return SeriesListResponse(
            items=series_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    async def search_series_paginated(
        self, 
        query: str, 
        page: int = 1, 
        size: int = 20
    ) -> SeriesListResponse:
        """Search series with pagination."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        series_list = await self.series_repo.search_series(query, skip=skip, limit=size)
        total_count = await self.series_repo.search_series_count(query)
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        series_responses = [SeriesResponse.model_validate(series) for series in series_list]

        return SeriesListResponse(
            items=series_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    async def get_series_by_status_paginated(
        self, 
        status: str, 
        page: int = 1, 
        size: int = 20
    ) -> SeriesListResponse:
        """Get series by status with pagination."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        series_list = await self.series_repo.get_series_by_status(status, skip=skip, limit=size)
        total_count = await self.series_repo.get_series_by_status_count(status)
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        series_responses = [SeriesResponse.model_validate(series) for series in series_list]

        return SeriesListResponse(
            items=series_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    async def update_series(
        self,
        series_id: int,
        series_data: SeriesUpdate,
        user_id: Optional[str] = None,
        preview_mode: bool = False,
    ) -> Optional[Series]:
        """Update series with validation, history tracking, and preview mode."""
        # Check if series exists
        existing_series = await self.series_repo.get_series_by_id(series_id)
        if not existing_series:
            return None

        # Get current data for history tracking
        current_data = {
            "title": existing_series.title,
            "description": existing_series.description,
            "author": existing_series.author,
            "artist": existing_series.artist,
            "status": existing_series.status,
            "cover_path": existing_series.cover_path,
            "metadata_json": existing_series.metadata_json,
        }

        # Prepare update data (excluding unset fields)
        update_dict = series_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            return existing_series

        # Preview mode - return preview without saving
        if preview_mode:
            preview = await self.history_service.create_diff_preview(
                current_data, update_dict
            )
            return {"preview": preview, "current": existing_series}

        # Check if title is being changed and already exists
        if "title" in update_dict and update_dict["title"] != existing_series.title:
            if await self.series_repo.is_title_taken(update_dict["title"], exclude_id=series_id):
                raise ValueError(f"Series with title '{update_dict['title']}' already exists")

        # Update the series
        updated_series = await self.series_repo.update_series(series_id, series_data)
        if not updated_series:
            return None

        # Record change in history
        new_data = {**current_data, **update_dict}
        await self.history_service.record_change(
            entity_type="series",
            entity_id=series_id,
            user_id=user_id,
            action="update",
            previous_data=current_data,
            new_data=new_data,
            description=f"Updated series '{updated_series.title}'",
        )

        return updated_series

    async def delete_series(self, series_id: int) -> bool:
        """Delete series by ID."""
        return await self.series_repo.delete_series(series_id)

    def get_recent_series(self, limit: int = 10) -> List[SeriesResponse]:
        """Get recently created series."""
        if limit > 50:
            limit = 50
        
        series_list = self.series_repo.get_recent_series(limit)
        return [SeriesResponse.model_validate(series) for series in series_list]

    def get_updated_series(self, limit: int = 10) -> List[SeriesResponse]:
        """Get recently updated series."""
        if limit > 50:
            limit = 50
        
        series_list = self.series_repo.get_updated_series(limit)
        return [SeriesResponse.model_validate(series) for series in series_list]

    def get_series_by_author_paginated(
        self, 
        author: str, 
        page: int = 1, 
        size: int = 20
    ) -> SeriesListResponse:
        """Get series by author with pagination."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        skip = (page - 1) * size
        series_list = self.series_repo.get_series_by_author(author, skip=skip, limit=size)
        # For author count, we can use search count as it includes author search
        total_count = self.series_repo.search_series_count(author)
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response schema
        series_responses = [SeriesResponse.model_validate(series) for series in series_list]

        return SeriesListResponse(
            items=series_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )

    def get_series_statistics(self) -> dict:
        """Get statistics about series in the database."""
        total_series = self.series_repo.get_series_count()
        
        # Get counts by status - this could be optimized with a single query
        status_counts = {}
        common_statuses = ["ongoing", "completed", "hiatus", "cancelled"]
        
        for status in common_statuses:
            count = self.series_repo.get_series_by_status_count(status)
            if count > 0:
                status_counts[status] = count

        return {
            "total_series": total_series,
            "status_counts": status_counts
        }

    async def get_series_history(
        self, series_id: int, limit: int = 50, offset: int = 0
    ):
        """Get change history for a series."""
        return await self.history_service.get_entity_history(
            entity_type="series",
            entity_id=series_id,
            limit=limit,
            offset=offset,
        )

    async def restore_series_from_history(
        self, series_id: int, history_id: int, user_id: Optional[str] = None
    ) -> Optional[Series]:
        """Restore a series to a previous state from history."""
        restore_data = await self.history_service.get_restore_data(history_id)
        if not restore_data:
            raise ValueError(f"History entry {history_id} not found")

        # Convert restore data to update format
        update_data = SeriesUpdate(**restore_data)
        
        return await self.update_series(
            series_id=series_id,
            series_data=update_data,
            user_id=user_id,
            preview_mode=False,
        )

    async def bulk_update_series(
        self,
        series_ids: List[int],
        update_data: SeriesUpdate,
        user_id: Optional[str] = None,
    ) -> List[Series]:
        """Update multiple series with the same data using atomic transaction."""
        if len(series_ids) > 100:
            raise ValueError("Cannot update more than 100 series at once")

        if len(set(series_ids)) != len(series_ids):
            raise ValueError("Series IDs must be unique")

        # Security Fix: Use atomic transaction to ensure data integrity
        async with self.db.begin() as transaction:
            try:
                updated_series = []
                update_dict = update_data.model_dump(exclude_unset=True)
                
                if not update_dict:
                    # Return existing series without changes
                    for series_id in series_ids:
                        series = await self.series_repo.get_series_by_id(series_id)
                        if series:
                            updated_series.append(series)
                    return updated_series

                # Validate that all series exist before making any changes
                existing_series = []
                for series_id in series_ids:
                    series = await self.series_repo.get_series_by_id(series_id)
                    if not series:
                        raise ValueError(f"Series with ID {series_id} not found")
                    existing_series.append(series)

                # Check for title conflicts if updating titles
                if "title" in update_dict:
                    new_title = update_dict["title"]
                    existing_with_title = await self.series_repo.get_series_by_title(new_title)
                    if existing_with_title and existing_with_title.id not in series_ids:
                        raise ValueError(f"Series with title '{new_title}' already exists")

                # Update each series individually to maintain proper history tracking
                for series_id in series_ids:
                    updated = await self.update_series(
                        series_id=series_id,
                        series_data=update_data,
                        user_id=user_id,
                        preview_mode=False,
                    )
                    if updated and not isinstance(updated, dict):  # Ensure it's not a preview
                        updated_series.append(updated)

                # Commit transaction
                await transaction.commit()
                return updated_series
                
            except Exception as e:
                # Transaction will be automatically rolled back on exception
                raise e

    async def get_filtered_and_sorted_series(
        self,
        filters: Optional[SeriesFilterParams] = None,
        sorting: Optional[SeriesSortParams] = None,
        preset_id: Optional[int] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> SeriesFilterResponse:
        """Get series with comprehensive filtering and sorting."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = 20

        # Load preset filters if specified
        preset_filters = None
        preset_sorting = None
        if preset_id and user_id:
            preset_filters, preset_sorting = await self.preset_service.get_preset_filters_and_sorting(
                preset_id, user_id
            )
        
        # Use preset filters/sorting as defaults, override with provided parameters
        final_filters = filters or preset_filters
        final_sorting = sorting or preset_sorting

        skip = (page - 1) * size
        series_list, total_count = await self.series_repo.get_filtered_series(
            filters=final_filters,
            sorting=final_sorting,
            skip=skip,
            limit=size
        )
        
        total_pages = ceil(total_count / size) if total_count > 0 else 1

        # Convert to response format
        series_responses = [SeriesResponse.model_validate(series) for series in series_list]
        series_dict_responses = [response.model_dump() for response in series_responses]

        # Prepare applied filters and sorting for response
        applied_filters = final_filters.model_dump(exclude_unset=True, exclude_none=True) if final_filters else {}
        applied_sorting = final_sorting.model_dump(exclude_unset=True, exclude_none=True) if final_sorting else {}

        return SeriesFilterResponse(
            items=series_dict_responses,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages,
            applied_filters=applied_filters,
            applied_sorting=applied_sorting
        )

    async def get_series_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options for dropdowns."""
        return await self.series_repo.get_series_filter_options()

    async def clear_all_filters(self) -> SeriesListResponse:
        """Get all series without any filters (equivalent to get_all_series_paginated)."""
        return await self.get_all_series_paginated()