from typing import List, Optional, Dict, Any, Tuple
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, or_, and_, func, update, delete, asc, cast, String, text
from sqlalchemy.future import select

from app.models.series import Series
from app.schemas.series import SeriesCreate, SeriesUpdate
from app.schemas.filters import (
    SeriesFilterParams, SeriesSortParams, SortField, SortDirection, 
    FilterLogic, SeriesStatus, ReadStatus
)

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

    async def get_filtered_series(
        self,
        filters: Optional[SeriesFilterParams] = None,
        sorting: Optional[SeriesSortParams] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Series], int]:
        """Get filtered and sorted series with count."""
        query = select(Series)
        count_query = select(func.count(Series.id))
        
        # Apply filters
        if filters:
            filter_conditions = self._build_filter_conditions(filters)
            if filter_conditions is not None:
                query = query.where(filter_conditions)
                count_query = count_query.where(filter_conditions)
        
        # Apply sorting
        if sorting and sorting.sort_by:
            order_clauses = self._build_sort_clauses(sorting.sort_by)
            query = query.order_by(*order_clauses)
        else:
            # Default sort by created_at desc
            query = query.order_by(desc(Series.created_at))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute queries
        result = await self.db.execute(query)
        series_list = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        return series_list, total_count

    def _build_filter_conditions(self, filters: SeriesFilterParams):
        """Build SQLAlchemy filter conditions from filter parameters."""
        conditions = []
        
        # Text search
        if filters.search:
            search_condition = or_(
                Series.title.ilike(f"%{filters.search}%"),
                Series.author.ilike(f"%{filters.search}%"),
                Series.artist.ilike(f"%{filters.search}%"),
                Series.description.ilike(f"%{filters.search}%")
            )
            conditions.append(search_condition)
        
        # Status filters
        if filters.status:
            status_conditions = [Series.status == status.value for status in filters.status]
            if len(status_conditions) == 1:
                conditions.append(status_conditions[0])
            else:
                conditions.append(or_(*status_conditions))
        
        # Author filter
        if filters.author:
            conditions.append(Series.author.ilike(f"%{filters.author}%"))
        
        # Artist filter
        if filters.artist:
            conditions.append(Series.artist.ilike(f"%{filters.artist}%"))
        
        # Genre filters (using JSONB metadata)
        if filters.genres:
            genre_conditions = []
            for genre in filters.genres:
                genre_conditions.append(
                    Series.metadata_json["genres"].astext.op("@>")([genre])
                )
            if genre_conditions:
                if len(genre_conditions) == 1:
                    conditions.append(genre_conditions[0])
                else:
                    # For multiple genres, use OR logic by default
                    conditions.append(or_(*genre_conditions))
        
        # Tag filters (using JSONB metadata)
        if filters.tags:
            tag_conditions = []
            for tag in filters.tags:
                tag_conditions.append(
                    Series.metadata_json["tags"].astext.op("@>")([tag])
                )
            if tag_conditions:
                if len(tag_conditions) == 1:
                    conditions.append(tag_conditions[0])
                else:
                    # For multiple tags, use OR logic by default
                    conditions.append(or_(*tag_conditions))
        
        # Date range filters
        if filters.created_date_range:
            if filters.created_date_range.start_date:
                conditions.append(Series.created_at >= filters.created_date_range.start_date)
            if filters.created_date_range.end_date:
                conditions.append(Series.created_at <= filters.created_date_range.end_date)
        
        if filters.updated_date_range:
            if filters.updated_date_range.start_date:
                conditions.append(Series.updated_at >= filters.updated_date_range.start_date)
            if filters.updated_date_range.end_date:
                conditions.append(Series.updated_at <= filters.updated_date_range.end_date)
        
        # Rating filters (using JSONB metadata)
        if filters.rating_filter:
            if filters.rating_filter.min_rating is not None:
                conditions.append(
                    cast(Series.metadata_json["rating"], String).cast(func.numeric) >= filters.rating_filter.min_rating
                )
            if filters.rating_filter.max_rating is not None:
                conditions.append(
                    cast(Series.metadata_json["rating"], String).cast(func.numeric) <= filters.rating_filter.max_rating
                )
        
        # Read status filters (using JSONB metadata) 
        if filters.read_status:
            read_status_conditions = []
            for status in filters.read_status:
                read_status_conditions.append(
                    Series.metadata_json["read_status"].astext == status.value
                )
            if read_status_conditions:
                if len(read_status_conditions) == 1:
                    conditions.append(read_status_conditions[0])
                else:
                    conditions.append(or_(*read_status_conditions))
        
        # Combine conditions based on filter logic
        if not conditions:
            return None
        
        if len(conditions) == 1:
            return conditions[0]
        
        if filters.filter_logic == FilterLogic.OR:
            return or_(*conditions)
        else:
            return and_(*conditions)

    def _build_sort_clauses(self, sort_criteria: List) -> List:
        """Build SQLAlchemy order clauses from sort criteria."""
        order_clauses = []
        
        for criteria in sort_criteria:
            field = criteria.field
            direction = criteria.direction
            
            # Map sort fields to SQLAlchemy columns
            column_mapping = {
                SortField.TITLE: Series.title,
                SortField.AUTHOR: Series.author,
                SortField.ARTIST: Series.artist,
                SortField.STATUS: Series.status,
                SortField.CREATED_AT: Series.created_at,
                SortField.UPDATED_AT: Series.updated_at,
                SortField.RATING: cast(Series.metadata_json["rating"], String).cast(func.numeric),
                SortField.LAST_READ: cast(Series.metadata_json["last_read"], String)
            }
            
            column = column_mapping.get(field)
            if column is not None:
                if direction == SortDirection.DESC:
                    order_clauses.append(desc(column))
                else:
                    order_clauses.append(asc(column))
        
        return order_clauses

    async def get_series_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options (statuses, authors, artists, genres, tags)."""
        # Get distinct values for dropdown filters
        status_query = select(Series.status).distinct().where(Series.status.is_not(None))
        author_query = select(Series.author).distinct().where(Series.author.is_not(None))
        artist_query = select(Series.artist).distinct().where(Series.artist.is_not(None))
        
        status_result = await self.db.execute(status_query)
        author_result = await self.db.execute(author_query)
        artist_result = await self.db.execute(artist_query)
        
        statuses = [row[0] for row in status_result.fetchall() if row[0]]
        authors = [row[0] for row in author_result.fetchall() if row[0]]
        artists = [row[0] for row in artist_result.fetchall() if row[0]]
        
        # Get genres and tags from JSONB metadata
        # This is a more complex query to extract distinct values from JSON arrays
        genres_query = text("""
            SELECT DISTINCT jsonb_array_elements_text(metadata_json->'genres') as genre
            FROM series 
            WHERE metadata_json ? 'genres' 
            AND jsonb_typeof(metadata_json->'genres') = 'array'
            ORDER BY genre
        """)
        
        tags_query = text("""
            SELECT DISTINCT jsonb_array_elements_text(metadata_json->'tags') as tag
            FROM series 
            WHERE metadata_json ? 'tags' 
            AND jsonb_typeof(metadata_json->'tags') = 'array'
            ORDER BY tag
        """)
        
        try:
            genres_result = await self.db.execute(genres_query)
            genres = [row[0] for row in genres_result.fetchall() if row[0]]
        except Exception as e:
            logger.warning(f"Could not fetch genres: {e}")
            genres = []
        
        try:
            tags_result = await self.db.execute(tags_query)
            tags = [row[0] for row in tags_result.fetchall() if row[0]]
        except Exception as e:
            logger.warning(f"Could not fetch tags: {e}")
            tags = []
        
        return {
            "statuses": sorted(statuses),
            "authors": sorted(authors),
            "artists": sorted(artists),
            "genres": genres,  # Already sorted in query
            "tags": tags,     # Already sorted in query
        }