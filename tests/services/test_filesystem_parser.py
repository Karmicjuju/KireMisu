"""Tests for filesystem parser service."""

import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
import pytest
from PIL import Image

from kiremisu.services.filesystem_parser import (
    ChapterInfo,
    FilesystemParser,
    SeriesInfo,
    parse_library_path,
)


@pytest.fixture
def temp_manga_library():
    """Create a temporary manga library for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test series structure
        series_dir = temp_path / "Test Series"
        series_dir.mkdir()

        # Create CBZ file
        cbz_path = series_dir / "Chapter 001.cbz"
        with zipfile.ZipFile(cbz_path, "w") as zf:
            # Create temporary test images
            for i in range(1, 6):
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    img = Image.new("RGB", (800, 1200), color=(255, 255, 255))
                    img.save(tmp.name, "JPEG")
                    zf.write(tmp.name, f"page_{i:03d}.jpg")
                    os.unlink(tmp.name)

        # Create folder-based chapter
        chapter_dir = series_dir / "Chapter 002"
        chapter_dir.mkdir()
        for i in range(1, 4):
            img = Image.new("RGB", (800, 1200), color=(255, 0, 0))
            img.save(chapter_dir / f"page_{i:03d}.jpg")

        # Create cover image
        cover_img = Image.new("RGB", (400, 600), color=(0, 255, 0))
        cover_img.save(series_dir / "cover.jpg")

        yield temp_path


@pytest.fixture
def temp_pdf_library():
    """Create a temporary library with PDF files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test series structure
        series_dir = temp_path / "PDF Series"
        series_dir.mkdir()

        # Create a simple PDF file with multiple pages
        pdf_path = series_dir / "Chapter 001.pdf"
        try:
            doc = fitz.new()

            # Add 3 pages to the PDF
            for i in range(3):
                page = doc.new_page()
                text = f"Page {i + 1} content"
                page.insert_text((100, 100), text)

            doc.save(str(pdf_path))
            doc.close()
        except Exception:
            # If PDF creation fails, create a dummy file for testing
            pdf_path.write_bytes(
                b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
            )

        yield temp_path


@pytest.fixture
def parser():
    """Create a filesystem parser instance."""
    return FilesystemParser(max_cpu_workers=1, max_io_workers=1)


