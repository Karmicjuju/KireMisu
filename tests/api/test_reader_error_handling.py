"""Test reader API error handling scenarios."""

import os
import tempfile
import zipfile
from unittest.mock import Mock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Series


@pytest.fixture
async def sample_series_and_chapter(db_session: AsyncSession):
    """Create sample series and chapter for error testing."""
    series = Series(
        title_primary="Error Test Series",
        file_path="/test/manga/error_series",
        author="Test Author",
        total_chapters=1,
    )
    db_session.add(series)
    await db_session.flush()

    chapter = Chapter(
        series_id=series.id,
        chapter_number=1.0,
        volume_number=1,
        title="Error Test Chapter",
        file_path="/test/manga/error_series/chapter_001.cbz",
        file_size=1024000,
        page_count=5,
        is_read=False,
        last_read_page=0,
    )
    db_session.add(chapter)
    await db_session.commit()
    await db_session.refresh(series)
    await db_session.refresh(chapter)

    return series, chapter


class TestReaderErrorHandling:
    """Test error handling scenarios in reader API."""

    @pytest.mark.asyncio
    async def test_get_page_file_not_found(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval when chapter file doesn't exist."""
        _, chapter = sample_series_and_chapter

        # Mock file system to return file not found
        with patch("os.path.exists", return_value=False):
            response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

            assert response.status_code == 500
            data = response.json()
            assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_page_corrupted_cbz(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval from corrupted CBZ file."""
        _, chapter = sample_series_and_chapter

        # Create a corrupted CBZ file (not a valid zip)
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as temp_file:
            temp_file.write(b"This is not a valid zip file")
            corrupted_path = temp_file.name

        try:
            # Update chapter path to point to corrupted file
            chapter.file_path = corrupted_path

            with patch("os.path.exists", return_value=True):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]
        finally:
            os.unlink(corrupted_path)

    @pytest.mark.asyncio
    async def test_get_page_empty_cbz(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval from empty CBZ file."""
        _, chapter = sample_series_and_chapter

        # Create an empty CBZ file
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, "w"):
                pass  # Create empty zip
            empty_cbz_path = temp_file.name

        try:
            chapter.file_path = empty_cbz_path

            with patch("os.path.exists", return_value=True):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]
        finally:
            os.unlink(empty_cbz_path)

    @pytest.mark.asyncio
    async def test_get_page_cbz_no_images(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval from CBZ with no image files."""
        _, chapter = sample_series_and_chapter

        # Create CBZ with only text files
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, "w") as zf:
                zf.writestr("readme.txt", "This CBZ has no images")
                zf.writestr("metadata.xml", "<metadata></metadata>")
            no_images_path = temp_file.name

        try:
            chapter.file_path = no_images_path

            with patch("os.path.exists", return_value=True):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]
        finally:
            os.unlink(no_images_path)

    @pytest.mark.asyncio
    async def test_get_page_permission_error(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval with file permission error."""
        _, chapter = sample_series_and_chapter

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile", side_effect=PermissionError("Permission denied")):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_page_memory_error(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval with memory error (large file)."""
        _, chapter = sample_series_and_chapter

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile", side_effect=MemoryError("Out of memory")):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_page_thread_pool_error(self, client: AsyncClient, sample_series_and_chapter):
        """Test page retrieval with thread pool execution error."""
        _, chapter = sample_series_and_chapter

        with patch("os.path.exists", return_value=True):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor.side_effect = RuntimeError(
                    "Thread pool error"
                )

                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_update_progress_database_error(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test progress update with database error."""
        _, chapter = sample_series_and_chapter

        progress_data = {"last_read_page": 2}

        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=Exception("Database error")
        ):
            response = await client.put(
                f"/api/reader/chapter/{chapter.id}/progress", json=progress_data
            )

            # Should return 500 for database errors
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_update_progress_concurrent_modification(
        self, client: AsyncClient, db_session: AsyncSession, sample_series_and_chapter
    ):
        """Test progress update with concurrent modification."""
        _, chapter = sample_series_and_chapter

        # Simulate concurrent modification by changing chapter in between
        progress_data = {"last_read_page": 2}

        # First request
        response1 = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=progress_data
        )
        assert response1.status_code == 200

        # Second concurrent request with different data
        progress_data2 = {"last_read_page": 3}
        response2 = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=progress_data2
        )
        assert response2.status_code == 200

        # Verify final state
        await db_session.refresh(chapter)
        assert chapter.last_read_page == 3

    @pytest.mark.asyncio
    async def test_get_chapter_info_database_connection_error(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test chapter info retrieval with database connection error."""
        _, chapter = sample_series_and_chapter

        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=Exception("Connection lost")
        ):
            response = await client.get(f"/api/reader/chapter/{chapter.id}/info")

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_page_with_invalid_uuid(self, client: AsyncClient):
        """Test page retrieval with malformed UUID."""
        response = await client.get("/api/reader/chapter/invalid-uuid/page/0")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_progress_with_invalid_data_types(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test progress update with invalid data types."""
        _, chapter = sample_series_and_chapter

        # Test with string instead of integer
        response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json={"last_read_page": "invalid"}
        )
        assert response.status_code == 422

        # Test with null value
        response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json={"last_read_page": None}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_page_with_extremely_large_page_index(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test page retrieval with extremely large page index."""
        _, chapter = sample_series_and_chapter

        response = await client.get(f"/api/reader/chapter/{chapter.id}/page/999999")

        assert response.status_code == 404
        data = response.json()
        assert "Page 999999 not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_network_timeout_simulation(self, client: AsyncClient, sample_series_and_chapter):
        """Test handling of network timeout during page extraction."""
        _, chapter = sample_series_and_chapter

        with patch("os.path.exists", return_value=True):
            with patch("asyncio.get_event_loop") as mock_loop:
                # Simulate timeout
                mock_loop.return_value.run_in_executor.side_effect = asyncio.TimeoutError(
                    "Operation timed out"
                )

                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_malformed_archive_handling(self, client: AsyncClient, sample_series_and_chapter):
        """Test handling of malformed archive files."""
        _, chapter = sample_series_and_chapter

        # Create malformed zip file
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as temp_file:
            # Write partial zip header
            temp_file.write(b"PK\x03\x04")  # ZIP file signature but incomplete
            malformed_path = temp_file.name

        try:
            chapter.file_path = malformed_path

            with patch("os.path.exists", return_value=True):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]
        finally:
            os.unlink(malformed_path)

    @pytest.mark.asyncio
    async def test_pdf_processing_error(self, client: AsyncClient, sample_series_and_chapter):
        """Test PDF processing errors."""
        _, chapter = sample_series_and_chapter
        chapter.file_path = "/test/chapter.pdf"

        with patch("os.path.exists", return_value=True):
            with patch("fitz.open", side_effect=Exception("PDF processing error")):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_folder_chapter_permission_denied(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test folder chapter with permission denied."""
        _, chapter = sample_series_and_chapter
        chapter.file_path = "/test/chapter_folder"

        with patch("os.path.exists", return_value=True):
            with patch("os.path.isdir", return_value=True):
                with patch("os.listdir", side_effect=PermissionError("Permission denied")):
                    response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                    assert response.status_code == 500
                    data = response.json()
                    assert "Failed to extract page" in data["detail"]

    @pytest.mark.asyncio
    async def test_image_corruption_handling(self, client: AsyncClient, sample_series_and_chapter):
        """Test handling of corrupted image files in archive."""
        _, chapter = sample_series_and_chapter

        # Create CBZ with corrupted image
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, "w") as zf:
                # Add corrupted "image" file
                zf.writestr("page001.png", b"This is not a valid PNG file")
            corrupted_images_path = temp_file.name

        try:
            chapter.file_path = corrupted_images_path

            with patch("os.path.exists", return_value=True):
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")

                # Should still return the corrupted data (client will handle the error)
                # Or return 500 if we add image validation
                assert response.status_code in [200, 500]

        finally:
            os.unlink(corrupted_images_path)

    @pytest.mark.asyncio
    async def test_very_large_page_count_mismatch(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test handling when actual page count doesn't match database."""
        _, chapter = sample_series_and_chapter

        # Set page count to 5 but create CBZ with only 2 pages
        chapter.page_count = 5

        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, "w") as zf:
                zf.writestr("page001.png", b"fake_png_data")
                zf.writestr("page002.png", b"fake_png_data")
            limited_pages_path = temp_file.name

        try:
            chapter.file_path = limited_pages_path

            with patch("os.path.exists", return_value=True):
                # Try to access page 4 (should fail)
                response = await client.get(f"/api/reader/chapter/{chapter.id}/page/4")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to extract page" in data["detail"]

        finally:
            os.unlink(limited_pages_path)

    @pytest.mark.asyncio
    async def test_concurrent_page_requests_resource_exhaustion(
        self, client: AsyncClient, sample_series_and_chapter
    ):
        """Test resource exhaustion with many concurrent page requests."""
        import asyncio

        _, chapter = sample_series_and_chapter

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                # Mock zip file with delay to simulate slow processing
                async def slow_read(*args, **kwargs):
                    await asyncio.sleep(0.1)
                    return b"fake_image_data"

                mock_zip_instance = Mock()
                mock_zip_instance.namelist.return_value = ["page001.png"]
                mock_zip_instance.read = slow_read
                mock_zip.return_value.__enter__.return_value = mock_zip_instance

                # Send many concurrent requests
                tasks = [client.get(f"/api/reader/chapter/{chapter.id}/page/0") for _ in range(20)]

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # Some requests might fail due to resource limits
                success_count = sum(
                    1 for r in responses if not isinstance(r, Exception) and r.status_code == 200
                )
                error_count = len(responses) - success_count

                # Should handle at least some requests successfully
                assert success_count > 0
                # Some might fail due to resource constraints
                assert error_count >= 0
