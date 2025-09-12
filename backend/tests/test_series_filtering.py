"""Tests for series filtering and sorting functionality."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.series import Series
from app.models.filter_preset import FilterPreset
from app.schemas.filters import (
    SeriesFilterParams, SeriesSortParams, SortField, SortDirection,
    SeriesStatus, ReadStatus, FilterLogic, FilterPresetCreate
)
from app.services.series import SeriesService
from app.services.filter_preset import FilterPresetService


@pytest.fixture
async def sample_series_data():
    """Create sample series data for testing."""
    return [
        {
            "title": "Attack on Titan",
            "description": "Humanity fights against titans",
            "author": "Hajime Isayama",
            "artist": "Hajime Isayama",
            "status": "completed",
            "metadata_json": {
                "genres": ["Action", "Drama", "Fantasy"],
                "tags": ["Military", "Post-apocalyptic"],
                "rating": 9.0,
                "read_status": "completed"
            }
        },
        {
            "title": "One Piece",
            "description": "Pirates searching for treasure",
            "author": "Eiichiro Oda",
            "artist": "Eiichiro Oda",
            "status": "ongoing",
            "metadata_json": {
                "genres": ["Action", "Adventure", "Comedy"],
                "tags": ["Pirates", "Friendship"],
                "rating": 9.5,
                "read_status": "reading"
            }
        },
        {
            "title": "Death Note",
            "description": "Light Yagami finds a deadly notebook",
            "author": "Tsugumi Ohba",
            "artist": "Takeshi Obata",
            "status": "completed",
            "metadata_json": {
                "genres": ["Thriller", "Supernatural", "Drama"],
                "tags": ["Psychological", "Supernatural"],
                "rating": 8.8,
                "read_status": "completed"
            }
        },
        {
            "title": "Naruto",
            "description": "Ninja boy wants to become Hokage",
            "author": "Masashi Kishimoto",
            "artist": "Masashi Kishimoto",
            "status": "completed",
            "metadata_json": {
                "genres": ["Action", "Adventure"],
                "tags": ["Ninja", "Friendship"],
                "rating": 8.5,
                "read_status": "reading"
            }
        },
        {
            "title": "My Hero Academia",
            "description": "Boy without powers in a superhero world",
            "author": "Kohei Horikoshi",
            "artist": "Kohei Horikoshi",
            "status": "ongoing",
            "metadata_json": {
                "genres": ["Action", "Superhero"],
                "tags": ["School", "Superpowers"],
                "rating": 8.7,
                "read_status": "plan_to_read"
            }
        }
    ]


@pytest.fixture
async def create_test_series(db: AsyncSession, sample_series_data):
    """Create test series in the database."""
    created_series = []
    for data in sample_series_data:
        series = Series(**data)
        db.add(series)
        await db.commit()
        await db.refresh(series)
        created_series.append(series)
    return created_series


class TestSeriesFiltering:
    """Test series filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_text_search_filter(self, db: AsyncSession, create_test_series):
        """Test text search filtering."""
        service = SeriesService(db)
        
        # Search by title
        filters = SeriesFilterParams(search="Attack")
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 1
        assert result.items[0]["title"] == "Attack on Titan"
        
        # Search by author
        filters = SeriesFilterParams(search="Oda")
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 1
        assert result.items[0]["title"] == "One Piece"
    
    @pytest.mark.asyncio
    async def test_status_filter(self, db: AsyncSession, create_test_series):
        """Test status filtering."""
        service = SeriesService(db)
        
        # Filter by completed status
        filters = SeriesFilterParams(status=[SeriesStatus.COMPLETED])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 3  # Attack on Titan, Death Note, Naruto
        completed_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in completed_titles
        assert "Death Note" in completed_titles
        assert "Naruto" in completed_titles
        
        # Filter by ongoing status
        filters = SeriesFilterParams(status=[SeriesStatus.ONGOING])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # One Piece, My Hero Academia
        ongoing_titles = {item["title"] for item in result.items}
        assert "One Piece" in ongoing_titles
        assert "My Hero Academia" in ongoing_titles
    
    @pytest.mark.asyncio
    async def test_author_filter(self, db: AsyncSession, create_test_series):
        """Test author filtering."""
        service = SeriesService(db)
        
        filters = SeriesFilterParams(author="Hajime Isayama")
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 1
        assert result.items[0]["title"] == "Attack on Titan"
    
    @pytest.mark.asyncio
    async def test_genre_filter(self, db: AsyncSession, create_test_series):
        """Test genre filtering."""
        service = SeriesService(db)
        
        # Filter by Action genre
        filters = SeriesFilterParams(genres=["Action"])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 4  # Attack on Titan, One Piece, Naruto, My Hero Academia
        action_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in action_titles
        assert "One Piece" in action_titles
        assert "Naruto" in action_titles
        assert "My Hero Academia" in action_titles
        
        # Filter by Drama genre
        filters = SeriesFilterParams(genres=["Drama"])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # Attack on Titan, Death Note
        drama_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in drama_titles
        assert "Death Note" in drama_titles
    
    @pytest.mark.asyncio
    async def test_tag_filter(self, db: AsyncSession, create_test_series):
        """Test tag filtering."""
        service = SeriesService(db)
        
        # Filter by Friendship tag
        filters = SeriesFilterParams(tags=["Friendship"])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # One Piece, Naruto
        friendship_titles = {item["title"] for item in result.items}
        assert "One Piece" in friendship_titles
        assert "Naruto" in friendship_titles
    
    @pytest.mark.asyncio
    async def test_rating_filter(self, db: AsyncSession, create_test_series):
        """Test rating filtering."""
        service = SeriesService(db)
        
        from app.schemas.filters import RatingFilter
        
        # Filter by minimum rating
        rating_filter = RatingFilter(min_rating=9.0)
        filters = SeriesFilterParams(rating_filter=rating_filter)
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # Attack on Titan (9.0), One Piece (9.5)
        high_rated_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in high_rated_titles
        assert "One Piece" in high_rated_titles
        
        # Filter by rating range
        rating_filter = RatingFilter(min_rating=8.5, max_rating=9.0)
        filters = SeriesFilterParams(rating_filter=rating_filter)
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 3  # Attack on Titan (9.0), Death Note (8.8), Naruto (8.5)
    
    @pytest.mark.asyncio
    async def test_read_status_filter(self, db: AsyncSession, create_test_series):
        """Test read status filtering."""
        service = SeriesService(db)
        
        # Filter by completed read status
        filters = SeriesFilterParams(read_status=[ReadStatus.COMPLETED])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # Attack on Titan, Death Note
        completed_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in completed_titles
        assert "Death Note" in completed_titles
        
        # Filter by reading status
        filters = SeriesFilterParams(read_status=[ReadStatus.READING])
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # One Piece, Naruto
        reading_titles = {item["title"] for item in result.items}
        assert "One Piece" in reading_titles
        assert "Naruto" in reading_titles
    
    @pytest.mark.asyncio
    async def test_combined_filters_and_logic(self, db: AsyncSession, create_test_series):
        """Test combining multiple filters with AND logic."""
        service = SeriesService(db)
        
        # Filter by Action genre AND completed status
        filters = SeriesFilterParams(
            genres=["Action"],
            status=[SeriesStatus.COMPLETED],
            filter_logic=FilterLogic.AND
        )
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total == 2  # Attack on Titan, Naruto
        combined_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in combined_titles
        assert "Naruto" in combined_titles
    
    @pytest.mark.asyncio
    async def test_combined_filters_or_logic(self, db: AsyncSession, create_test_series):
        """Test combining multiple filters with OR logic."""
        service = SeriesService(db)
        
        # Filter by Drama genre OR Superhero genre
        filters = SeriesFilterParams(
            genres=["Drama", "Superhero"],
            filter_logic=FilterLogic.OR
        )
        result = await service.get_filtered_and_sorted_series(filters=filters)
        
        assert result.total >= 3  # At least Attack on Titan, Death Note, My Hero Academia
        or_titles = {item["title"] for item in result.items}
        assert "Attack on Titan" in or_titles
        assert "Death Note" in or_titles
        assert "My Hero Academia" in or_titles