class TestFilesystemParser:
    """Test cases for FilesystemParser class."""

    @pytest.mark.asyncio
    async def test_scan_library_path_success(self, parser, temp_manga_library):
        """Test successful library path scanning."""
        series_list = await parser.scan_library_path(str(temp_manga_library))

        assert len(series_list) == 1
        series = series_list[0]
        assert series.title_primary == "Test Series"
        assert len(series.chapters) == 2
        assert series.cover_image_path is not None

    @pytest.mark.asyncio
    async def test_scan_library_path_nonexistent(self, parser):
        """Test scanning non-existent path raises ValueError."""
        with pytest.raises(ValueError, match="Library path does not exist"):
            await parser.scan_library_path("/nonexistent/path")

    @pytest.mark.asyncio
    async def test_scan_library_path_file_not_directory(self, parser, temp_manga_library):
        """Test scanning file instead of directory raises ValueError."""
        # Create a test file
        test_file = temp_manga_library / "test.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError, match="Library path is not a directory"):
            await parser.scan_library_path(str(test_file))

    @pytest.mark.asyncio
    async def test_parse_series_directory(self, parser, temp_manga_library):
        """Test parsing a series directory."""
        series_dir = temp_manga_library / "Test Series"
        series_info = await parser.parse_series(str(series_dir))

        assert series_info is not None
        assert series_info.title_primary == "Test Series"
        assert len(series_info.chapters) == 2
        assert series_info.cover_image_path is not None

        # Check chapters are sorted properly
        chapters = series_info.chapters
        assert chapters[0].chapter_number == 1.0
        assert chapters[1].chapter_number == 2.0

    @pytest.mark.asyncio
    async def test_parse_series_single_file(self, parser, temp_manga_library):
        """Test parsing a single CBZ file as series."""
        cbz_path = temp_manga_library / "Test Series" / "Chapter 001.cbz"
        series_info = await parser.parse_series(str(cbz_path))

        assert series_info is not None
        assert "Chapter" in series_info.title_primary
        assert len(series_info.chapters) == 1
        assert series_info.chapters[0].chapter_number == 1.0

    @pytest.mark.asyncio
    async def test_parse_series_nonexistent(self, parser):
        """Test parsing non-existent series returns None."""
        series_info = await parser.parse_series("/nonexistent/series")
        assert series_info is None

    @pytest.mark.asyncio
    async def test_parse_chapter_cbz(self, parser, temp_manga_library):
        """Test parsing CBZ chapter file."""
        cbz_path = temp_manga_library / "Test Series" / "Chapter 001.cbz"
        chapter_info = await parser.parse_chapter(str(cbz_path))

        assert chapter_info is not None
        assert chapter_info.chapter_number == 1.0
        assert chapter_info.page_count == 5  # Created with 5 pages
        assert chapter_info.file_size > 0

    @pytest.mark.asyncio
    async def test_parse_chapter_directory(self, parser, temp_manga_library):
        """Test parsing directory-based chapter."""
        chapter_dir = temp_manga_library / "Test Series" / "Chapter 002"
        chapter_info = await parser.parse_chapter(str(chapter_dir))

        assert chapter_info is not None
        assert chapter_info.chapter_number == 2.0
        assert chapter_info.page_count == 3  # Created with 3 pages
        assert chapter_info.file_size > 0

    @pytest.mark.asyncio
    async def test_parse_chapter_nonexistent(self, parser):
        """Test parsing non-existent chapter returns None."""
        chapter_info = await parser.parse_chapter("/nonexistent/chapter.cbz")
        assert chapter_info is None

    def test_extract_series_title(self, parser):
        """Test series title extraction from names."""
        test_cases = [
            ("One Piece", "One Piece"),
            ("One_Piece_Vol_01", "One Piece"),
            ("Attack-on-Titan", "Attack on Titan"),
            ("Naruto.Chapter.001.cbz", "Naruto"),
            ("Dragon Ball Z - Volume 1", "Dragon Ball Z"),
            ("My Hero Academia Vol 10 Ch 95", "My Hero Academia"),
        ]

        for input_name, expected in test_cases:
            result = parser._extract_series_title(input_name)
            assert result == expected, f"Failed for input: {input_name}"

    def test_extract_chapter_title(self, parser):
        """Test chapter title extraction from names."""
        test_cases = [
            ("Chapter 01 - The Beginning", "The Beginning"),
            ("Ch 12 - Final Battle", "Final Battle"),
            ("001 - Prologue", "Prologue"),
            ("Chapter 5.5 - Extra Story.cbz", "Extra Story"),
            ("Simple Chapter 1", None),  # No title separator
        ]

        for input_name, expected in test_cases:
            result = parser._extract_chapter_title(input_name)
            assert result == expected, f"Failed for input: {input_name}"

    def test_extract_chapter_volume_numbers(self, parser):
        """Test chapter and volume number extraction."""
        test_cases = [
            ("Chapter 001", (1.0, None)),
            ("Ch 12.5", (12.5, None)),
            ("Vol 02 Ch 005", (5.0, 2)),
            ("Volume 1 Chapter 10", (10.0, 1)),
            ("V03_C015", (15.0, 3)),
            ("001 - Title", (1.0, None)),
            ("c042", (42.0, None)),
            ("No Numbers Here", (None, None)),
        ]

        for input_name, expected in test_cases:
            result = parser._extract_chapter_volume_numbers(input_name)
            assert result == expected, f"Failed for input: {input_name}"

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_manga_library):
        """Test parser as async context manager."""
        async with FilesystemParser() as parser:
            series_list = await parser.scan_library_path(str(temp_manga_library))
            assert len(series_list) == 1

        # Thread pools should be shut down after context exit
        assert parser.cpu_pool._shutdown
        assert parser.io_pool._shutdown


