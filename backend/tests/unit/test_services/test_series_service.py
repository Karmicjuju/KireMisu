import pytest
from sqlalchemy.orm import Session

from app.services.series import SeriesService
from app.schemas.series import SeriesCreate, SeriesUpdate


class TestSeriesService:
    """Test class for SeriesService with business logic validation."""

    def test_create_series_success(self, db_session: Session):
        """Test creating a series through service layer."""
        service = SeriesService(db_session)
        
        series_data = SeriesCreate(
            title="Test Series",
            description="A test series",
            author="Test Author",
            status="ongoing"
        )
        
        series = service.create_series(series_data)
        
        assert series.id is not None
        assert series.title == "Test Series"
        assert series.description == "A test series"
        assert series.author == "Test Author"
        assert series.status == "ongoing"

    def test_create_series_duplicate_title(self, db_session: Session):
        """Test creating a series with duplicate title raises error."""
        service = SeriesService(db_session)
        
        # Create first series
        series_data1 = SeriesCreate(title="Duplicate Title")
        service.create_series(series_data1)
        
        # Try to create second series with same title
        series_data2 = SeriesCreate(title="Duplicate Title")
        
        with pytest.raises(ValueError, match="already exists"):
            service.create_series(series_data2)

    def test_get_series_by_id(self, db_session: Session):
        """Test getting series by ID through service."""
        service = SeriesService(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="Test Series")
        created_series = service.create_series(series_data)
        
        # Get the series
        retrieved_series = service.get_series_by_id(created_series.id)
        
        assert retrieved_series is not None
        assert retrieved_series.id == created_series.id
        assert retrieved_series.title == "Test Series"

    def test_get_series_by_id_not_found(self, db_session: Session):
        """Test getting non-existent series returns None."""
        service = SeriesService(db_session)
        
        series = service.get_series_by_id(9999)
        assert series is None

    def test_get_all_series_paginated(self, db_session: Session):
        """Test paginated series retrieval."""
        service = SeriesService(db_session)
        
        # Create multiple series
        for i in range(15):
            series_data = SeriesCreate(title=f"Series {i}")
            service.create_series(series_data)
        
        # Test pagination
        result = service.get_all_series_paginated(page=1, size=10)
        
        assert len(result.items) == 10
        assert result.total >= 15
        assert result.page == 1
        assert result.size == 10
        assert result.pages >= 2
        
        # Test second page
        result = service.get_all_series_paginated(page=2, size=10)
        assert len(result.items) >= 5
        assert result.page == 2

    def test_get_all_series_paginated_validation(self, db_session: Session):
        """Test pagination parameter validation."""
        service = SeriesService(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="Test Series")
        service.create_series(series_data)
        
        # Test invalid page numbers are corrected
        result = service.get_all_series_paginated(page=0, size=20)
        assert result.page == 1
        
        result = service.get_all_series_paginated(page=-1, size=20)
        assert result.page == 1
        
        # Test invalid size is corrected
        result = service.get_all_series_paginated(page=1, size=0)
        assert result.size == 20
        
        result = service.get_all_series_paginated(page=1, size=200)
        assert result.size == 20

    def test_search_series_paginated(self, db_session: Session):
        """Test searching series with pagination."""
        service = SeriesService(db_session)
        
        # Create test data
        series_data1 = SeriesCreate(title="Dragon Ball", author="Akira Toriyama")
        series_data2 = SeriesCreate(title="Dragon Quest", author="Other Author")
        series_data3 = SeriesCreate(title="One Piece", author="Eiichiro Oda")
        
        service.create_series(series_data1)
        service.create_series(series_data2)
        service.create_series(series_data3)
        
        # Search for "Dragon"
        result = service.search_series_paginated("Dragon", page=1, size=10)
        
        assert len(result.items) == 2
        assert result.total == 2
        assert result.page == 1
        
        # Check that both Dragon series are returned
        titles = [item.title for item in result.items]
        assert "Dragon Ball" in titles
        assert "Dragon Quest" in titles

    def test_get_series_by_status_paginated(self, db_session: Session):
        """Test filtering series by status."""
        service = SeriesService(db_session)
        
        # Create series with different statuses
        ongoing_data1 = SeriesCreate(title="Ongoing 1", status="ongoing")
        ongoing_data2 = SeriesCreate(title="Ongoing 2", status="ongoing")
        completed_data = SeriesCreate(title="Completed", status="completed")
        
        service.create_series(ongoing_data1)
        service.create_series(ongoing_data2)
        service.create_series(completed_data)
        
        # Filter by ongoing status
        result = service.get_series_by_status_paginated("ongoing", page=1, size=10)
        
        assert len(result.items) == 2
        assert result.total == 2
        for item in result.items:
            assert item.status == "ongoing"
        
        # Filter by completed status
        result = service.get_series_by_status_paginated("completed", page=1, size=10)
        
        assert len(result.items) == 1
        assert result.total == 1
        assert result.items[0].status == "completed"

    def test_update_series_success(self, db_session: Session):
        """Test updating a series through service layer."""
        service = SeriesService(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="Original Title", status="ongoing")
        series = service.create_series(series_data)
        
        # Update the series
        update_data = SeriesUpdate(
            title="Updated Title",
            description="New description",
            status="completed"
        )
        
        updated_series = service.update_series(series.id, update_data)
        
        assert updated_series is not None
        assert updated_series.title == "Updated Title"
        assert updated_series.description == "New description"
        assert updated_series.status == "completed"

    def test_update_series_duplicate_title(self, db_session: Session):
        """Test updating series to duplicate title raises error."""
        service = SeriesService(db_session)
        
        # Create two series
        series_data1 = SeriesCreate(title="First Series")
        series_data2 = SeriesCreate(title="Second Series")
        
        series1 = service.create_series(series_data1)
        series2 = service.create_series(series_data2)
        
        # Try to update series2 to have the same title as series1
        update_data = SeriesUpdate(title="First Series")
        
        with pytest.raises(ValueError, match="already exists"):
            service.update_series(series2.id, update_data)

    def test_update_series_not_found(self, db_session: Session):
        """Test updating non-existent series returns None."""
        service = SeriesService(db_session)
        
        update_data = SeriesUpdate(title="Updated Title")
        result = service.update_series(9999, update_data)
        
        assert result is None

    def test_delete_series_success(self, db_session: Session):
        """Test deleting a series."""
        service = SeriesService(db_session)
        
        # Create a series
        series_data = SeriesCreate(title="To Delete")
        series = service.create_series(series_data)
        
        # Delete the series
        success = service.delete_series(series.id)
        assert success is True
        
        # Verify it's deleted
        deleted_series = service.get_series_by_id(series.id)
        assert deleted_series is None

    def test_delete_series_not_found(self, db_session: Session):
        """Test deleting non-existent series returns False."""
        service = SeriesService(db_session)
        
        success = service.delete_series(9999)
        assert success is False

    def test_get_recent_series(self, db_session: Session):
        """Test getting recent series with limit validation."""
        service = SeriesService(db_session)
        
        # Create multiple series
        for i in range(15):
            series_data = SeriesCreate(title=f"Recent Series {i}")
            service.create_series(series_data)
        
        # Test with normal limit
        recent = service.get_recent_series(limit=5)
        assert len(recent) == 5
        
        # Test with limit validation (should cap at 50)
        recent = service.get_recent_series(limit=100)
        assert len(recent) <= 50

    def test_get_updated_series(self, db_session: Session):
        """Test getting recently updated series."""
        service = SeriesService(db_session)
        
        # Create and update a series
        series_data = SeriesCreate(title="To Update")
        series = service.create_series(series_data)
        
        # Update it
        update_data = SeriesUpdate(description="Updated description")
        service.update_series(series.id, update_data)
        
        # Get updated series
        updated = service.get_updated_series(limit=10)
        
        assert len(updated) >= 1
        # Should find our updated series
        titles = [s.title for s in updated]
        assert "To Update" in titles

    def test_get_series_by_author_paginated(self, db_session: Session):
        """Test getting series by author with pagination."""
        service = SeriesService(db_session)
        
        # Create series by different authors
        toriyama_data = SeriesCreate(title="Dragon Ball", author="Akira Toriyama")
        oda_data = SeriesCreate(title="One Piece", author="Eiichiro Oda")
        
        service.create_series(toriyama_data)
        service.create_series(oda_data)
        
        # Search by author
        result = service.get_series_by_author_paginated("Toriyama", page=1, size=10)
        
        assert len(result.items) == 1
        assert result.items[0].author == "Akira Toriyama"
        assert result.items[0].title == "Dragon Ball"

    def test_get_series_statistics(self, db_session: Session):
        """Test getting series statistics."""
        service = SeriesService(db_session)
        
        # Create series with different statuses
        ongoing_data1 = SeriesCreate(title="Ongoing 1", status="ongoing")
        ongoing_data2 = SeriesCreate(title="Ongoing 2", status="ongoing")
        completed_data = SeriesCreate(title="Completed", status="completed")
        hiatus_data = SeriesCreate(title="Hiatus", status="hiatus")
        
        service.create_series(ongoing_data1)
        service.create_series(ongoing_data2)
        service.create_series(completed_data)
        service.create_series(hiatus_data)
        
        # Get statistics
        stats = service.get_series_statistics()
        
        assert stats["total_series"] >= 4
        assert stats["status_counts"]["ongoing"] == 2
        assert stats["status_counts"]["completed"] == 1
        assert stats["status_counts"]["hiatus"] == 1
        
        # Should not include statuses with 0 count
        assert "cancelled" not in stats["status_counts"]

    def test_series_response_model_validation(self, db_session: Session):
        """Test that SeriesResponse models are properly validated."""
        service = SeriesService(db_session)
        
        # Create a series with metadata
        metadata = {"genre": "action", "rating": 9.5}
        series_data = SeriesCreate(
            title="Validation Test",
            description="Test description",
            author="Test Author",
            metadata_json=metadata
        )
        
        series = service.create_series(series_data)
        
        # Get through service (which returns SeriesResponse)
        result = service.get_all_series_paginated(page=1, size=10)
        
        found_series = None
        for item in result.items:
            if item.title == "Validation Test":
                found_series = item
                break
        
        assert found_series is not None
        assert found_series.title == "Validation Test"
        assert found_series.description == "Test description"
        assert found_series.author == "Test Author"
        assert found_series.metadata_json["genre"] == "action"
        assert found_series.metadata_json["rating"] == 9.5
        assert found_series.created_at is not None
        assert found_series.updated_at is not None