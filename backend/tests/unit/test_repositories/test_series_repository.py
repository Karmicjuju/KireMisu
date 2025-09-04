import pytest
from sqlalchemy.orm import Session

from app.models.series import Series
from app.repositories.series import SeriesRepository
from app.schemas.series import SeriesCreate, SeriesUpdate


class TestSeriesRepository:
    """Test class for SeriesRepository with PostgreSQL."""

    def test_create_series(self, db_session: Session):
        """Test creating a new series."""
        repo = SeriesRepository(db_session)
        
        series_data = SeriesCreate(
            title="Test Manga",
            description="A test manga series",
            author="Test Author",
            artist="Test Artist",
            status="ongoing",
            metadata_json={"genre": "action", "year": 2023}
        )
        
        series = repo.create_series(series_data)
        
        assert series.id is not None
        assert series.title == "Test Manga"
        assert series.description == "A test manga series"
        assert series.author == "Test Author"
        assert series.artist == "Test Artist"
        assert series.status == "ongoing"
        assert series.metadata_json["genre"] == "action"
        assert series.metadata_json["year"] == 2023
        assert series.created_at is not None
        assert series.updated_at is not None

    def test_create_series_minimal_data(self, db_session: Session):
        """Test creating a series with only required fields."""
        repo = SeriesRepository(db_session)
        
        series_data = SeriesCreate(title="Minimal Manga")
        series = repo.create_series(series_data)
        
        assert series.id is not None
        assert series.title == "Minimal Manga"
        assert series.description is None
        assert series.author is None
        assert series.artist is None
        assert series.status is None
        assert series.metadata_json is None

    def test_get_series_by_id(self, db_session: Session):
        """Test getting a series by ID."""
        repo = SeriesRepository(db_session)
        
        # Create a series first
        series_data = SeriesCreate(title="Test Manga")
        created_series = repo.create_series(series_data)
        
        # Get the series by ID
        retrieved_series = repo.get_series_by_id(created_series.id)
        
        assert retrieved_series is not None
        assert retrieved_series.id == created_series.id
        assert retrieved_series.title == "Test Manga"

    def test_get_series_by_id_not_found(self, db_session: Session):
        """Test getting a non-existent series by ID."""
        repo = SeriesRepository(db_session)
        
        series = repo.get_series_by_id(9999)
        assert series is None

    def test_get_all_series(self, db_session: Session):
        """Test getting all series with pagination."""
        repo = SeriesRepository(db_session)
        
        # Create multiple series
        for i in range(5):
            series_data = SeriesCreate(title=f"Test Manga {i}")
            repo.create_series(series_data)
        
        # Test pagination
        series_list = repo.get_all_series(skip=0, limit=3)
        assert len(series_list) == 3
        
        series_list = repo.get_all_series(skip=3, limit=3)
        assert len(series_list) == 2

    def test_get_series_count(self, db_session: Session):
        """Test getting total series count."""
        repo = SeriesRepository(db_session)
        
        initial_count = repo.get_series_count()
        
        # Create a series
        series_data = SeriesCreate(title="Test Manga")
        repo.create_series(series_data)
        
        new_count = repo.get_series_count()
        assert new_count == initial_count + 1

    def test_search_series(self, db_session: Session):
        """Test searching series by title, author, or artist."""
        repo = SeriesRepository(db_session)
        
        # Create test series
        series_data1 = SeriesCreate(
            title="Dragon Ball",
            author="Akira Toriyama",
            artist="Akira Toriyama"
        )
        series_data2 = SeriesCreate(
            title="One Piece",
            author="Eiichiro Oda",
            artist="Eiichiro Oda"
        )
        series_data3 = SeriesCreate(
            title="Naruto",
            author="Masashi Kishimoto",
            artist="Masashi Kishimoto"
        )
        
        repo.create_series(series_data1)
        repo.create_series(series_data2)
        repo.create_series(series_data3)
        
        # Search by title
        results = repo.search_series("Dragon")
        assert len(results) == 1
        assert results[0].title == "Dragon Ball"
        
        # Search by author
        results = repo.search_series("Oda")
        assert len(results) == 1
        assert results[0].title == "One Piece"
        
        # Search case insensitive
        results = repo.search_series("naruto")
        assert len(results) == 1
        assert results[0].title == "Naruto"

    def test_search_series_count(self, db_session: Session):
        """Test getting count of search results."""
        repo = SeriesRepository(db_session)
        
        # Create test series
        series_data1 = SeriesCreate(title="Dragon Ball", author="Akira Toriyama")
        series_data2 = SeriesCreate(title="Dragon Quest", author="Other Author")
        
        repo.create_series(series_data1)
        repo.create_series(series_data2)
        
        count = repo.search_series_count("Dragon")
        assert count == 2

    def test_get_series_by_status(self, db_session: Session):
        """Test getting series by status."""
        repo = SeriesRepository(db_session)
        
        # Create series with different statuses
        series_data1 = SeriesCreate(title="Ongoing Series", status="ongoing")
        series_data2 = SeriesCreate(title="Completed Series", status="completed")
        series_data3 = SeriesCreate(title="Another Ongoing", status="ongoing")
        
        repo.create_series(series_data1)
        repo.create_series(series_data2)
        repo.create_series(series_data3)
        
        # Get ongoing series
        ongoing_series = repo.get_series_by_status("ongoing")
        assert len(ongoing_series) == 2
        
        # Get completed series
        completed_series = repo.get_series_by_status("completed")
        assert len(completed_series) == 1
        assert completed_series[0].title == "Completed Series"

    def test_get_series_by_status_count(self, db_session: Session):
        """Test getting count of series by status."""
        repo = SeriesRepository(db_session)
        
        # Create series with different statuses
        series_data1 = SeriesCreate(title="Ongoing Series", status="ongoing")
        series_data2 = SeriesCreate(title="Completed Series", status="completed")
        
        repo.create_series(series_data1)
        repo.create_series(series_data2)
        
        ongoing_count = repo.get_series_by_status_count("ongoing")
        assert ongoing_count == 1
        
        completed_count = repo.get_series_by_status_count("completed")
        assert completed_count == 1

    def test_update_series(self, db_session: Session):
        """Test updating a series."""
        repo = SeriesRepository(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="Original Title", status="ongoing")
        series = repo.create_series(series_data)
        
        # Update the series
        update_data = SeriesUpdate(
            title="Updated Title",
            description="Updated description",
            status="completed"
        )
        updated_series = repo.update_series(series.id, update_data)
        
        assert updated_series is not None
        assert updated_series.title == "Updated Title"
        assert updated_series.description == "Updated description"
        assert updated_series.status == "completed"
        assert updated_series.updated_at > updated_series.created_at

    def test_update_series_not_found(self, db_session: Session):
        """Test updating a non-existent series."""
        repo = SeriesRepository(db_session)
        
        update_data = SeriesUpdate(title="Updated Title")
        updated_series = repo.update_series(9999, update_data)
        
        assert updated_series is None

    def test_delete_series(self, db_session: Session):
        """Test deleting a series."""
        repo = SeriesRepository(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="To Delete")
        series = repo.create_series(series_data)
        
        # Delete the series
        success = repo.delete_series(series.id)
        assert success is True
        
        # Verify it's deleted
        deleted_series = repo.get_series_by_id(series.id)
        assert deleted_series is None

    def test_delete_series_not_found(self, db_session: Session):
        """Test deleting a non-existent series."""
        repo = SeriesRepository(db_session)
        
        success = repo.delete_series(9999)
        assert success is False

    def test_is_title_taken(self, db_session: Session):
        """Test checking if a title is already taken."""
        repo = SeriesRepository(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="Unique Title")
        series = repo.create_series(series_data)
        
        # Check if title is taken
        assert repo.is_title_taken("Unique Title") is True
        assert repo.is_title_taken("Different Title") is False
        
        # Check with exclusion
        assert repo.is_title_taken("Unique Title", exclude_id=series.id) is False

    def test_get_recent_series(self, db_session: Session):
        """Test getting recently created series."""
        repo = SeriesRepository(db_session)
        
        # Create multiple series
        for i in range(5):
            series_data = SeriesCreate(title=f"Recent Series {i}")
            repo.create_series(series_data)
        
        recent_series = repo.get_recent_series(limit=3)
        assert len(recent_series) == 3
        
        # Should be ordered by created_at DESC
        for i in range(len(recent_series) - 1):
            assert recent_series[i].created_at >= recent_series[i + 1].created_at

    def test_get_updated_series(self, db_session: Session):
        """Test getting recently updated series."""
        repo = SeriesRepository(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="To Update")
        series = repo.create_series(series_data)
        
        # Update it
        update_data = SeriesUpdate(description="Updated description")
        repo.update_series(series.id, update_data)
        
        updated_series_list = repo.get_updated_series(limit=10)
        assert len(updated_series_list) >= 1
        assert updated_series_list[0].title == "To Update"

    def test_jsonb_metadata_operations(self, db_session: Session):
        """Test PostgreSQL JSONB operations with metadata."""
        repo = SeriesRepository(db_session)
        
        # Create a series with complex metadata
        metadata = {
            "genres": ["action", "adventure"],
            "rating": 9.5,
            "tags": {"demographic": "shounen", "serialization": "weekly"},
            "volumes": 42
        }
        
        series_data = SeriesCreate(
            title="Complex Metadata Series",
            metadata_json=metadata
        )
        series = repo.create_series(series_data)
        
        # Retrieve and verify the metadata
        retrieved = repo.get_series_by_id(series.id)
        assert retrieved.metadata_json["genres"] == ["action", "adventure"]
        assert retrieved.metadata_json["rating"] == 9.5
        assert retrieved.metadata_json["tags"]["demographic"] == "shounen"
        assert retrieved.metadata_json["volumes"] == 42
        
        # Update metadata
        new_metadata = {
            "genres": ["action", "adventure", "comedy"],
            "rating": 9.7,
            "tags": {"demographic": "shounen", "serialization": "weekly"},
            "volumes": 45,
            "status_note": "Recently updated"
        }
        
        update_data = SeriesUpdate(metadata_json=new_metadata)
        updated = repo.update_series(series.id, update_data)
        
        assert len(updated.metadata_json["genres"]) == 3
        assert updated.metadata_json["rating"] == 9.7
        assert updated.metadata_json["volumes"] == 45
        assert "status_note" in updated.metadata_json