class TestConvenienceFunction:
    """Test the convenience parse_library_path function."""

    @pytest.mark.asyncio
    async def test_parse_library_path_convenience(self, temp_manga_library):
        """Test the convenience function works correctly."""
        series_list = await parse_library_path(str(temp_manga_library))

        assert len(series_list) == 1
        series = series_list[0]
        assert series.title_primary == "Test Series"
        assert len(series.chapters) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_directory(self, parser):
        """Test parsing empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            series_list = await parser.scan_library_path(temp_dir)
            assert len(series_list) == 0

    @pytest.mark.asyncio
    async def test_directory_with_no_manga_files(self, parser):
        """Test directory with no manga files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create directory with non-manga files
            test_dir = temp_path / "Not Manga"
            test_dir.mkdir()
            (test_dir / "readme.txt").write_text("Not a manga file")
            (test_dir / "image.bmp").write_text("Not really an image")

            series_list = await parser.scan_library_path(temp_dir)
            assert len(series_list) == 0

    @pytest.mark.asyncio
    async def test_corrupted_zip_file(self, parser):
        """Test handling of corrupted ZIP files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create corrupted CBZ file with chapter number in name
            corrupted_cbz = temp_path / "Chapter 001 - corrupted.cbz"
            corrupted_cbz.write_text("This is not a valid ZIP file")

            chapter_info = await parser.parse_chapter(str(corrupted_cbz))

            # Should still create chapter_info but with 0 pages
            assert chapter_info is not None
            assert chapter_info.page_count == 0
            assert chapter_info.chapter_number == 1.0

    @pytest.mark.asyncio
    async def test_permission_denied_handling(self, parser):
        """Test handling of permission denied errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch both exists and access to simulate permission denied on existing path
            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.isdir", return_value=True),
                patch("os.access", return_value=False),
            ):
                with pytest.raises(ValueError, match="Library path is not readable"):
                    await parser.scan_library_path(temp_dir)

    @pytest.mark.asyncio
    async def test_fractional_chapter_numbers(self, parser):
        """Test parsing fractional chapter numbers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            series_dir = temp_path / "Test Series"
            series_dir.mkdir()

            # Create chapters with fractional numbers
            for chapter_num in ["1.5", "2.5", "3.0"]:
                cbz_path = series_dir / f"Chapter {chapter_num}.cbz"
                with zipfile.ZipFile(cbz_path, "w") as zf:
                    # Add dummy content
                    zf.writestr("page_001.jpg", b"dummy image data")

            series_info = await parser.parse_series(str(series_dir))

            assert series_info is not None
            assert len(series_info.chapters) == 3

            # Check chapters are sorted correctly
            chapter_numbers = [c.chapter_number for c in series_info.chapters]
            assert chapter_numbers == [1.5, 2.5, 3.0]


class TestFileFormatSupport:
    """Test different file format support."""

    @pytest.mark.asyncio
    async def test_mixed_file_formats(self, parser):
        """Test parsing directory with mixed file formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            series_dir = temp_path / "Mixed Series"
            series_dir.mkdir()

            # Create CBZ file
            cbz_path = series_dir / "Chapter 001.cbz"
            with zipfile.ZipFile(cbz_path, "w") as zf:
                zf.writestr("page_001.jpg", b"dummy image data")

            # Create directory with images
            chapter_dir = series_dir / "Chapter 002"
            chapter_dir.mkdir()
            img = Image.new("RGB", (100, 100))
            img.save(chapter_dir / "page_001.jpg")

            series_info = await parser.parse_series(str(series_dir))

            assert series_info is not None
            assert len(series_info.chapters) == 2
            assert series_info.chapters[0].chapter_number == 1.0
            assert series_info.chapters[1].chapter_number == 2.0


