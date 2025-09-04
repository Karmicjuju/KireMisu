import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.series import Series
from app.repositories.series import SeriesRepository
from app.schemas.series import SeriesCreate, SeriesUpdate


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def series_repository(db_session):
    """Create a series repository instance."""
    return SeriesRepository(db_session)


@pytest.fixture
def sample_series_create():
    """Sample series creation data."""
    return SeriesCreate(
        title="Test Manga Series",
        description="A test manga series for testing purposes",
        author="Test Author",
        artist="Test Artist",
        status="ongoing",
        cover_path="/covers/test_series.jpg",
        metadata_json={"genre": "action", "rating": 8.5}
    )


class TestSeriesRepository:
    """Test cases for SeriesRepository."""

    def test_create_series_success(self, series_repository, sample_series_create):
        """Test successful series creation."""
        series = series_repository.create(sample_series_create)
        
        assert series.id is not None
        assert series.title == "Test Manga Series"
        assert series.description == "A test manga series for testing purposes"
        assert series.author == "Test Author"
        assert series.artist == "Test Artist"
        assert series.status == "ongoing"
        assert series.cover_path == "/covers/test_series.jpg"
        assert series.metadata_json == {"genre": "action", "rating": 8.5}
        assert series.created_at is not None
        assert series.updated_at is not None

    def test_create_series_minimal_data(self, series_repository):
        """Test series creation with minimal required data."""
        minimal_series = SeriesCreate(title="Minimal Series")
        series = series_repository.create(minimal_series)
        
        assert series.id is not None
        assert series.title == "Minimal Series"
        assert series.description is None
        assert series.author is None
        assert series.artist is None
        assert series.status is None
        assert series.cover_path is None
        assert series.metadata_json is None

    def test_get_by_id(self, series_repository, sample_series_create):
        """Test getting series by ID."""
        created_series = series_repository.create(sample_series_create)
        
        retrieved_series = series_repository.get_by_id(created_series.id)
        
        assert retrieved_series is not None
        assert retrieved_series.id == created_series.id
        assert retrieved_series.title == "Test Manga Series"

    def test_get_by_id_not_found(self, series_repository):
        """Test getting series by non-existent ID returns None."""
        series = series_repository.get_by_id(999)
        assert series is None

    def test_get_all_empty(self, series_repository):
        """Test getting all series when none exist."""
        series_list = series_repository.get_all()
        assert series_list == []

    def test_get_all_with_data(self, series_repository, sample_series_create):
        """Test getting all series with pagination."""
        # Create multiple series
        for i in range(5):
            series_data = SeriesCreate(
                title=f"Test Series {i+1}",
                author=f"Author {i+1}"
            )
            series_repository.create(series_data)
        
        # Test pagination
        series_list = series_repository.get_all(skip=0, limit=3)
        assert len(series_list) == 3
        
        series_list = series_repository.get_all(skip=3, limit=3)
        assert len(series_list) == 2

    def test_get_total_count(self, series_repository):
        """Test getting total count of series."""
        # Initially no series
        assert series_repository.get_total_count() == 0
        
        # Create some series
        for i in range(3):
            series_data = SeriesCreate(title=f"Series {i+1}")
            series_repository.create(series_data)
        
        assert series_repository.get_total_count() == 3

    def test_update_series(self, series_repository, sample_series_create):
        """Test updating series information."""
        created_series = series_repository.create(sample_series_create)
        
        update_data = SeriesUpdate(
            title="Updated Title",
            description="Updated description",
            status="completed"
        )
        
        updated_series = series_repository.update(created_series.id, update_data)
        
        assert updated_series is not None
        assert updated_series.title == "Updated Title"
        assert updated_series.description == "Updated description"
        assert updated_series.status == "completed"
        assert updated_series.author == "Test Author"  # Should not change
        assert updated_series.artist == "Test Artist"  # Should not change

    def test_update_series_not_found(self, series_repository):
        """Test updating non-existent series returns None."""
        update_data = SeriesUpdate(title="Updated Title")
        result = series_repository.update(999, update_data)
        assert result is None

    def test_delete_series(self, series_repository, sample_series_create):
        """Test deleting series."""
        created_series = series_repository.create(sample_series_create)
        
        # Delete the series
        result = series_repository.delete(created_series.id)
        assert result is True
        
        # Verify series is deleted
        retrieved_series = series_repository.get_by_id(created_series.id)
        assert retrieved_series is None

    def test_delete_series_not_found(self, series_repository):
        """Test deleting non-existent series returns False."""
        result = series_repository.delete(999)
        assert result is False

    def test_get_by_title(self, series_repository, sample_series_create):
        """Test getting series by title."""
        series_repository.create(sample_series_create)
        
        retrieved_series = series_repository.get_by_title("Test Manga Series")
        
        assert retrieved_series is not None
        assert retrieved_series.title == "Test Manga Series"
        assert retrieved_series.author == "Test Author"

    def test_get_by_title_not_found(self, series_repository):
        """Test getting series by non-existent title returns None."""
        series = series_repository.get_by_title("Non-existent Series")
        assert series is None

    def test_get_by_author(self, series_repository):
        """Test getting series by author."""
        # Create series with different authors
        authors = ["Author A", "Author B", "Author A"]
        for i, author in enumerate(authors):
            series_data = SeriesCreate(title=f"Series {i+1}", author=author)
            series_repository.create(series_data)
        
        # Get series by Author A
        series_list = series_repository.get_by_author("Author A")
        assert len(series_list) == 2
        
        # Test pagination
        series_list = series_repository.get_by_author("Author A", skip=0, limit=1)
        assert len(series_list) == 1

    def test_get_by_status(self, series_repository):
        """Test getting series by status."""
        # Create series with different statuses
        statuses = ["ongoing", "completed", "ongoing"]
        for i, status in enumerate(statuses):
            series_data = SeriesCreate(title=f"Series {i+1}", status=status)
            series_repository.create(series_data)
        
        # Get series by ongoing status
        series_list = series_repository.get_by_status("ongoing")
        assert len(series_list) == 2
        
        # Test pagination
        series_list = series_repository.get_by_status("ongoing", skip=0, limit=1)
        assert len(series_list) == 1

    def test_search_by_title(self, series_repository):
        """Test searching series by title."""
        # Create series with different titles
        titles = ["Dragon Ball", "Dragon Quest", "One Piece", "Attack on Dragon"]
        for title in titles:
            series_data = SeriesCreate(title=title)
            series_repository.create(series_data)
        
        # Search for "Dragon"
        series_list = series_repository.search_by_title("Dragon")
        assert len(series_list) == 3
        
        # Search for "piece" (case insensitive)
        series_list = series_repository.search_by_title("piece")
        assert len(series_list) == 1
        assert series_list[0].title == "One Piece"
        
        # Test pagination
        series_list = series_repository.search_by_title("Dragon", skip=0, limit=2)
        assert len(series_list) == 2

    def test_search_by_title_not_found(self, series_repository):
        """Test searching for non-existent title returns empty list."""
        series_data = SeriesCreate(title="Test Series")
        series_repository.create(series_data)
        
        series_list = series_repository.search_by_title("Non-existent")
        assert series_list == []