class TestSeriesSorting:
    """Test series sorting functionality."""
    
    @pytest.mark.asyncio
    async def test_sort_by_title_asc(self, db: AsyncSession, create_test_series):
        """Test sorting by title ascending."""
        service = SeriesService(db)
        
        from app.schemas.filters import SortCriteria
        sort_criteria = [SortCriteria(field=SortField.TITLE, direction=SortDirection.ASC)]
        sorting = SeriesSortParams(sort_by=sort_criteria)
        
        result = await service.get_filtered_and_sorted_series(sorting=sorting)
        
        titles = [item["title"] for item in result.items]
        assert titles == sorted(titles)
    
    @pytest.mark.asyncio
    async def test_sort_by_title_desc(self, db: AsyncSession, create_test_series):
        """Test sorting by title descending."""
        service = SeriesService(db)
        
        from app.schemas.filters import SortCriteria
        sort_criteria = [SortCriteria(field=SortField.TITLE, direction=SortDirection.DESC)]
        sorting = SeriesSortParams(sort_by=sort_criteria)
        
        result = await service.get_filtered_and_sorted_series(sorting=sorting)
        
        titles = [item["title"] for item in result.items]
        assert titles == sorted(titles, reverse=True)
    
    @pytest.mark.asyncio
    async def test_sort_by_author(self, db: AsyncSession, create_test_series):
        """Test sorting by author."""
        service = SeriesService(db)
        
        from app.schemas.filters import SortCriteria
        sort_criteria = [SortCriteria(field=SortField.AUTHOR, direction=SortDirection.ASC)]
        sorting = SeriesSortParams(sort_by=sort_criteria)
        
        result = await service.get_filtered_and_sorted_series(sorting=sorting)
        
        authors = [item["author"] for item in result.items if item["author"]]
        assert authors == sorted(authors)
    
    @pytest.mark.asyncio
    async def test_sort_by_rating_desc(self, db: AsyncSession, create_test_series):
        """Test sorting by rating descending."""
        service = SeriesService(db)
        
        from app.schemas.filters import SortCriteria
        sort_criteria = [SortCriteria(field=SortField.RATING, direction=SortDirection.DESC)]
        sorting = SeriesSortParams(sort_by=sort_criteria)
        
        result = await service.get_filtered_and_sorted_series(sorting=sorting)
        
        # Extract ratings from metadata
        ratings = []
        for item in result.items:
            if item.get("metadata_json") and "rating" in item["metadata_json"]:
                ratings.append(item["metadata_json"]["rating"])
        
        assert ratings == sorted(ratings, reverse=True)
    
    @pytest.mark.asyncio
    async def test_multi_level_sorting(self, db: AsyncSession, create_test_series):
        """Test multi-level sorting (status then title)."""
        service = SeriesService(db)
        
        from app.schemas.filters import SortCriteria
        sort_criteria = [
            SortCriteria(field=SortField.STATUS, direction=SortDirection.ASC),
            SortCriteria(field=SortField.TITLE, direction=SortDirection.ASC)
        ]
        sorting = SeriesSortParams(sort_by=sort_criteria)
        
        result = await service.get_filtered_and_sorted_series(sorting=sorting)
        
        # Verify that items are first sorted by status, then by title within each status group
        prev_status = None
        prev_title = None
        for item in result.items:
            current_status = item["status"]
            current_title = item["title"]
            
            if prev_status is not None:
                if current_status == prev_status:
                    # Within same status, titles should be in ascending order
                    assert current_title >= prev_title
                else:
                    # Status should be in ascending order
                    assert current_status >= prev_status
            
            prev_status = current_status
            prev_title = current_title