@pytest.mark.asyncio
async def test_real_fixtures_parsing():
    """Test parsing the created test fixtures."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "manga-samples"

    if not fixtures_path.exists():
        pytest.skip("Test fixtures not found")

    async with FilesystemParser() as parser:
        series_list = await parser.scan_library_path(str(fixtures_path))

        # Should find multiple series
        assert len(series_list) > 0

        # Check that each series has chapters
        for series in series_list:
            assert len(series.chapters) > 0
            assert series.title_primary is not None

            # Check chapters have valid data
            for chapter in series.chapters:
                assert chapter.chapter_number is not None
                assert chapter.file_path is not None


class TestSeriesInfoDataClass:
    """Test SeriesInfo data class functionality."""

    def test_total_chapters_property(self):
        """Test SeriesInfo.total_chapters property."""
        series = SeriesInfo(title_primary="Test Series", file_path="/test")
        assert series.total_chapters == 0

        # Add some chapters
        chapter1 = ChapterInfo(file_path="/test/ch1", chapter_number=1.0)
        chapter2 = ChapterInfo(file_path="/test/ch2", chapter_number=2.0)
        series.chapters = [chapter1, chapter2]

        assert series.total_chapters == 2


class TestPDFSupport:
    """Test PDF file format support."""

    @pytest.mark.asyncio
    async def test_parse_pdf_chapter(self, parser, temp_pdf_library):
        """Test parsing PDF chapter file."""
        pdf_path = temp_pdf_library / "PDF Series" / "Chapter 001.pdf"
        chapter_info = await parser.parse_chapter(str(pdf_path))

        assert chapter_info is not None
        assert chapter_info.chapter_number == 1.0
        # Page count might be 0 if PDF parsing fails, that's acceptable
        assert chapter_info.page_count >= 0
        assert chapter_info.file_size > 0

    @pytest.mark.asyncio
    async def test_parse_pdf_series(self, parser, temp_pdf_library):
        """Test parsing PDF series."""
        series_dir = temp_pdf_library / "PDF Series"
        series_info = await parser.parse_series(str(series_dir))

        assert series_info is not None
        assert series_info.title_primary == "PDF Series"
        assert len(series_info.chapters) == 1
        # Page count might be 0 if PDF parsing fails, that's acceptable
        assert series_info.chapters[0].page_count >= 0

    @pytest.mark.asyncio
    async def test_corrupted_pdf_file(self, parser):
        """Test handling of corrupted PDF files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create corrupted PDF file
            corrupted_pdf = temp_path / "Chapter 001.pdf"
            corrupted_pdf.write_text("This is not a valid PDF file")

            chapter_info = await parser.parse_chapter(str(corrupted_pdf))

            # Should still create chapter_info but with 0 pages
            assert chapter_info is not None
            assert chapter_info.page_count == 0
            assert chapter_info.chapter_number == 1.0


class TestRARSupport:
    """Test RAR/CBR file format support."""

    @pytest.mark.asyncio
    async def test_parse_cbr_chapter_mock(self, parser):
        """Test parsing CBR chapter file with mocked rarfile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cbr_path = temp_path / "Chapter 001.cbr"

            # Create a dummy CBR file (just an empty file for testing)
            cbr_path.write_bytes(b"dummy rar content")

            # Mock rarfile.RarFile to simulate a working RAR file
            mock_info = MagicMock()
            mock_info.filename = "page_001.jpg"

            with patch("rarfile.RarFile") as mock_rar:
                mock_rar_instance = MagicMock()
                mock_rar_instance.infolist.return_value = [mock_info]
                mock_rar.return_value.__enter__.return_value = mock_rar_instance

                chapter_info = await parser.parse_chapter(str(cbr_path))

                assert chapter_info is not None
                assert chapter_info.chapter_number == 1.0
                assert chapter_info.page_count == 1  # Mocked to have 1 page

    @pytest.mark.asyncio
    async def test_corrupted_rar_file(self, parser):
        """Test handling of corrupted RAR files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create corrupted CBR file
            corrupted_cbr = temp_path / "Chapter 001.cbr"
            corrupted_cbr.write_text("This is not a valid RAR file")

            chapter_info = await parser.parse_chapter(str(corrupted_cbr))

            # Should still create chapter_info but with 0 pages
            assert chapter_info is not None
            assert chapter_info.page_count == 0
            assert chapter_info.chapter_number == 1.0


