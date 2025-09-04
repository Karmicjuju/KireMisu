from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, or_, func

from app.models.series import Series
from app.schemas.series import SeriesCreate, SeriesUpdate

# Setup logging for database operations
logger = logging.getLogger(__name__)


class SeriesRepository:
    """Repository layer for series data access operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_series(self, series_data: SeriesCreate) -> Series:
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
            self.db.commit()
            self.db.refresh(db_series)
            return db_series
        except IntegrityError as e:
            self.db.rollback()
            # Log the actual error for debugging but don't expose sensitive details
            logger.error(f"Series creation failed with integrity error: {str(e)}")
            # Check for common integrity violations and provide safe error messages
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()
            if 'duplicate' in error_msg or 'unique' in error_msg:
                raise ValueError("Series with this title already exists")
            elif 'foreign key' in error_msg:
                raise ValueError("Invalid reference to related data")
            else:
                raise ValueError("Series creation failed due to data constraints")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during series creation: {str(e)}")
            raise ValueError("Series creation failed due to database error")

    def get_series_by_id(self, series_id: int) -> Optional[Series]:
        """Get series by ID."""
        return self.db.query(Series).filter(Series.id == series_id).first()

    def get_all_series(self, skip: int = 0, limit: int = 100) -> List[Series]:
        """Get all series with pagination."""
        return (
            self.db.query(Series)
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_series_count(self) -> int:
        """Get total count of series."""
        return self.db.query(func.count(Series.id)).scalar()

    def search_series(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Series]:
        """Search series by title, author, or artist."""
        search_filter = or_(
            Series.title.ilike(f"%{query}%"),
            Series.author.ilike(f"%{query}%"),
            Series.artist.ilike(f"%{query}%")
        )
        
        return (
            self.db.query(Series)
            .filter(search_filter)
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_series_count(self, query: str) -> int:
        """Get count of series matching search query."""
        search_filter = or_(
            Series.title.ilike(f"%{query}%"),
            Series.author.ilike(f"%{query}%"),
            Series.artist.ilike(f"%{query}%")
        )
        return self.db.query(func.count(Series.id)).filter(search_filter).scalar()

    def get_series_by_status(
        self, 
        status: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Series]:
        """Get series by status."""
        return (
            self.db.query(Series)
            .filter(Series.status == status)
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_series_by_status_count(self, status: str) -> int:
        """Get count of series by status."""
        return self.db.query(func.count(Series.id)).filter(Series.status == status).scalar()

    def get_series_by_author(
        self, 
        author: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Series]:
        """Get series by author."""
        return (
            self.db.query(Series)
            .filter(Series.author.ilike(f"%{author}%"))
            .order_by(desc(Series.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_series(self, series_id: int, series_data: SeriesUpdate) -> Optional[Series]:
        """Update series information."""
        db_series = self.get_series_by_id(series_id)
        if not db_series:
            return None

        update_data = series_data.model_dump(exclude_unset=True)

        try:
            for field, value in update_data.items():
                setattr(db_series, field, value)

            self.db.commit()
            self.db.refresh(db_series)
            return db_series
        except IntegrityError as e:
            self.db.rollback()
            # Log the actual error for debugging but don't expose sensitive details
            logger.error(f"Series update failed with integrity error: {str(e)}")
            # Check for common integrity violations and provide safe error messages
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()
            if 'duplicate' in error_msg or 'unique' in error_msg:
                raise ValueError("Series with this title already exists")
            elif 'foreign key' in error_msg:
                raise ValueError("Invalid reference to related data")
            else:
                raise ValueError("Series update failed due to data constraints")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during series update: {str(e)}")
            raise ValueError("Series update failed due to database error")

    def delete_series(self, series_id: int) -> bool:
        """Delete series by ID."""
        db_series = self.get_series_by_id(series_id)
        if not db_series:
            return False

        try:
            self.db.delete(db_series)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Series deletion failed with integrity error: {str(e)}")
            raise ValueError("Cannot delete series: it may have associated data that must be removed first")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during series deletion: {str(e)}")
            raise ValueError("Series deletion failed due to database error")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error during series deletion: {str(e)}")
            raise ValueError("Series deletion failed due to an unexpected error")

    def is_title_taken(self, title: str, exclude_id: Optional[int] = None) -> bool:
        """Check if series title is already taken."""
        query = self.db.query(Series).filter(Series.title == title)
        if exclude_id:
            query = query.filter(Series.id != exclude_id)
        return query.first() is not None

    def get_recent_series(self, limit: int = 10) -> List[Series]:
        """Get recently created series."""
        return (
            self.db.query(Series)
            .order_by(desc(Series.created_at))
            .limit(limit)
            .all()
        )

    def get_updated_series(self, limit: int = 10) -> List[Series]:
        """Get recently updated series."""
        return (
            self.db.query(Series)
            .order_by(desc(Series.updated_at))
            .limit(limit)
            .all()
        )