class TestFilterPresets:
    """Test filter preset functionality."""
    
    @pytest.mark.asyncio
    async def test_create_filter_preset(self, db: AsyncSession):
        """Test creating a filter preset."""
        service = FilterPresetService(db)
        
        filters = SeriesFilterParams(
            search="action",
            status=[SeriesStatus.COMPLETED],
            genres=["Action"]
        )
        
        from app.schemas.filters import SortCriteria
        sorting = SeriesSortParams(
            sort_by=[SortCriteria(field=SortField.TITLE, direction=SortDirection.ASC)]
        )
        
        preset_data = FilterPresetCreate(
            name="Completed Action Series",
            description="All completed action series sorted by title",
            filters=filters,
            sorting=sorting,
            is_public=False
        )
        
        preset = await service.create_preset(preset_data, "test_user_id")
        
        assert preset.name == "Completed Action Series"
        assert preset.user_id == "test_user_id"
        assert preset.is_public is False
        assert preset.filters_json is not None
        assert preset.sorting_json is not None
    
    @pytest.mark.asyncio
    async def test_get_preset_by_id(self, db: AsyncSession):
        """Test retrieving a filter preset by ID."""
        service = FilterPresetService(db)
        
        # First create a preset
        filters = SeriesFilterParams(search="test")
        preset_data = FilterPresetCreate(
            name="Test Preset",
            filters=filters
        )
        
        created_preset = await service.create_preset(preset_data, "test_user_id")
        
        # Then retrieve it
        retrieved_preset = await service.get_preset_by_id(created_preset.id, "test_user_id")
        
        assert retrieved_preset is not None
        assert retrieved_preset.name == "Test Preset"
        assert retrieved_preset.user_id == "test_user_id"
    
    @pytest.mark.asyncio
    async def test_preset_name_uniqueness(self, db: AsyncSession):
        """Test that preset names must be unique per user."""
        service = FilterPresetService(db)
        
        filters = SeriesFilterParams(search="test")
        preset_data = FilterPresetCreate(
            name="Duplicate Name",
            filters=filters
        )
        
        # Create first preset
        await service.create_preset(preset_data, "test_user_id")
        
        # Try to create second preset with same name
        with pytest.raises(ValueError, match="already exists"):
            await service.create_preset(preset_data, "test_user_id")
    
    @pytest.mark.asyncio
    async def test_public_preset_access(self, db: AsyncSession):
        """Test that public presets are accessible to other users."""
        service = FilterPresetService(db)
        
        filters = SeriesFilterParams(search="public")
        preset_data = FilterPresetCreate(
            name="Public Preset",
            filters=filters,
            is_public=True
        )
        
        # Create public preset as user1
        preset = await service.create_preset(preset_data, "user1")
        
        # Access as user2
        retrieved_preset = await service.get_preset_by_id(preset.id, "user2")
        
        assert retrieved_preset is not None
        assert retrieved_preset.name == "Public Preset"
        assert retrieved_preset.is_public is True
    
    @pytest.mark.asyncio
    async def test_private_preset_access_denied(self, db: AsyncSession):
        """Test that private presets are not accessible to other users."""
        service = FilterPresetService(db)
        
        filters = SeriesFilterParams(search="private")
        preset_data = FilterPresetCreate(
            name="Private Preset",
            filters=filters,
            is_public=False
        )
        
        # Create private preset as user1
        preset = await service.create_preset(preset_data, "user1")
        
        # Try to access as user2
        retrieved_preset = await service.get_preset_by_id(preset.id, "user2")
        
        assert retrieved_preset is None


class TestFilteringAPI:
    """Test filtering API endpoints."""
    
    def test_filter_and_sort_endpoint(self, client: TestClient):
        """Test the comprehensive filtering and sorting endpoint."""
        filter_request = {
            "page": 1,
            "size": 10,
            "filters": {
                "search": "test",
                "status": ["completed"],
                "filter_logic": "and"
            },
            "sorting": {
                "sort_by": [
                    {"field": "title", "direction": "asc"}
                ]
            }
        }
        
        response = client.post("/api/v1/series/filter", json=filter_request)
        
        # Should return proper response structure even if no series match
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "applied_filters" in data
        assert "applied_sorting" in data
    
    def test_filter_options_endpoint(self, client: TestClient):
        """Test the filter options endpoint."""
        response = client.get("/api/v1/series/filter/options")
        
        assert response.status_code == 200
        data = response.json()
        assert "statuses" in data
        assert "authors" in data
        assert "artists" in data
        assert "genres" in data
        assert "tags" in data
    
    def test_clear_filters_endpoint(self, client: TestClient):
        """Test the clear filters endpoint."""
        response = client.post("/api/v1/series/filter/clear?page=1&size=20")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data