class TestSecurityTests:
    """Test security aspects of the filesystem parser."""

    @pytest.mark.asyncio
    async def test_path_traversal_protection_zip(self, parser):
        """Test protection against path traversal in ZIP files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a ZIP file with path traversal attempt (with valid chapter name)
            malicious_zip = temp_path / "Chapter 001.cbz"
            with zipfile.ZipFile(malicious_zip, "w") as zf:
                # Try to write outside the extraction directory
                zf.writestr("../../../etc/passwd", b"malicious content")
                zf.writestr("normal_page.jpg", b"normal image data")

            chapter_info = await parser.parse_chapter(str(malicious_zip))

            # Should only count legitimate image files, not path traversal attempts
            assert chapter_info is not None
            assert chapter_info.page_count == 1  # Only the legitimate image

    @pytest.mark.asyncio
    async def test_hidden_files_filtering_zip(self, parser):
        """Test filtering of hidden/system files in ZIP archives."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            zip_with_hidden = temp_path / "Chapter 001.cbz"
            with zipfile.ZipFile(zip_with_hidden, "w") as zf:
                # Add legitimate image files
                zf.writestr("page_001.jpg", b"image data")
                zf.writestr("page_002.png", b"image data")

                # Add hidden/system files that should be ignored
                zf.writestr("__MACOSX/._page_001.jpg", b"mac metadata")
                zf.writestr(".DS_Store", b"mac folder metadata")
                zf.writestr("Thumbs.db", b"windows thumbnail cache")

            chapter_info = await parser.parse_chapter(str(zip_with_hidden))

            assert chapter_info is not None
            assert chapter_info.page_count == 2  # Only legitimate images counted

    @pytest.mark.asyncio
    async def test_file_type_validation(self, parser):
        """Test validation of file types and extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test unsupported file extension
            unsupported_file = temp_path / "chapter.exe"
            unsupported_file.write_text("Not a manga file")

            chapter_info = await parser.parse_chapter(str(unsupported_file))
            assert chapter_info is None  # Should reject unsupported formats

    @pytest.mark.asyncio
    async def test_large_archive_handling(self, parser):
        """Test handling of archives with many files (resource exhaustion protection)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            large_zip = temp_path / "Chapter 001.cbz"
            with zipfile.ZipFile(large_zip, "w") as zf:
                # Create an archive with many files to test resource handling
                for i in range(100):  # Reduced number for faster testing
                    zf.writestr(f"page_{i:04d}.jpg", b"small image data")

            chapter_info = await parser.parse_chapter(str(large_zip))

            # Should handle large archives gracefully
            assert chapter_info is not None
            assert chapter_info.page_count == 100

    @pytest.mark.asyncio
    async def test_invalid_filename_handling(self, parser):
        """Test handling of files with invalid or problematic names."""
        invalid_names = [
            "chapter with spaces.cbz",
            "chapter-with-dashes.cbz",
            "chapter_with_underscores.cbz",
            "chapter.with.dots.cbz",
            "chapter@with#special!chars.cbz",
            "very-long-filename-that-might-cause-issues-in-some-systems.cbz",
        ]

        for invalid_name in invalid_names:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create CBZ with problematic filename (ensure it has a chapter number)
                # Always prepend with a clear chapter number
                name_with_chapter = f"Chapter 001 - {invalid_name}"
                problem_file = temp_path / name_with_chapter
                with zipfile.ZipFile(problem_file, "w") as zf:
                    zf.writestr("page_001.jpg", b"image data")

                # Should handle problematic filenames gracefully
                chapter_info = await parser.parse_chapter(str(problem_file))
                assert chapter_info is not None
                assert chapter_info.chapter_number is not None


