"""Test library scan API endpoints."""

import tempfile
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import LibraryPath, Series, Chapter
from kiremisu.services.filesystem_parser import SeriesInfo, ChapterInfo
from kiremisu.services.importer import ImportStats


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
async def disabled_library_path(db_session: AsyncSession, temp_directory: str):
    """Create a disabled library path for testing."""
    import os

    disabled_path = temp_directory + "/disabled"
    os.makedirs(disabled_path, exist_ok=True)

    library_path = LibraryPath(
        path=disabled_path,
        enabled=False,
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
                source_metadata={"format": "cbz"},
            ),
            ChapterInfo(
                file_path="/test/manga/series/chapter_2.cbz",
                chapter_number=2.0,
                volume_number=1,
                title="Chapter 2",
                file_size=1024000,
                page_count=22,
                source_metadata={"format": "cbz"},
            ),
        ],
        author="Test Author",
        artist="Test Artist",
        description="A test manga series",
        source_metadata={"format": "cbz", "language": "en"},
    )


@pytest.mark.api
class TestLibraryScanAPI:
    """Test library scan API endpoints."""

    @pytest.mark.asyncio
    async def test_scan_library_all_paths_success(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test successful scan of all library paths."""
        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            mock_scan.return_value = [sample_series_info]

            # Test scanning all paths (no library_path_id in request)
            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "status" in data
            assert "message" in data
            assert "stats" in data

            # Verify status
            assert data["status"] == "completed"
            assert "Library scan completed" in data["message"]

            # Verify stats structure
            stats = data["stats"]
            assert "series_found" in stats
            assert "series_created" in stats
            assert "series_updated" in stats
            assert "chapters_found" in stats
            assert "chapters_created" in stats
            assert "chapters_updated" in stats
            assert "errors" in stats

            # Verify actual stats values
            assert stats["series_found"] == 1
            assert stats["series_created"] == 1
            assert stats["chapters_found"] == 2
            assert stats["chapters_created"] == 2
            assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_scan_library_specific_path_success(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test successful scan of specific library path."""
        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            mock_scan.return_value = [sample_series_info]

            # Test scanning specific path
            response = await client.post(
                "/api/library/scan", json={"library_path_id": str(sample_library_path.id)}
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "completed"
            assert "Library path scan completed" in data["message"]

            stats = data["stats"]
            assert stats["series_found"] == 1
            assert stats["series_created"] == 1
            assert stats["chapters_found"] == 2
            assert stats["chapters_created"] == 2
            assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_scan_library_specific_path_not_found(
        self,
        client: AsyncClient,
    ):
        """Test scan with non-existent library path ID."""
        nonexistent_id = uuid4()

        response = await client.post(
            "/api/library/scan", json={"library_path_id": str(nonexistent_id)}
        )

        assert response.status_code == 404
        data = response.json()
        assert "Library path not found" in data["detail"]
        assert str(nonexistent_id) in data["detail"]

    @pytest.mark.asyncio
    async def test_scan_library_with_errors(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test scan that completes with errors."""
        # Mock importer to return stats with errors
        mock_stats = ImportStats()
        mock_stats.series_found = 2
        mock_stats.series_created = 1
        mock_stats.chapters_found = 3
        mock_stats.chapters_created = 2
        mock_stats.errors = 1  # One error occurred

        with patch("kiremisu.services.importer.ImporterService.scan_library_paths") as mock_scan:
            mock_scan.return_value = mock_stats

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 200
            data = response.json()

            # Should indicate completed with errors
            assert data["status"] == "completed_with_errors"
            assert "1 errors encountered" in data["message"]
            assert data["stats"]["errors"] == 1

    @pytest.mark.asyncio
    async def test_scan_library_importer_value_error(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
    ):
        """Test scan with ValueError from importer."""
        with patch("kiremisu.services.importer.ImporterService.scan_library_paths") as mock_scan:
            mock_scan.side_effect = ValueError("Invalid library path configuration")

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 400
            data = response.json()
            assert "Invalid library path configuration" in data["detail"]

    @pytest.mark.asyncio
    async def test_scan_library_importer_generic_error(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
    ):
        """Test scan with generic error from importer."""
        with patch("kiremisu.services.importer.ImporterService.scan_library_paths") as mock_scan:
            mock_scan.side_effect = Exception("Database connection failed")

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 500
            data = response.json()
            assert "Library scan failed" in data["detail"]
            assert "Database connection failed" in data["detail"]

    @pytest.mark.asyncio
    async def test_scan_library_empty_request_body(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test scan with empty request body."""
        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            mock_scan.return_value = [sample_series_info]

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_scan_library_no_enabled_paths(
        self,
        client: AsyncClient,
        disabled_library_path: LibraryPath,
    ):
        """Test scan when no enabled library paths exist."""
        response = await client.post("/api/library/scan", json={})

        assert response.status_code == 200
        data = response.json()

        # Should complete successfully but with zero results
        assert data["status"] == "completed"
        assert data["stats"]["series_found"] == 0
        assert data["stats"]["series_created"] == 0
        assert data["stats"]["chapters_found"] == 0
        assert data["stats"]["chapters_created"] == 0
        assert data["stats"]["errors"] == 0

    @pytest.mark.asyncio
    async def test_scan_library_invalid_uuid_format(
        self,
        client: AsyncClient,
    ):
        """Test scan with invalid UUID format."""
        response = await client.post("/api/library/scan", json={"library_path_id": "invalid-uuid"})

        # Should return validation error for invalid UUID
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_scan_library_response_schema_validation(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test that response matches expected schema."""
        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            mock_scan.return_value = [sample_series_info]

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 200
            data = response.json()

            # Validate complete response structure
            required_fields = ["status", "message", "stats"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Validate stats structure
            stats = data["stats"]
            required_stats_fields = [
                "series_found",
                "series_created",
                "series_updated",
                "chapters_found",
                "chapters_created",
                "chapters_updated",
                "errors",
            ]
            for field in required_stats_fields:
                assert field in stats, f"Missing required stats field: {field}"
                assert isinstance(stats[field], int), f"Stats field {field} should be integer"

            # Validate status is a string
            assert isinstance(data["status"], str)
            assert isinstance(data["message"], str)

    @pytest.mark.asyncio
    async def test_scan_library_existing_series_update(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test scan that updates existing series."""
        # Create existing series in database
        existing_series = Series(
            title_primary="Existing Series",
            file_path="/test/manga/existing",
            author="Original Author",
            total_chapters=1,
        )
        db_session.add(existing_series)

        existing_chapter = Chapter(
            series_id=existing_series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Chapter 1",
            file_path="/test/manga/existing/chapter_1.cbz",
            file_size=1024000,
            page_count=20,
        )
        db_session.add(existing_chapter)
        await db_session.commit()

        # Create updated series info
        updated_series_info = SeriesInfo(
            title_primary="Updated Series Title",  # Changed
            file_path="/test/manga/existing",  # Same path for matching
            chapters=[
                ChapterInfo(
                    file_path="/test/manga/existing/chapter_1.cbz",
                    chapter_number=1.0,
                    volume_number=1,
                    title="Updated Chapter 1",  # Changed
                    file_size=2048000,  # Changed
                    page_count=25,  # Changed
                ),
                ChapterInfo(
                    file_path="/test/manga/existing/chapter_2.cbz",
                    chapter_number=2.0,
                    volume_number=1,
                    title="Chapter 2",
                    file_size=1024000,
                    page_count=20,
                ),  # New chapter
            ],
            author="Updated Author",  # Changed
        )

        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            mock_scan.return_value = [updated_series_info]

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 200
            data = response.json()

            # Should show updates
            stats = data["stats"]
            assert stats["series_found"] == 1
            assert stats["series_created"] == 0
            assert stats["series_updated"] == 1  # Existing series updated
            assert stats["chapters_found"] == 2
            assert stats["chapters_created"] == 1  # One new chapter
            assert stats["chapters_updated"] == 1  # One existing chapter updated

    @pytest.mark.asyncio
    async def test_scan_library_large_dataset(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
    ):
        """Test scan with large dataset."""
        # Create large series list
        large_series_list = []
        for i in range(10):  # 10 series
            chapters = []
            for j in range(5):  # 5 chapters each
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
                )
            )

        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            mock_scan.return_value = large_series_list

            response = await client.post("/api/library/scan", json={})

            assert response.status_code == 200
            data = response.json()

            # Verify large dataset handling
            assert data["status"] == "completed"
            stats = data["stats"]
            assert stats["series_found"] == 10
            assert stats["series_created"] == 10
            assert stats["chapters_found"] == 50
            assert stats["chapters_created"] == 50
            assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_scan_library_concurrent_requests(
        self,
        client: AsyncClient,
        sample_library_path: LibraryPath,
        sample_series_info: SeriesInfo,
    ):
        """Test handling of concurrent scan requests."""
        import asyncio

        with patch(
            "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
        ) as mock_scan:
            # Add delay to simulate longer processing
            async def slow_scan(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return [sample_series_info]

            mock_scan.side_effect = slow_scan

            # Send multiple concurrent requests
            tasks = [
                client.post("/api/library/scan", json={}),
                client.post("/api/library/scan", json={}),
                client.post("/api/library/scan", json={}),
            ]

            responses = await asyncio.gather(*tasks)

            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] in ["completed", "completed_with_errors"]

    @pytest.mark.asyncio
    async def test_scan_library_request_validation(
        self,
        client: AsyncClient,
    ):
        """Test request validation."""
        # Test with invalid JSON structure
        response = await client.post("/api/library/scan", json={"invalid_field": "value"})

        # Should accept extra fields (Pydantic model allows this by default)
        assert response.status_code in [200, 404]  # 404 if no paths exist

        # Test with None library_path_id (should be treated as scanning all paths)
        response = await client.post("/api/library/scan", json={"library_path_id": None})

        assert response.status_code in [200, 404]  # 404 if no paths exist

    @pytest.mark.asyncio
    async def test_scan_library_database_transaction_integrity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_library_path: LibraryPath,
    ):
        """Test database transaction integrity during scan."""
        # Create series that will partially fail
        series_info_list = [
            SeriesInfo(
                title_primary="Good Series",
                file_path="/test/manga/good",
                chapters=[
                    ChapterInfo(
                        file_path="/test/manga/good/chapter_1.cbz",
                        chapter_number=1.0,
                        volume_number=1,
                        title="Chapter 1",
                        file_size=1024000,
                        page_count=20,
                    )
                ],
            ),
            SeriesInfo(
                title_primary="Error Series",
                file_path="/test/manga/error",
                chapters=[
                    ChapterInfo(
                        file_path="/test/manga/error/chapter_1.cbz",
                        chapter_number=1.0,
                        volume_number=1,
                        title="Chapter 1",
                        file_size=1024000,
                        page_count=20,
                    )
                ],
            ),
        ]

        # Mock to fail on second series
        with patch("kiremisu.services.importer.ImporterService._create_series") as mock_create:

            async def selective_failure(self, db, series_info, stats):
                if series_info.title_primary == "Error Series":
                    raise Exception("Simulated database error")
                # Call original method for successful series
                from kiremisu.services.importer import ImporterService

                return await ImporterService._create_series(self, db, series_info, stats)

            mock_create.side_effect = selective_failure

            with patch(
                "kiremisu.services.filesystem_parser.FilesystemParser.scan_library_path"
            ) as mock_scan:
                mock_scan.return_value = series_info_list

                response = await client.post("/api/library/scan", json={})

                assert response.status_code == 200
                data = response.json()

                # Should complete with errors
                assert data["status"] == "completed_with_errors"
                assert data["stats"]["errors"] > 0

                # Check that good series was created despite error in second series
                from sqlalchemy import select

                result = await db_session.execute(select(Series))
                series_list = list(result.scalars().all())

                # Should have one series (the successful one)
                series_titles = [s.title_primary for s in series_list]
                assert "Good Series" in series_titles
                assert "Error Series" not in series_titles
