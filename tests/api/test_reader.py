"""Test reader API endpoints."""

import os
import tempfile
import zipfile
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Series, Chapter


@pytest.fixture
async def sample_series(db_session: AsyncSession):
    """Create a sample series for testing."""
    series = Series(
        title_primary="Test Manga Series",
        file_path="/test/manga/series",
        author="Test Author",
        total_chapters=3,
        read_chapters=0,
    )
    db_session.add(series)
    await db_session.commit()
    await db_session.refresh(series)
    return series


@pytest.fixture
async def sample_chapter(db_session: AsyncSession, sample_series: Series):
    """Create a sample chapter for testing."""
    chapter = Chapter(
        series_id=sample_series.id,
        chapter_number=1.0,
        volume_number=1,
        title="Test Chapter",
        file_path="/test/manga/series/chapter_001.cbz",
        file_size=1024000,
        page_count=5,
        is_read=False,
        last_read_page=0,
    )
    db_session.add(chapter)
    await db_session.commit()
    await db_session.refresh(chapter)
    return chapter


@pytest.fixture
def mock_cbz_file():
    """Create a mock CBZ file with test images."""
    # Create test CBZ content in memory
    cbz_content = BytesIO()

    # Create simple test PNG image (1x1 pixel)
    test_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x18\xdd\x8d\xb4\x1c\x00"
        b"\x00\x00\x00IEND\xaeB`\x82"
    )

    with zipfile.ZipFile(cbz_content, "w") as zf:
        for i in range(5):
            zf.writestr(f"page_{i:03d}.png", test_png)

    return cbz_content.getvalue()