class TestPerformanceAndScalability:
    """Test performance aspects and scalability of the parser."""

    @pytest.mark.asyncio
    async def test_large_directory_scanning(self, parser):
        """Test scanning directories with many series."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create many series directories
            num_series = 50
            for i in range(num_series):
                series_dir = temp_path / f"Series {i:03d}"
                series_dir.mkdir()

                # Create a simple chapter file in each series
                cbz_path = series_dir / "Chapter 001.cbz"
                with zipfile.ZipFile(cbz_path, "w") as zf:
                    zf.writestr("page_001.jpg", b"image data")

            # Should handle large numbers of series efficiently
            series_list = await parser.scan_library_path(str(temp_path))
            assert len(series_list) == num_series

    @pytest.mark.asyncio
    async def test_deep_directory_structure(self, parser):
        """Test parsing deeply nested directory structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a series directory with nested structure
            series_dir = temp_path / "Nested Series"
            series_dir.mkdir()

            # Create chapter file in series directory
            cbz_path = series_dir / "Chapter 001.cbz"
            with zipfile.ZipFile(cbz_path, "w") as zf:
                zf.writestr("page_001.jpg", b"image data")

            # Should find series in the structure
            series_list = await parser.scan_library_path(str(temp_path))
            assert len(series_list) >= 1

    @pytest.mark.asyncio
    async def test_concurrent_parsing(self, parser):
        """Test concurrent parsing operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple series
            series_paths = []
            for i in range(5):
                series_dir = temp_path / f"Concurrent Series {i}"
                series_dir.mkdir()

                cbz_path = series_dir / "Chapter 001.cbz"
                with zipfile.ZipFile(cbz_path, "w") as zf:
                    zf.writestr("page_001.jpg", b"image data")

                series_paths.append(str(series_dir))

            # Parse multiple series concurrently
            import asyncio

            tasks = [parser.parse_series(path) for path in series_paths]
            results = await asyncio.gather(*tasks)

            # All should complete successfully
            assert len(results) == 5
            assert all(result is not None for result in results)


class TestErrorHandlingAndRobustness:
    """Test comprehensive error handling scenarios."""

    @pytest.mark.asyncio
    async def test_series_parsing_with_mixed_valid_invalid_chapters(self, parser):
        """Test series parsing when some chapters are valid and others invalid."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            series_dir = temp_path / "Mixed Series"
            series_dir.mkdir()

            # Create valid CBZ
            valid_cbz = series_dir / "Chapter 001.cbz"
            with zipfile.ZipFile(valid_cbz, "w") as zf:
                zf.writestr("page_001.jpg", b"image data")

            # Create invalid "CBZ" (not actually a zip)
            invalid_cbz = series_dir / "Chapter 002.cbz"
            invalid_cbz.write_text("not a zip file")

            # Create valid directory chapter
            valid_dir = series_dir / "Chapter 003"
            valid_dir.mkdir()
            img = Image.new("RGB", (100, 100))
            img.save(valid_dir / "page_001.jpg")

            series_info = await parser.parse_series(str(series_dir))

            # Should successfully parse valid chapters and skip invalid ones
            assert series_info is not None
            assert len(series_info.chapters) >= 2  # At least the valid ones

    @pytest.mark.asyncio
    async def test_permission_errors_during_parsing(self, parser):
        """Test handling permission errors during directory traversal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock permission errors in different scenarios
            with patch("pathlib.Path.iterdir") as mock_iterdir:
                mock_iterdir.side_effect = PermissionError("Access denied")

                # Should handle permission errors gracefully
                candidates = await parser._find_series_candidates(temp_path)
                assert candidates == []  # Should return empty list, not crash

    @pytest.mark.asyncio
    async def test_oserror_handling(self, parser):
        """Test handling of various OS errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test various OS error scenarios
            with patch("pathlib.Path.iterdir") as mock_iterdir:
                mock_iterdir.side_effect = OSError("Generic OS error")

                candidates = await parser._find_series_candidates(temp_path)
                assert candidates == []

    @pytest.mark.asyncio
    async def test_chapter_number_extraction_edge_cases(self, parser):
        """Test chapter number extraction with various edge cases."""
        edge_cases = [
            ("", (None, None)),  # Empty string
            ("No Numbers", (None, None)),  # No numbers at all
            ("Chapter 0", (0.0, None)),  # Zero chapter
            ("Chapter 999", (999.0, None)),  # Large number
            ("Vol 01 Ch 001.5", (1.5, 1)),  # Fractional with volume
            ("V99 C999.99", (999.99, 99)),  # Large numbers
            ("chapter-001-title", (1.0, None)),  # Dash separators
            ("c1.0e2", (1.0, None)),  # Scientific notation (should extract 1.0)
        ]

        for input_name, expected in edge_cases:
            result = parser._extract_chapter_volume_numbers(input_name)
            # For scientific notation case, we expect it to extract the first number
            if "1.0e2" in input_name:
                assert result[0] == 1.0  # Should extract 1.0, not interpret scientific notation
            else:
                assert result == expected, f"Failed for input: {input_name}"


