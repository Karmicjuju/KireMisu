"""Tests for chapters API endpoints."""

import asyncio
import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Series
from kiremisu.main import app


class TestChaptersAPI:
    """Test cases for chapters API endpoints."""

    @pytest.fixture
    async def test_series(self, db_session: AsyncSession):
        """Create a test series."""
        series = Series(
            id=uuid4(),
            title_primary="Test Series",
            language="en",
            file_path="/test/series",
            total_chapters=2,
            read_chapters=0,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)
        return series

    @pytest.fixture
    async def test_chapter_cbz(self, db_session: AsyncSession, test_series: Series):
        """Create a test chapter with CBZ file."""
        # Create a temporary CBZ file
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as f:
            cbz_path = f.name

        # Create a ZIP file with test images
        with zipfile.ZipFile(cbz_path, "w") as zf:
            # Add some test image entries (we'll just add text files for testing)
            zf.writestr("page_001.jpg", b"fake image data 1")
            zf.writestr("page_002.png", b"fake image data 2")
            zf.writestr("page_003.jpg", b"fake image data 3")

        chapter = Chapter(
            id=uuid4(),
            series_id=test_series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Test Chapter",
            file_path=cbz_path,
            file_size=1024,
            page_count=3,
        )
        db_session.add(chapter)
        await db_session.commit()
        await db_session.refresh(chapter)

        yield chapter

        # Cleanup
        Path(cbz_path).unlink(missing_ok=True)

    @pytest.fixture
    async def test_chapter_directory(self, db_session: AsyncSession, test_series: Series):
        """Create a test chapter with directory structure."""
        # Create a temporary directory with test images
        with tempfile.TemporaryDirectory() as temp_dir:
            chapter_dir = Path(temp_dir) / "chapter_001"
            chapter_dir.mkdir()

            # Create fake image files
            for i in range(1, 4):
                image_file = chapter_dir / f"page_{i:03d}.jpg"
                image_file.write_bytes(b"fake image data")

            chapter = Chapter(
                id=uuid4(),
                series_id=test_series.id,
                chapter_number=1.0,
                volume_number=1,
                title="Test Directory Chapter",
                file_path=str(chapter_dir),
                file_size=512,
                page_count=3,
            )
            db_session.add(chapter)
            await db_session.commit()
            await db_session.refresh(chapter)

            yield chapter

    @pytest.mark.asyncio
    async def test_get_chapter_success(self, async_client: AsyncClient, test_chapter_cbz: Chapter):
        """Test successful chapter retrieval."""
        response = await async_client.get(f"/api/chapters/{test_chapter_cbz.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_chapter_cbz.id)
        assert data["chapter_number"] == 1.0
        assert data["title"] == "Test Chapter"
        assert data["page_count"] == 3

    @pytest.mark.asyncio
    async def test_get_chapter_not_found(self, async_client: AsyncClient):
        """Test chapter not found error."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/chapters/{fake_id}")

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_chapter_pages_info_success(
        self, async_client: AsyncClient, test_chapter_cbz: Chapter
    ):
        """Test successful chapter pages info retrieval."""
        response = await async_client.get(f"/api/chapters/{test_chapter_cbz.id}/pages")

        assert response.status_code == 200
        data = response.json()
        assert data["chapter_id"] == str(test_chapter_cbz.id)
        assert data["total_pages"] == 3
        assert len(data["pages"]) == 3

        for i, page in enumerate(data["pages"], 1):
            assert page["page_number"] == i
            assert page["url"] == f"/api/chapters/{test_chapter_cbz.id}/pages/{i}"

    @pytest.mark.asyncio
    async def test_get_chapter_pages_info_not_found(self, async_client: AsyncClient):
        """Test chapter pages info for non-existent chapter."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/chapters/{fake_id}/pages")

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_chapter_page_invalid_page_number(
        self, async_client: AsyncClient, test_chapter_cbz: Chapter
    ):
        """Test page streaming with invalid page number."""
        # Test page number too high
        response = await async_client.get(f"/api/chapters/{test_chapter_cbz.id}/pages/10")
        assert response.status_code == 404
        assert "Page 10 not found" in response.json()["detail"]

        # Test page number too low
        response = await async_client.get(f"/api/chapters/{test_chapter_cbz.id}/pages/0")
        assert response.status_code == 404
        assert "Page 0 not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_chapter_page_chapter_not_found(self, async_client: AsyncClient):
        """Test page streaming for non-existent chapter."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/chapters/{fake_id}/pages/1")

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_series_chapters_success(
        self, async_client: AsyncClient, test_series: Series, test_chapter_cbz: Chapter
    ):
        """Test successful series chapters retrieval."""
        response = await async_client.get(f"/api/chapters/series/{test_series.id}/chapters")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(test_chapter_cbz.id)
        assert data[0]["series_id"] == str(test_series.id)

    @pytest.mark.asyncio
    async def test_get_series_chapters_series_not_found(self, async_client: AsyncClient):
        """Test series chapters for non-existent series."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/chapters/series/{fake_id}/chapters")

        assert response.status_code == 404
        assert "Series not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_series_chapters_pagination(
        self, async_client: AsyncClient, test_series: Series, db_session: AsyncSession
    ):
        """Test series chapters pagination."""
        # Create multiple chapters
        chapters = []
        for i in range(5):
            chapter = Chapter(
                id=uuid4(),
                series_id=test_series.id,
                chapter_number=float(i + 1),
                volume_number=1,
                title=f"Chapter {i + 1}",
                file_path=f"/test/chapter_{i + 1}.cbz",
                file_size=1024,
                page_count=10,
            )
            chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()

        # Test pagination
        response = await async_client.get(
            f"/api/chapters/series/{test_series.id}/chapters?skip=2&limit=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Should get chapters 3 and 4 (0-indexed, so skip 2 items)
        assert data[0]["chapter_number"] == 3.0
        assert data[1]["chapter_number"] == 4.0


class TestChapterPageStreaming:
    """Test cases for chapter page streaming functionality."""

    def test_natural_sort_key(self):
        """Test natural sorting of filenames."""
        from kiremisu.api.chapters import _natural_sort_key

        filenames = ["page_10.jpg", "page_2.jpg", "page_1.jpg", "page_20.jpg"]
        sorted_filenames = sorted(filenames, key=_natural_sort_key)

        expected = ["page_1.jpg", "page_2.jpg", "page_10.jpg", "page_20.jpg"]
        assert sorted_filenames == expected

    def test_get_content_type(self):
        """Test content type detection."""
        from kiremisu.api.chapters import _get_content_type

        assert _get_content_type("image.jpg") == "image/jpeg"
        assert _get_content_type("image.jpeg") == "image/jpeg"
        assert _get_content_type("image.png") == "image/png"
        assert _get_content_type("image.gif") == "image/gif"
        assert _get_content_type("image.webp") == "image/webp"
        assert _get_content_type("image.bmp") == "image/bmp"
        assert _get_content_type("image.tiff") == "image/tiff"
        assert _get_content_type("unknown.xyz") == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_get_page_from_zip_async(self):
        """Test page extraction from ZIP archives."""
        from kiremisu.api.chapters import _get_page_from_zip_async

        # Create a temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as f:
            cbz_path = Path(f.name)

        try:
            # Create a ZIP file with test images
            with zipfile.ZipFile(cbz_path, "w") as zf:
                zf.writestr("page_001.jpg", b"fake image data 1")
                zf.writestr("page_002.png", b"fake image data 2")
                zf.writestr("page_003.jpg", b"fake image data 3")
                zf.writestr("__MACOSX/._page_001.jpg", b"system file")  # Should be ignored

            # Test successful extraction
            result = await _get_page_from_zip_async(cbz_path, 1)
            assert result is not None
            assert result["filename"] == "page_001.jpg"

            # Test page out of bounds
            result = await _get_page_from_zip_async(cbz_path, 10)
            assert result is None

        finally:
            cbz_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_page_from_directory_async(self):
        """Test page extraction from directory structure."""
        from kiremisu.api.chapters import _get_page_from_directory_async

        with tempfile.TemporaryDirectory() as temp_dir:
            chapter_dir = Path(temp_dir)

            # Create fake image files
            (chapter_dir / "page_001.jpg").write_bytes(b"image 1")
            (chapter_dir / "page_002.png").write_bytes(b"image 2")
            (chapter_dir / "page_003.jpg").write_bytes(b"image 3")

            # Test successful extraction
            result = await _get_page_from_directory_async(chapter_dir, 1)
            assert result is not None
            assert result["filename"] == "page_001.jpg"

            # Test page out of bounds
            result = await _get_page_from_directory_async(chapter_dir, 10)
            assert result is None


class TestSecurityValidation:
    """Test security-related functionality."""

    @pytest.mark.asyncio
    async def test_path_traversal_protection(
        self, async_client: AsyncClient, db_session: AsyncSession, test_series: Series
    ):
        """Test that directory traversal attempts are blocked."""
        # Create a chapter with a suspicious path
        chapter = Chapter(
            id=uuid4(),
            series_id=test_series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Malicious Chapter",
            file_path="../../../etc/passwd",  # Potential directory traversal
            file_size=1024,
            page_count=1,
        )
        db_session.add(chapter)
        await db_session.commit()

        # Attempt to access page should be blocked
        response = await async_client.get(f"/api/chapters/{chapter.id}/pages/1")

        # Should return 404 or 403, not expose system files
        assert response.status_code in [403, 404]