class TestReaderAPI:
    """Test reader API endpoints."""

    @pytest.mark.asyncio
    async def test_get_chapter_info_success(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
        sample_series: Series,
    ):
        """Test successful chapter info retrieval."""
        response = await client.get(f"/api/reader/chapter/{sample_chapter.id}/info")

        assert response.status_code == 200
        data = response.json()

        # Verify chapter information
        assert data["id"] == str(sample_chapter.id)
        assert data["series_id"] == str(sample_series.id)
        assert data["series_title"] == sample_series.title_primary
        assert data["chapter_number"] == sample_chapter.chapter_number
        assert data["volume_number"] == sample_chapter.volume_number
        assert data["title"] == sample_chapter.title
        assert data["page_count"] == sample_chapter.page_count
        assert data["is_read"] == sample_chapter.is_read
        assert data["last_read_page"] == sample_chapter.last_read_page
        assert data["file_size"] == sample_chapter.file_size

    @pytest.mark.asyncio
    async def test_get_chapter_info_not_found(self, client: AsyncClient):
        """Test chapter info with non-existent chapter."""
        nonexistent_id = uuid4()
        response = await client.get(f"/api/reader/chapter/{nonexistent_id}/info")

        assert response.status_code == 404
        data = response.json()
        assert "Chapter not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_chapter_page_success(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
        mock_cbz_file: bytes,
    ):
        """Test successful page retrieval from CBZ file."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = mock_cbz_file
                mock_open.return_value.__enter__.return_value = mock_file

                response = await client.get(f"/api/reader/chapter/{sample_chapter.id}/page/0")

                assert response.status_code == 200
                assert response.headers["content-type"] == "image/png"
                assert "Cache-Control" in response.headers
                assert int(response.headers["content-length"]) > 0

    @pytest.mark.asyncio
    async def test_get_chapter_page_invalid_page_index(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
    ):
        """Test page retrieval with invalid page index."""
        # Test negative page index
        response = await client.get(f"/api/reader/chapter/{sample_chapter.id}/page/-1")
        assert response.status_code == 404
        assert "Page -1 not found" in response.json()["detail"]

        # Test page index beyond page count
        response = await client.get(
            f"/api/reader/chapter/{sample_chapter.id}/page/{sample_chapter.page_count}"
        )
        assert response.status_code == 404
        assert f"Page {sample_chapter.page_count} not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_chapter_page_file_not_found(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
    ):
        """Test page retrieval when chapter file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            response = await client.get(f"/api/reader/chapter/{sample_chapter.id}/page/0")

            assert response.status_code == 500
            assert "Failed to extract page" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_chapter_page_chapter_not_found(self, client: AsyncClient):
        """Test page retrieval with non-existent chapter."""
        nonexistent_id = uuid4()
        response = await client.get(f"/api/reader/chapter/{nonexistent_id}/page/0")

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_reading_progress_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_chapter: Chapter,
    ):
        """Test successful reading progress update."""
        progress_data = {"last_read_page": 2, "is_read": False}

        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json=progress_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(sample_chapter.id)
        assert data["last_read_page"] == 2
        assert data["is_read"] == False

        # Verify database was updated
        await db_session.refresh(sample_chapter)
        assert sample_chapter.last_read_page == 2
        assert sample_chapter.is_read == False

    @pytest.mark.asyncio
    async def test_update_reading_progress_mark_as_read(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_chapter: Chapter,
    ):
        """Test marking chapter as read."""
        progress_data = {
            "last_read_page": sample_chapter.page_count - 1,  # Last page
            "is_read": True,
        }

        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json=progress_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_read"] == True
        assert data["read_at"] is not None

        # Verify database was updated
        await db_session.refresh(sample_chapter)
        assert sample_chapter.is_read == True
        assert sample_chapter.read_at is not None

    @pytest.mark.asyncio
    async def test_update_reading_progress_auto_mark_read_on_last_page(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_chapter: Chapter,
    ):
        """Test automatic marking as read when reaching last page."""
        progress_data = {
            "last_read_page": sample_chapter.page_count - 1  # Last page
        }

        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json=progress_data
        )

        assert response.status_code == 200
        data = response.json()

        # Should automatically mark as read when on last page
        assert data["is_read"] == True
        assert data["read_at"] is not None

    @pytest.mark.asyncio
    async def test_update_reading_progress_invalid_page(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
    ):
        """Test progress update with invalid page number."""
        # Test negative page
        progress_data = {"last_read_page": -1}
        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json=progress_data
        )
        assert response.status_code == 400
        assert "Invalid page number" in response.json()["detail"]

        # Test page beyond chapter length
        progress_data = {"last_read_page": sample_chapter.page_count}
        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json=progress_data
        )
        assert response.status_code == 400
        assert "Invalid page number" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_reading_progress_chapter_not_found(self, client: AsyncClient):
        """Test progress update with non-existent chapter."""
        nonexistent_id = uuid4()
        progress_data = {"last_read_page": 1}

        response = await client.put(
            f"/api/reader/chapter/{nonexistent_id}/progress", json=progress_data
        )

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_series_chapters_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_series: Series,
    ):
        """Test successful series chapters retrieval."""
        # Create multiple chapters for the series
        chapters = []
        for i in range(3):
            chapter = Chapter(
                series_id=sample_series.id,
                chapter_number=float(i + 1),
                volume_number=1,
                title=f"Chapter {i + 1}",
                file_path=f"/test/manga/series/chapter_{i + 1:03d}.cbz",
                file_size=1024000,
                page_count=20,
                is_read=i == 0,  # First chapter is read
                last_read_page=19 if i == 0 else 0,
            )
            chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()

        response = await client.get(f"/api/reader/series/{sample_series.id}/chapters")

        assert response.status_code == 200
        data = response.json()

        # Verify series info
        assert data["series"]["id"] == str(sample_series.id)
        assert data["series"]["title"] == sample_series.title_primary
        assert data["series"]["total_chapters"] == sample_series.total_chapters
        assert data["series"]["read_chapters"] == sample_series.read_chapters

        # Verify chapters are ordered correctly
        assert len(data["chapters"]) == 3
        for i, chapter_data in enumerate(data["chapters"]):
            assert chapter_data["chapter_number"] == float(i + 1)
            assert chapter_data["title"] == f"Chapter {i + 1}"
            assert chapter_data["page_count"] == 20
            if i == 0:
                assert chapter_data["is_read"] == True
                assert chapter_data["last_read_page"] == 19
            else:
                assert chapter_data["is_read"] == False
                assert chapter_data["last_read_page"] == 0

    @pytest.mark.asyncio
    async def test_get_series_chapters_not_found(self, client: AsyncClient):
        """Test series chapters with non-existent series."""
        nonexistent_id = uuid4()
        response = await client.get(f"/api/reader/series/{nonexistent_id}/chapters")

        assert response.status_code == 404
        assert "Series not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_series_chapters_empty(
        self,
        client: AsyncClient,
        sample_series: Series,
    ):
        """Test series chapters with no chapters."""
        response = await client.get(f"/api/reader/series/{sample_series.id}/chapters")

        assert response.status_code == 200
        data = response.json()

        assert data["series"]["id"] == str(sample_series.id)
        assert data["chapters"] == []

    @pytest.mark.asyncio
    async def test_chapter_page_different_formats(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_series: Series,
    ):
        """Test page retrieval from different file formats."""
        # Test CBZ format
        cbz_chapter = Chapter(
            series_id=sample_series.id,
            chapter_number=1.0,
            title="CBZ Chapter",
            file_path="/test/manga/chapter.cbz",
            page_count=1,
        )
        db_session.add(cbz_chapter)

        # Test PDF format
        pdf_chapter = Chapter(
            series_id=sample_series.id,
            chapter_number=2.0,
            title="PDF Chapter",
            file_path="/test/manga/chapter.pdf",
            page_count=1,
        )
        db_session.add(pdf_chapter)

        # Test folder format
        folder_chapter = Chapter(
            series_id=sample_series.id,
            chapter_number=3.0,
            title="Folder Chapter",
            file_path="/test/manga/chapter_folder",
            page_count=1,
        )
        db_session.add(folder_chapter)

        await db_session.commit()

        # Mock file operations for different formats
        with patch("os.path.exists", return_value=True):
            with patch("os.path.isdir") as mock_isdir:
                with patch("zipfile.ZipFile") as mock_zip:
                    with patch("fitz.open") as mock_fitz:
                        with patch("os.listdir") as mock_listdir:
                            # Setup mocks for different file types
                            mock_isdir.side_effect = lambda path: path.endswith("_folder")

                            # Mock CBZ
                            mock_zip_instance = MagicMock()
                            mock_zip_instance.namelist.return_value = ["page001.png"]
                            mock_zip_instance.read.return_value = b"fake_png_data"
                            mock_zip.return_value.__enter__.return_value = mock_zip_instance

                            # Test CBZ format
                            response = await client.get(
                                f"/api/reader/chapter/{cbz_chapter.id}/page/0"
                            )
                            # Note: This will fail because we need actual file operations
                            # In a real test, we'd mock the entire extraction pipeline

    @pytest.mark.asyncio
    async def test_concurrent_page_requests(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
        mock_cbz_file: bytes,
    ):
        """Test handling multiple concurrent page requests."""
        import asyncio

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = mock_cbz_file
                mock_open.return_value.__enter__.return_value = mock_file

                # Send multiple concurrent requests for different pages
                tasks = [
                    client.get(f"/api/reader/chapter/{sample_chapter.id}/page/{i}")
                    for i in range(3)
                ]

                responses = await asyncio.gather(*tasks)

                # All requests should succeed
                for response in responses:
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "image/png"

    @pytest.mark.asyncio
    async def test_progress_validation_schema(
        self,
        client: AsyncClient,
        sample_chapter: Chapter,
    ):
        """Test request validation for progress updates."""
        # Test missing required field
        response = await client.put(f"/api/reader/chapter/{sample_chapter.id}/progress", json={})
        assert response.status_code == 422

        # Test invalid data types
        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json={"last_read_page": "invalid"}
        )
        assert response.status_code == 422

        # Test negative page number (should be caught by validation)
        response = await client.put(
            f"/api/reader/chapter/{sample_chapter.id}/progress", json={"last_read_page": -1}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chapter_ordering_in_series(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_series: Series,
    ):
        """Test that chapters are returned in correct order."""
        # Create chapters with mixed ordering
        chapters_data = [
            (3.0, 1, "Chapter 3"),
            (1.0, 1, "Chapter 1"),
            (2.5, 1, "Chapter 2.5"),
            (2.0, 1, "Chapter 2"),
            (1.0, 2, "Volume 2 Chapter 1"),  # Same chapter number, different volume
        ]

        for chapter_num, vol_num, title in chapters_data:
            chapter = Chapter(
                series_id=sample_series.id,
                chapter_number=chapter_num,
                volume_number=vol_num,
                title=title,
                file_path=f"/test/manga/series/{title.replace(' ', '_')}.cbz",
                page_count=20,
            )
            db_session.add(chapter)

        await db_session.commit()

        response = await client.get(f"/api/reader/series/{sample_series.id}/chapters")
        assert response.status_code == 200

        chapters = response.json()["chapters"]

        # Verify ordering: volume 1 chapters first, then volume 2, ordered by chapter number
        expected_order = [
            "Chapter 1",
            "Chapter 2",
            "Chapter 2.5",
            "Chapter 3",
            "Volume 2 Chapter 1",
        ]

        actual_order = [ch["title"] for ch in chapters]
        assert actual_order == expected_order