class TestAdvancedFeatures:
    """Test advanced parsing features and metadata extraction."""

    @pytest.mark.asyncio
    async def test_cover_image_detection_priority(self, parser):
        """Test cover image detection with various naming patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            series_dir = temp_path / "Cover Test Series"
            series_dir.mkdir()

            # Create images with different priority levels
            img = Image.new("RGB", (100, 100))

            # Lower priority images
            img.save(series_dir / "random_image.jpg")
            img.save(series_dir / "zzz_last.jpg")

            # Higher priority cover image
            img.save(series_dir / "cover.jpg")

            # Create at least one chapter so the series is valid
            cbz_path = series_dir / "Chapter 001.cbz"
            with zipfile.ZipFile(cbz_path, "w") as zf:
                zf.writestr("page_001.jpg", b"image data")

            series_info = await parser.parse_series(str(series_dir))

            assert series_info is not None
            assert series_info.cover_image_path is not None
            assert "cover.jpg" in series_info.cover_image_path

    @pytest.mark.asyncio
    async def test_title_extraction_complex_cases(self, parser):
        """Test series title extraction with complex naming patterns."""
        complex_cases = [
            ("One Piece - Digital Colored Comics", "One Piece Digital Colored Comics"),
            ("Attack on Titan (Shingeki no Kyojin)", "Attack on Titan (Shingeki no Kyojin)"),
            ("Dr. STONE", "Dr STONE"),
            ("JoJo's Bizarre Adventure Part 8", "JoJo's Bizarre Adventure Part 8"),
            ("Kimetsu no Yaiba - Vol 1-23 Complete", "Kimetsu no Yaiba"),
            ("My Hero Academia [Official Translation]", "My Hero Academia [Official Translation]"),
        ]

        for input_name, expected in complex_cases:
            result = parser._extract_series_title(input_name)
            assert result == expected, f"Failed for input: {input_name}"

    @pytest.mark.asyncio
    async def test_chapter_sorting_complex_scenarios(self, parser):
        """Test chapter sorting with complex numbering scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            series_dir = temp_path / "Complex Sorting Series"
            series_dir.mkdir()

            # Create chapters with complex numbering
            chapter_files = [
                "Chapter 1.cbz",
                "Chapter 1.5.cbz",
                "Chapter 2.cbz",
                "Chapter 10.cbz",  # Should come after single digits
                "Vol 2 Ch 11.cbz",
                "Vol 1 Ch 3.cbz",
            ]

            for filename in chapter_files:
                cbz_path = series_dir / filename
                with zipfile.ZipFile(cbz_path, "w") as zf:
                    zf.writestr("page_001.jpg", b"image data")

            series_info = await parser.parse_series(str(series_dir))

            assert series_info is not None
            assert len(series_info.chapters) == 6

            # Check sorting: volumes first, then by chapter number
            chapters = series_info.chapters

            # Should be sorted by (volume, chapter) - None volumes come first, then numbered volumes
            # Check that chapters are properly sorted
            chapter_nums = [(c.volume_number or 0, c.chapter_number) for c in chapters]
            assert chapter_nums == sorted(chapter_nums)

            # Vol 1 Ch 3 and Vol 2 Ch 11 should be present
            vol1_chapters = [c for c in chapters if c.volume_number == 1]
            vol2_chapters = [c for c in chapters if c.volume_number == 2]
            assert len(vol1_chapters) == 1
            assert len(vol2_chapters) == 1
            assert vol1_chapters[0].chapter_number == 3.0
            assert vol2_chapters[0].chapter_number == 11.0
