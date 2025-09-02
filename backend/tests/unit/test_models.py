from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.chapter import Chapter
from app.models.series import Series


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


class TestSeriesModel:
    """Test cases for Series database model."""

    def test_create_series_basic(self, db_session):
        """Test creating a basic series with required fields."""
        series = Series(
            title="Test Manga",
            description="A test manga series",
            author="Test Author",
            artist="Test Artist",
            status="ongoing"
        )

        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        assert series.id is not None
        assert series.title == "Test Manga"
        assert series.description == "A test manga series"
        assert series.author == "Test Author"
        assert series.artist == "Test Artist"
        assert series.status == "ongoing"
        assert series.created_at is not None
        assert series.updated_at is not None

    def test_create_series_with_metadata(self, db_session):
        """Test creating series with JSON metadata."""
        metadata = {
            "genres": ["Action", "Adventure"],
            "tags": ["Shounen", "Fantasy"],
            "publication_year": 2020,
            "rating": 8.5
        }

        series = Series(
            title="Metadata Test Manga",
            metadata_json=metadata
        )

        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        assert series.metadata_json == metadata
        assert series.metadata_json["genres"] == ["Action", "Adventure"]
        assert series.metadata_json["rating"] == 8.5

    def test_series_repr(self, db_session):
        """Test series string representation."""
        series = Series(
            title="Repr Test Manga",
            author="Repr Author"
        )

        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        expected = (
            f"<Series(id={series.id}, title='Repr Test Manga', "
            f"author='Repr Author')>"
        )
        assert repr(series) == expected


class TestChapterModel:
    """Test cases for Chapter database model."""

    def test_create_chapter_basic(self, db_session):
        """Test creating a basic chapter."""
        # First create a series
        series = Series(title="Test Series")
        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        # Create chapter
        chapter = Chapter(
            series_id=series.id,
            number=Decimal("1.0"),
            title="Test Chapter",
            file_path="/path/to/chapter1.cbz"
        )

        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        assert chapter.id is not None
        assert chapter.series_id == series.id
        assert chapter.number == Decimal("1.0")
        assert chapter.title == "Test Chapter"
        assert chapter.file_path == "/path/to/chapter1.cbz"
        assert chapter.read_status is False  # Default value
        assert chapter.created_at is not None

    def test_create_chapter_with_decimal_number(self, db_session):
        """Test creating chapter with decimal number (e.g., 1.5)."""
        series = Series(title="Test Series")
        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        chapter = Chapter(
            series_id=series.id,
            number=Decimal("1.5"),
            file_path="/path/to/chapter1.5.cbz"
        )

        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        assert chapter.number == Decimal("1.5")

    def test_chapter_unique_constraint(self, db_session):
        """Test unique constraint on series_id + number."""
        series = Series(title="Test Series")
        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        # Create first chapter
        chapter1 = Chapter(
            series_id=series.id,
            number=Decimal("1.0"),
            file_path="/path/to/chapter1.cbz"
        )
        db_session.add(chapter1)
        db_session.commit()

        # Try to create duplicate chapter with same series_id and number
        chapter2 = Chapter(
            series_id=series.id,
            number=Decimal("1.0"),  # Same number
            file_path="/path/to/different_chapter1.cbz"
        )

        db_session.add(chapter2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_chapter_repr(self, db_session):
        """Test chapter string representation."""
        series = Series(title="Test Series")
        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        chapter = Chapter(
            series_id=series.id,
            number=Decimal("2.0"),
            title="Chapter Two",
            file_path="/path/to/chapter2.cbz"
        )

        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        expected = (
            f"<Chapter(id={chapter.id}, series_id={series.id}, "
            f"number=2.00, title='Chapter Two')>"
        )
        assert repr(chapter) == expected


class TestSeriesChapterRelationship:
    """Test cases for Series-Chapter relationships."""

    def test_series_chapters_relationship(self, db_session):
        """Test bidirectional relationship between Series and Chapters."""
        # Create series
        series = Series(title="Relationship Test Series")
        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        # Create chapters
        chapter1 = Chapter(
            series_id=series.id,
            number=Decimal("1.0"),
            file_path="/path/to/chapter1.cbz"
        )
        chapter2 = Chapter(
            series_id=series.id,
            number=Decimal("2.0"),
            file_path="/path/to/chapter2.cbz"
        )

        db_session.add_all([chapter1, chapter2])
        db_session.commit()
        db_session.refresh(chapter1)
        db_session.refresh(chapter2)

        # Test series -> chapters relationship
        assert len(series.chapters) == 2
        chapter_numbers = {ch.number for ch in series.chapters}
        assert chapter_numbers == {Decimal("1.0"), Decimal("2.0")}

        # Test chapter -> series relationship
        assert chapter1.series.id == series.id
        assert chapter2.series.id == series.id
        assert chapter1.series.title == "Relationship Test Series"

    def test_cascade_delete(self, db_session):
        """Test that deleting series deletes associated chapters."""
        # Create series with chapters
        series = Series(title="Cascade Test Series")
        db_session.add(series)
        db_session.commit()
        db_session.refresh(series)

        chapter1 = Chapter(
            series_id=series.id,
            number=Decimal("1.0"),
            file_path="/path/to/chapter1.cbz"
        )
        chapter2 = Chapter(
            series_id=series.id,
            number=Decimal("2.0"),
            file_path="/path/to/chapter2.cbz"
        )

        db_session.add_all([chapter1, chapter2])
        db_session.commit()

        chapter1_id = chapter1.id
        chapter2_id = chapter2.id

        # Delete series
        db_session.delete(series)
        db_session.commit()

        # Verify chapters were also deleted due to cascade
        assert (
            db_session.query(Chapter)
            .filter(Chapter.id == chapter1_id)
            .first()
            is None
        )
        assert (
            db_session.query(Chapter)
            .filter(Chapter.id == chapter2_id)
            .first()
            is None
        )

