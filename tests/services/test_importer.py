"""Test importer service layer."""

import tempfile
import os
import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath, Series, Chapter
from kiremisu.services.importer import ImporterService, ImportStats
from kiremisu.services.filesystem_parser import SeriesInfo, ChapterInfo


@pytest.fixture
async def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def sample_library_path(db_session: AsyncSession, temp_directory: str):
    """Create a sample library path for testing."""
    library_path = LibraryPath(
        path=temp_directory,
        enabled=True,
        scan_interval_hours=24,
    )
    db_session.add(library_path)
    await db_session.commit()
    await db_session.refresh(library_path)
    return library_path


@pytest.fixture
async def sample_series_info():
    """Create sample series info for testing."""
    return SeriesInfo(
        title_primary="Test Manga Series",
        file_path="/test/manga/series",
        chapters=[
            ChapterInfo(
                file_path="/test/manga/series/chapter_1.cbz",
                chapter_number=1.0,
                volume_number=1,
                title="Chapter 1",
                file_size=1024000,
                page_count=20,
                source_metadata={"format": "cbz", "scan_quality": "high"},
            ),
            ChapterInfo(
                file_path="/test/manga/series/chapter_2.cbz",
                chapter_number=2.0,
                volume_number=1,
                title="Chapter 2",
                file_size=1024000,
                page_count=22,
                source_metadata={"format": "cbz", "scan_quality": "high"},
            ),
        ],
        author="Test Author",
        artist="Test Artist",
        description="A test manga series",
        source_metadata={"format": "cbz", "language": "en"},
    )


@pytest.fixture
async def existing_series(db_session: AsyncSession, sample_series_info: SeriesInfo):
    """Create an existing series in the database."""
    series = Series(
        title_primary=sample_series_info.title_primary,
        file_path=sample_series_info.file_path,
        author=sample_series_info.author,
        artist=sample_series_info.artist,
        description=sample_series_info.description,
        source_metadata=sample_series_info.source_metadata,
        total_chapters=len(sample_series_info.chapters),
    )
    db_session.add(series)
    await db_session.commit()
    await db_session.refresh(series)

    # Add existing chapters
    for chapter_info in sample_series_info.chapters:
        chapter = Chapter(
            series_id=series.id,
            chapter_number=chapter_info.chapter_number,
            volume_number=chapter_info.volume_number,
            title=chapter_info.title,
            file_path=chapter_info.file_path,
            file_size=chapter_info.file_size,
            page_count=chapter_info.page_count,
            source_metadata=chapter_info.source_metadata,
        )
        db_session.add(chapter)

    await db_session.commit()
    return series


class TestImportStats:
    """Test ImportStats class."""

    def test_init_defaults(self):
        """Test ImportStats initialization with default values."""
        stats = ImportStats()
        assert stats.series_found == 0
        assert stats.series_created == 0
        assert stats.series_updated == 0
        assert stats.chapters_found == 0
        assert stats.chapters_created == 0
        assert stats.chapters_updated == 0
        assert stats.errors == 0

    def test_to_dict(self):
        """Test converting stats to dictionary."""
        stats = ImportStats()
        stats.series_found = 2
        stats.series_created = 1
        stats.chapters_found = 5
        stats.chapters_created = 3
        stats.errors = 1

        expected = {
            "series_found": 2,
            "series_created": 1,
            "series_updated": 0,
            "chapters_found": 5,
            "chapters_created": 3,
            "chapters_updated": 0,
            "errors": 1,
        }
        assert stats.to_dict() == expected


