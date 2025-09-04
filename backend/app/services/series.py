from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from math import ceil

from app.models.series import Series
from app.repositories.series import SeriesRepository
from app.schemas.series import SeriesCreate, SeriesUpdate, SeriesListResponse, SeriesResponse


class SeriesService:
    """Service layer for series management and business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.series_repo = SeriesRepository(db)

    def create_series(self, series_data: SeriesCreate) -> Series:
        """Create a new series with validation."""
        # Check if title already exists
        if self.series_repo.is_title_taken(series_data.title):
            raise ValueError(f"Series with title '{series_data.title}' already exists")
        
        return self.series_repo.create_series(series_data)

    def get_series_by_id(self, series_id: int) -> Optional[Series]:
        """Get series by ID."""
        return self.series_repo.get_series_by_id(series_id)

    def get_all_series_paginated(
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
        series_list = self.series_repo.get_all_series(skip=skip, limit=size)
        total_count = self.series_repo.get_series_count()
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

    def search_series_paginated(
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
        series_list = self.series_repo.search_series(query, skip=skip, limit=size)
        total_count = self.series_repo.search_series_count(query)
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

    def get_series_by_status_paginated(
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
        series_list = self.series_repo.get_series_by_status(status, skip=skip, limit=size)
        total_count = self.series_repo.get_series_by_status_count(status)
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

    def update_series(self, series_id: int, series_data: SeriesUpdate) -> Optional[Series]:
        """Update series with validation."""
        # Check if series exists
        existing_series = self.series_repo.get_series_by_id(series_id)
        if not existing_series:
            return None

        # Check if title is being changed and already exists
        if series_data.title and series_data.title != existing_series.title:
            if self.series_repo.is_title_taken(series_data.title, exclude_id=series_id):
                raise ValueError(f"Series with title '{series_data.title}' already exists")

        return self.series_repo.update_series(series_id, series_data)

    def delete_series(self, series_id: int) -> bool:
        """Delete series by ID."""
        return self.series_repo.delete_series(series_id)

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