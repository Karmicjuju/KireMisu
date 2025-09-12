"""Pydantic schemas for filtering and sorting functionality."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


class SortDirection(str, Enum):
    """Enumeration for sort directions."""
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    """Enumeration for sortable fields."""
    TITLE = "title"
    AUTHOR = "author"
    ARTIST = "artist"
    STATUS = "status"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    LAST_READ = "last_read"
    RATING = "rating"


class SeriesStatus(str, Enum):
    """Enumeration for series status values."""
    ONGOING = "ongoing"
    COMPLETED = "completed"
    HIATUS = "hiatus"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ReadStatus(str, Enum):
    """Enumeration for read status values."""
    UNREAD = "unread"
    READING = "reading"
    COMPLETED = "completed"
    DROPPED = "dropped"
    PLAN_TO_READ = "plan_to_read"


class FilterLogic(str, Enum):
    """Enumeration for filter combination logic."""
    AND = "and"
    OR = "or"


class SortCriteria(BaseModel):
    """Schema for sorting criteria."""
    field: SortField = Field(..., description="Field to sort by")
    direction: SortDirection = Field(SortDirection.ASC, description="Sort direction")
    
    class Config:
        use_enum_values = True


class DateRangeFilter(BaseModel):
    """Schema for date range filtering."""
    start_date: Optional[datetime] = Field(None, description="Start date (inclusive)")
    end_date: Optional[datetime] = Field(None, description="End date (inclusive)")
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date is after start_date."""
        if v and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError("End date must be after start date")
        return v


class RatingFilter(BaseModel):
    """Schema for rating filtering."""
    min_rating: Optional[float] = Field(None, ge=0.0, le=10.0, description="Minimum rating")
    max_rating: Optional[float] = Field(None, ge=0.0, le=10.0, description="Maximum rating")
    
    @field_validator('max_rating')
    @classmethod
    def validate_rating_range(cls, v, info):
        """Ensure max_rating is greater than min_rating."""
        if v and info.data.get('min_rating') and v < info.data['min_rating']:
            raise ValueError("Maximum rating must be greater than minimum rating")
        return v


class SeriesFilterParams(BaseModel):
    """Schema for series filtering parameters."""
    
    # Text search
    search: Optional[str] = Field(None, max_length=200, description="Search query for title, author, or artist")
    
    # Status filters
    status: Optional[List[SeriesStatus]] = Field(None, description="Filter by series status")
    read_status: Optional[List[ReadStatus]] = Field(None, description="Filter by read status")
    
    # Text field filters
    author: Optional[str] = Field(None, max_length=255, description="Filter by author")
    artist: Optional[str] = Field(None, max_length=255, description="Filter by artist")
    
    # Genre/tag filters (using JSONB metadata)
    genres: Optional[List[str]] = Field(None, description="Filter by genres")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    
    # Date range filters
    created_date_range: Optional[DateRangeFilter] = Field(None, description="Filter by creation date range")
    updated_date_range: Optional[DateRangeFilter] = Field(None, description="Filter by update date range")
    last_read_date_range: Optional[DateRangeFilter] = Field(None, description="Filter by last read date range")
    
    # Rating filter
    rating_filter: Optional[RatingFilter] = Field(None, description="Filter by rating range")
    
    # Filter combination logic
    filter_logic: FilterLogic = Field(FilterLogic.AND, description="Logic for combining filters (AND/OR)")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, v):
        """Validate and sanitize search query."""
        if v is not None:
            sanitized = v.strip()
            if not sanitized:
                return None
            if len(sanitized) < 1:
                raise ValueError("Search query too short")
            return sanitized
        return v
    
    @field_validator('genres', 'tags')
    @classmethod
    def validate_string_lists(cls, v):
        """Validate genre and tag lists."""
        if v is not None:
            # Remove empty strings and duplicates
            cleaned = list(set(tag.strip() for tag in v if tag and tag.strip()))
            return cleaned if cleaned else None
        return v
    
    class Config:
        use_enum_values = True


class SeriesSortParams(BaseModel):
    """Schema for series sorting parameters."""
    
    sort_by: List[SortCriteria] = Field(
        default=[SortCriteria(field=SortField.TITLE, direction=SortDirection.ASC)],
        description="List of sort criteria (in order of priority)",
        max_items=3
    )
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_criteria(cls, v):
        """Validate sort criteria list."""
        if not v:
            return [SortCriteria(field=SortField.TITLE, direction=SortDirection.ASC)]
        
        # Check for duplicate fields
        fields = [criteria.field for criteria in v]
        if len(fields) != len(set(fields)):
            raise ValueError("Cannot sort by the same field multiple times")
        
        return v
    
    class Config:
        use_enum_values = True


class FilterPresetCreate(BaseModel):
    """Schema for creating filter presets."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Preset name")
    description: Optional[str] = Field(None, max_length=500, description="Preset description")
    filters: SeriesFilterParams = Field(..., description="Filter parameters")
    sorting: Optional[SeriesSortParams] = Field(None, description="Sort parameters")
    is_public: bool = Field(False, description="Whether preset is public")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate preset name."""
        name = v.strip()
        if not name:
            raise ValueError("Preset name cannot be empty")
        if len(name) < 1:
            raise ValueError("Preset name too short")
        return name
    
    class Config:
        use_enum_values = True


class FilterPresetUpdate(BaseModel):
    """Schema for updating filter presets."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Preset name")
    description: Optional[str] = Field(None, max_length=500, description="Preset description")
    filters: Optional[SeriesFilterParams] = Field(None, description="Filter parameters")
    sorting: Optional[SeriesSortParams] = Field(None, description="Sort parameters")
    is_public: Optional[bool] = Field(None, description="Whether preset is public")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate preset name."""
        if v is not None:
            name = v.strip()
            if not name:
                raise ValueError("Preset name cannot be empty")
            if len(name) < 1:
                raise ValueError("Preset name too short")
            return name
        return v
    
    class Config:
        use_enum_values = True


class FilterPresetResponse(BaseModel):
    """Schema for filter preset responses."""
    
    id: int
    name: str
    description: Optional[str] = None
    filters: Dict[str, Any]  # SeriesFilterParams as dict
    sorting: Optional[Dict[str, Any]] = None  # SeriesSortParams as dict
    is_public: bool
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FilterPresetListResponse(BaseModel):
    """Schema for paginated filter preset list responses."""
    
    items: List[FilterPresetResponse]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        from_attributes = True


class SeriesFilterRequest(BaseModel):
    """Schema for comprehensive series filtering and sorting request."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    # Filtering
    filters: Optional[SeriesFilterParams] = Field(None, description="Filter parameters")
    
    # Sorting
    sorting: Optional[SeriesSortParams] = Field(None, description="Sort parameters")
    
    # Preset usage
    preset_id: Optional[int] = Field(None, description="Use saved filter preset")
    
    class Config:
        use_enum_values = True


class SeriesFilterResponse(BaseModel):
    """Schema for filtered series response."""
    
    items: List[Dict[str, Any]]  # SeriesResponse items
    total: int
    page: int
    size: int
    pages: int
    applied_filters: Dict[str, Any]  # Applied filter parameters
    applied_sorting: Dict[str, Any]  # Applied sort parameters
    
    class Config:
        from_attributes = True