class TestImporterService:
    """Test ImporterService functionality."""

    @pytest.mark.asyncio
    async def test_scan_library_paths_empty(self, db_session: AsyncSession):
        """Test scanning when no library paths exist."""
        importer = ImporterService()

        stats = await importer.scan_library_paths(db_session)

        assert stats.series_found == 0
        assert stats.series_created == 0
        assert stats.chapters_found == 0
        assert stats.errors == 0

    @pytest.mark.asyncio
    async def test_scan_library_paths_specific_id_not_found(self, db_session: AsyncSession):
        """Test scanning with non-existent library path ID."""
        importer = ImporterService()
        nonexistent_id = uuid4()

        with pytest.raises(ValueError, match=f"Library path not found: {nonexistent_id}"):
            await importer.scan_library_paths(db_session, library_path_id=nonexistent_id)

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_create_new_series(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test scanning and creating new series."""
        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [sample_series_info]

        importer = ImporterService()
        stats = await importer.scan_library_paths(db_session)

        # Verify statistics
        assert stats.series_found == 1
        assert stats.series_created == 1
        assert stats.series_updated == 0
        assert stats.chapters_found == 2
        assert stats.chapters_created == 2
        assert stats.chapters_updated == 0
        assert stats.errors == 0

        # Verify series was created in database
        from sqlalchemy import select

        result = await db_session.execute(select(Series))
        series_list = list(result.scalars().all())
        assert len(series_list) == 1

        series = series_list[0]
        assert series.title_primary == sample_series_info.title_primary
        assert series.file_path == sample_series_info.file_path
        assert series.author == sample_series_info.author
        assert series.total_chapters == 2

        # Verify chapters were created
        result = await db_session.execute(select(Chapter))
        chapters_list = list(result.scalars().all())
        assert len(chapters_list) == 2

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_update_existing_series(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
        existing_series: Series,
        sample_series_info: SeriesInfo,
    ):
        """Test scanning and updating existing series."""
        # Modify series info to test updates
        updated_series_info = SeriesInfo(
            title_primary="Updated Test Manga Series",  # Changed title
            file_path=sample_series_info.file_path,  # Same path (for matching)
            chapters=sample_series_info.chapters
            + [
                ChapterInfo(
                    file_path="/test/manga/series/chapter_3.cbz",
                    chapter_number=3.0,
                    volume_number=1,
                    title="Chapter 3",
                    file_size=1024000,
                    page_count=24,
                    source_metadata={"format": "cbz", "scan_quality": "high"},
                )
            ],  # Added new chapter
            author=sample_series_info.author,
            artist=sample_series_info.artist,
            description="Updated description",  # Changed description
            source_metadata={
                "format": "cbz",
                "language": "en",
                "publisher": "Test Publisher",
            },  # Updated metadata
        )

        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [updated_series_info]

        importer = ImporterService()
        stats = await importer.scan_library_paths(db_session)

        # Verify statistics
        assert stats.series_found == 1
        assert stats.series_created == 0
        assert stats.series_updated == 1
        assert stats.chapters_found == 3
        assert stats.chapters_created == 1  # One new chapter
        assert stats.chapters_updated == 0  # Existing chapters unchanged
        assert stats.errors == 0

        # Verify series was updated
        await db_session.refresh(existing_series)
        assert existing_series.title_primary == "Updated Test Manga Series"
        assert existing_series.description == "Updated description"
        assert existing_series.total_chapters == 3

        # Verify metadata was merged
        assert existing_series.source_metadata["format"] == "cbz"
        assert existing_series.source_metadata["language"] == "en"
        assert existing_series.source_metadata["publisher"] == "Test Publisher"

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_idempotent(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test that running scan multiple times is idempotent."""
        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [sample_series_info]

        importer = ImporterService()

        # First scan
        stats1 = await importer.scan_library_paths(db_session)
        assert stats1.series_created == 1
        assert stats1.chapters_created == 2

        # Second scan (should be idempotent)
        stats2 = await importer.scan_library_paths(db_session)
        assert stats2.series_created == 0
        assert stats2.series_updated == 0  # No changes, so no updates
        assert stats2.chapters_created == 0
        assert stats2.chapters_updated == 0  # No changes, so no updates

        # Verify only one series exists
        from sqlalchemy import select

        result = await db_session.execute(select(Series))
        series_list = list(result.scalars().all())
        assert len(series_list) == 1

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_transaction_rollback_on_series_error(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test transaction rollback when series import fails."""
        # Create a second series that will cause an error
        error_series_info = SeriesInfo(
            title_primary="Error Series",
            file_path="/test/manga/error_series",
            chapters=[
                ChapterInfo(
                    file_path="/test/manga/error_series/chapter_1.cbz",
                    chapter_number=1.0,
                    volume_number=1,
                    title="Chapter 1",
                    file_size=1024000,
                    page_count=20,
                )
            ],
        )

        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [sample_series_info, error_series_info]

        # Mock series creation to fail for the second series
        original_create_series = ImporterService._create_series

        async def mock_create_series(self, db, series_info, stats):
            if series_info.title_primary == "Error Series":
                raise Exception("Database error during series creation")
            return await original_create_series(self, db, series_info, stats)

        with patch.object(ImporterService, "_create_series", mock_create_series):
            importer = ImporterService()
            stats = await importer.scan_library_paths(db_session)

        # First series should succeed, second should fail
        assert stats.series_found == 2
        assert stats.series_created == 1  # Only first series succeeded
        assert stats.errors == 1  # Second series failed

        # Verify only the successful series was committed
        from sqlalchemy import select

        result = await db_session.execute(select(Series))
        series_list = list(result.scalars().all())
        assert len(series_list) == 1
        assert series_list[0].title_primary == "Test Manga Series"

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_parser_error(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test handling of parser errors."""
        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.side_effect = Exception("Parser error: corrupted files")

        importer = ImporterService()
        stats = await importer.scan_library_paths(db_session)

        # Should handle parser error gracefully
        assert stats.series_found == 0
        assert stats.errors == 1

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_fractional_chapters(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test handling of fractional chapter numbers."""
        series_info = SeriesInfo(
            title_primary="Test Manga with Fractional Chapters",
            file_path="/test/manga/fractional",
            chapters=[
                ChapterInfo(
                    file_path="/test/manga/fractional/chapter_1.cbz",
                    chapter_number=1.0,
                    volume_number=1,
                    title="Chapter 1",
                    file_size=1024000,
                    page_count=20,
                ),
                ChapterInfo(
                    file_path="/test/manga/fractional/chapter_1_5.cbz",
                    chapter_number=1.5,  # Fractional chapter
                    volume_number=1,
                    title="Chapter 1.5",
                    file_size=512000,
                    page_count=10,
                ),
                ChapterInfo(
                    file_path="/test/manga/fractional/chapter_2.cbz",
                    chapter_number=2.0,
                    volume_number=1,
                    title="Chapter 2",
                    file_size=1024000,
                    page_count=22,
                ),
            ],
        )

        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [series_info]

        importer = ImporterService()
        stats = await importer.scan_library_paths(db_session)

        # Verify fractional chapters are handled
        assert stats.series_created == 1
        assert stats.chapters_created == 3

        # Verify chapters in database with correct ordering
        from sqlalchemy import select

        result = await db_session.execute(select(Chapter).order_by(Chapter.chapter_number))
        chapters = list(result.scalars().all())
        assert len(chapters) == 3
        assert chapters[0].chapter_number == 1.0
        assert chapters[1].chapter_number == 1.5
        assert chapters[2].chapter_number == 2.0

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_jsonb_metadata_update(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
        existing_series: Series,
        sample_series_info: SeriesInfo,
    ):
        """Test JSONB metadata merging behavior."""
        # Set initial metadata on existing series
        existing_series.source_metadata = {
            "format": "cbz",
            "language": "en",
            "original_source": "scanner_v1",
        }
        await db_session.commit()

        # Create updated series info with new metadata
        updated_series_info = SeriesInfo(
            title_primary=sample_series_info.title_primary,
            file_path=sample_series_info.file_path,
            chapters=sample_series_info.chapters,
            author=sample_series_info.author,
            artist=sample_series_info.artist,
            description=sample_series_info.description,
            source_metadata={
                "format": "cbz",
                "language": "jp",  # Changed
                "scan_quality": "high",  # New field
                "original_source": "scanner_v2",  # Updated field
            },
        )

        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [updated_series_info]

        importer = ImporterService()
        stats = await importer.scan_library_paths(db_session)

        # Verify metadata was merged correctly
        await db_session.refresh(existing_series)
        metadata = existing_series.source_metadata

        assert metadata["format"] == "cbz"
        assert metadata["language"] == "jp"  # Updated
        assert metadata["scan_quality"] == "high"  # New field added
        assert metadata["original_source"] == "scanner_v2"  # Updated
        assert stats.series_updated == 1

    @pytest.mark.asyncio
    async def test_get_paths_to_scan_specific_id(
        self,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test getting specific library path to scan."""
        importer = ImporterService()

        paths = await importer._get_paths_to_scan(db_session, sample_library_path.id)

        assert len(paths) == 1
        assert paths[0].id == sample_library_path.id

    @pytest.mark.asyncio
    async def test_get_paths_to_scan_all_enabled(
        self,
        db_session: AsyncSession,
        temp_directory: str,
    ):
        """Test getting all enabled library paths."""
        # Create multiple library paths
        enabled_path = LibraryPath(
            path=temp_directory + "/enabled",
            enabled=True,
            scan_interval_hours=24,
        )
        disabled_path = LibraryPath(
            path=temp_directory + "/disabled",
            enabled=False,
            scan_interval_hours=24,
        )

        os.makedirs(enabled_path.path, exist_ok=True)
        os.makedirs(disabled_path.path, exist_ok=True)

        db_session.add_all([enabled_path, disabled_path])
        await db_session.commit()

        importer = ImporterService()
        paths = await importer._get_paths_to_scan(db_session)

        # Should only return enabled path
        assert len(paths) == 1
        assert paths[0].enabled is True

    @pytest.mark.asyncio
    async def test_update_last_scan_time(
        self,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test updating last scan time."""
        original_last_scan = sample_library_path.last_scan

        importer = ImporterService()
        await importer._update_last_scan_time(db_session, sample_library_path.id)
        await db_session.commit()

        # Refresh and verify update
        await db_session.refresh(sample_library_path)
        assert sample_library_path.last_scan is not None
        assert sample_library_path.last_scan != original_last_scan
        assert sample_library_path.last_scan > datetime.utcnow() - timedelta(seconds=10)

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_chapter_updates(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
        existing_series: Series,
        sample_series_info: SeriesInfo,
    ):
        """Test updating existing chapters with new information."""
        # Create updated series info with modified chapters
        updated_chapters = [
            ChapterInfo(
                file_path="/test/manga/series/chapter_1.cbz",
                chapter_number=1.0,
                volume_number=1,
                title="Updated Chapter 1 Title",  # Changed title
                file_size=2048000,  # Changed file size
                page_count=25,  # Changed page count
                source_metadata={"format": "cbz", "scan_quality": "ultra"},  # Updated metadata
            ),
            ChapterInfo(
                file_path="/test/manga/series/chapter_2.cbz",
                chapter_number=2.0,
                volume_number=1,
                title="Chapter 2",  # Unchanged
                file_size=1024000,  # Unchanged
                page_count=22,  # Unchanged
                source_metadata={"format": "cbz", "scan_quality": "high"},  # Unchanged
            ),
        ]

        updated_series_info = SeriesInfo(
            title_primary=sample_series_info.title_primary,
            file_path=sample_series_info.file_path,
            chapters=updated_chapters,
            author=sample_series_info.author,
            artist=sample_series_info.artist,
            description=sample_series_info.description,
            source_metadata=sample_series_info.source_metadata,
        )

        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = [updated_series_info]

        importer = ImporterService()
        stats = await importer.scan_library_paths(db_session)

        # Should detect chapter updates
        assert stats.chapters_updated == 1  # Only first chapter changed
        assert stats.chapters_created == 0  # No new chapters

        # Verify chapter updates in database
        from sqlalchemy import select

        result = await db_session.execute(select(Chapter).where(Chapter.chapter_number == 1.0))
        chapter1 = result.scalar_one()

        assert chapter1.title == "Updated Chapter 1 Title"
        assert chapter1.file_size == 2048000
        assert chapter1.page_count == 25
        assert chapter1.source_metadata["scan_quality"] == "ultra"

    @pytest.mark.asyncio
    @patch("kiremisu.services.importer.ImporterService._get_paths_to_scan")
    @patch("kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path")
    async def test_scan_library_paths_large_library_performance(
        self,
        mock_scan_library_path: AsyncMock,
        mock_get_paths_to_scan: AsyncMock,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test performance with large number of series and chapters."""
        # Create a large number of series with multiple chapters
        large_series_list = []
        for i in range(50):  # 50 series
            chapters = []
            for j in range(10):  # 10 chapters each
                chapters.append(
                    ChapterInfo(
                        file_path=f"/test/manga/series_{i}/chapter_{j}.cbz",
                        chapter_number=float(j + 1),
                        volume_number=1,
                        title=f"Chapter {j + 1}",
                        file_size=1024000,
                        page_count=20,
                    )
                )

            large_series_list.append(
                SeriesInfo(
                    title_primary=f"Test Series {i}",
                    file_path=f"/test/manga/series_{i}",
                    chapters=chapters,
                    author=f"Author {i}",
                    artist=f"Artist {i}",
                )
            )

        # Setup mocks
        mock_get_paths_to_scan.return_value = [sample_library_path]
        mock_scan_library_path.return_value = large_series_list

        importer = ImporterService()

        # Measure execution time
        import time

        start_time = time.time()
        stats = await importer.scan_library_paths(db_session)
        execution_time = time.time() - start_time

        # Verify results
        assert stats.series_found == 50
        assert stats.series_created == 50
        assert stats.chapters_found == 500
        assert stats.chapters_created == 500
        assert stats.errors == 0

        # Performance should be reasonable (under 10 seconds for this size)
        assert execution_time < 10.0

        # Verify database state
        from sqlalchemy import select, func

        result = await db_session.execute(select(func.count(Series.id)))
        series_count = result.scalar()
        assert series_count == 50

        result = await db_session.execute(select(func.count(Chapter.id)))
        chapter_count = result.scalar()
        assert chapter_count == 500
