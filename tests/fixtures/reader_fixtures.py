"""Test fixtures and utilities for reader functionality."""

import os
import shutil
import tempfile
import zipfile
from io import BytesIO

import pytest
from PIL import Image


def create_test_image(width: int = 800, height: int = 1200, color: str = "white") -> bytes:
    """Create a test image as PNG bytes.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        color: Background color

    Returns:
        PNG image data as bytes
    """
    img = Image.new("RGB", (width, height), color)

    # Add some content to make it look like a manga page
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(img)

    # Try to use a default font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except (OSError, ImportError):
        font = ImageFont.load_default()

    # Add page number
    draw.text((width // 2 - 50, height // 2), "Page Content", fill="black", font=font)

    # Add some decorative elements
    draw.rectangle([50, 50, width - 50, 150], outline="black", width=3)
    draw.rectangle([50, height - 150, width - 50, height - 50], outline="black", width=3)

    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def create_test_cbz(pages: int = 5, output_path: str = None) -> str:
    """Create a test CBZ file with specified number of pages.

    Args:
        pages: Number of pages to create
        output_path: Output file path (if None, creates temporary file)

    Returns:
        Path to created CBZ file
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".cbz")
        os.close(fd)

    with zipfile.ZipFile(output_path, "w") as zf:
        for i in range(pages):
            # Create different colored pages for variety
            colors = ["white", "lightgray", "lightblue", "lightyellow", "lightgreen"]
            color = colors[i % len(colors)]

            page_data = create_test_image(color=color)
            zf.writestr(f"page_{i + 1:03d}.png", page_data)

    return output_path


def create_test_cbr(pages: int = 5, output_path: str = None) -> str:
    """Create a test CBR file with specified number of pages.

    Note: This creates a ZIP file with .cbr extension since creating
    actual RAR files requires external tools.

    Args:
        pages: Number of pages to create
        output_path: Output file path (if None, creates temporary file)

    Returns:
        Path to created CBR file
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".cbr")
        os.close(fd)

    # Use same implementation as CBZ but with .cbr extension
    with zipfile.ZipFile(output_path, "w") as zf:
        for i in range(pages):
            colors = ["white", "lightgray", "lightblue", "lightyellow", "lightgreen"]
            color = colors[i % len(colors)]

            page_data = create_test_image(color=color)
            zf.writestr(f"page_{i + 1:03d}.png", page_data)

    return output_path


def create_test_folder_chapter(pages: int = 5, output_dir: str = None) -> str:
    """Create a test chapter as a folder with image files.

    Args:
        pages: Number of pages to create
        output_dir: Output directory path (if None, creates temporary directory)

    Returns:
        Path to created chapter directory
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    os.makedirs(output_dir, exist_ok=True)

    for i in range(pages):
        colors = ["white", "lightgray", "lightblue", "lightyellow", "lightgreen"]
        color = colors[i % len(colors)]

        page_data = create_test_image(color=color)
        page_path = os.path.join(output_dir, f"page_{i + 1:03d}.png")

        with open(page_path, "wb") as f:
            f.write(page_data)

    return output_dir


def create_test_pdf_chapter(pages: int = 5, output_path: str = None) -> str:
    """Create a test PDF chapter with specified number of pages.

    Args:
        pages: Number of pages to create
        output_path: Output file path (if None, creates temporary file)

    Returns:
        Path to created PDF file
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        pytest.skip("PyMuPDF not available for PDF test fixture creation")

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

    doc = fitz.open()  # Create new PDF

    for i in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 size

        # Add some content to the page
        text = f"Test PDF Page {i + 1}"
        point = fitz.Point(100, 100)
        page.insert_text(point, text, fontsize=20)

        # Add a rectangle
        rect = fitz.Rect(50, 150, 545, 792)
        page.draw_rect(rect, color=(0, 0, 0), width=2)

    doc.save(output_path)
    doc.close()

    return output_path


class ReaderTestFixtures:
    """Helper class for managing reader test fixtures."""

    def __init__(self):
        self.temp_dirs: list[str] = []
        self.temp_files: list[str] = []

    def create_test_library(self, base_dir: str = None) -> str:
        """Create a complete test library with multiple series and formats.

        Args:
            base_dir: Base directory for library (if None, creates temporary)

        Returns:
            Path to created library directory
        """
        if base_dir is None:
            base_dir = tempfile.mkdtemp()
            self.temp_dirs.append(base_dir)

        # Create series directories
        series_configs = [
            {
                "name": "Test Series A",
                "chapters": [
                    ("cbz", 5, "Chapter 001.cbz"),
                    ("cbz", 7, "Chapter 002.cbz"),
                    ("folder", 4, "Chapter 003"),
                ],
            },
            {
                "name": "Test Series B",
                "chapters": [
                    ("pdf", 6, "Chapter 1.pdf"),
                    ("cbr", 8, "Chapter 2.cbr"),
                ],
            },
            {
                "name": "Mixed Format Series",
                "chapters": [
                    ("cbz", 10, "Vol 1 Ch 001.cbz"),
                    ("folder", 12, "Vol 1 Ch 002"),
                    ("pdf", 8, "Vol 1 Ch 003.pdf"),
                    ("cbr", 15, "Vol 2 Ch 001.cbr"),
                ],
            },
        ]

        for series_config in series_configs:
            series_dir = os.path.join(base_dir, series_config["name"])
            os.makedirs(series_dir, exist_ok=True)

            for format_type, pages, filename in series_config["chapters"]:
                if format_type == "cbz":
                    file_path = os.path.join(series_dir, filename)
                    create_test_cbz(pages, file_path)
                    self.temp_files.append(file_path)

                elif format_type == "cbr":
                    file_path = os.path.join(series_dir, filename)
                    create_test_cbr(pages, file_path)
                    self.temp_files.append(file_path)

                elif format_type == "pdf":
                    file_path = os.path.join(series_dir, filename)
                    create_test_pdf_chapter(pages, file_path)
                    self.temp_files.append(file_path)

                elif format_type == "folder":
                    folder_path = os.path.join(series_dir, filename)
                    create_test_folder_chapter(pages, folder_path)
                    self.temp_dirs.append(folder_path)

        return base_dir

    def create_edge_case_files(self, base_dir: str) -> list[tuple[str, str]]:
        """Create files with edge cases for testing error handling.

        Args:
            base_dir: Directory to create files in

        Returns:
            List of (file_path, description) tuples
        """
        edge_cases = []

        # Empty CBZ file
        empty_cbz = os.path.join(base_dir, "empty.cbz")
        with zipfile.ZipFile(empty_cbz, "w") as zf:
            pass  # Create empty zip
        self.temp_files.append(empty_cbz)
        edge_cases.append((empty_cbz, "Empty CBZ file"))

        # CBZ with no images
        no_images_cbz = os.path.join(base_dir, "no_images.cbz")
        with zipfile.ZipFile(no_images_cbz, "w") as zf:
            zf.writestr("readme.txt", "This CBZ has no images")
        self.temp_files.append(no_images_cbz)
        edge_cases.append((no_images_cbz, "CBZ with no image files"))

        # Corrupted CBZ (invalid zip)
        corrupted_cbz = os.path.join(base_dir, "corrupted.cbz")
        with open(corrupted_cbz, "wb") as f:
            f.write(b"This is not a valid zip file")
        self.temp_files.append(corrupted_cbz)
        edge_cases.append((corrupted_cbz, "Corrupted CBZ file"))

        # Empty folder
        empty_folder = os.path.join(base_dir, "empty_folder")
        os.makedirs(empty_folder, exist_ok=True)
        self.temp_dirs.append(empty_folder)
        edge_cases.append((empty_folder, "Empty folder"))

        # Folder with no images
        no_images_folder = os.path.join(base_dir, "no_images_folder")
        os.makedirs(no_images_folder, exist_ok=True)
        with open(os.path.join(no_images_folder, "readme.txt"), "w") as f:
            f.write("No images here")
        self.temp_dirs.append(no_images_folder)
        edge_cases.append((no_images_folder, "Folder with no image files"))

        return edge_cases

    def cleanup(self):
        """Clean up all created temporary files and directories."""
        # Remove temporary files
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except OSError:
                pass

        # Remove temporary directories
        for dir_path in self.temp_dirs:
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
            except OSError:
                pass

        self.temp_files.clear()
        self.temp_dirs.clear()


@pytest.fixture
def reader_fixtures():
    """Pytest fixture providing ReaderTestFixtures instance."""
    fixtures = ReaderTestFixtures()
    yield fixtures
    fixtures.cleanup()


@pytest.fixture
def test_cbz_file():
    """Pytest fixture providing a temporary CBZ file."""
    cbz_path = create_test_cbz(pages=5)
    yield cbz_path
    try:
        os.unlink(cbz_path)
    except OSError:
        pass


@pytest.fixture
def test_pdf_file():
    """Pytest fixture providing a temporary PDF file."""
    pdf_path = create_test_pdf_chapter(pages=3)
    yield pdf_path
    try:
        os.unlink(pdf_path)
    except OSError:
        pass


@pytest.fixture
def test_folder_chapter():
    """Pytest fixture providing a temporary folder chapter."""
    folder_path = create_test_folder_chapter(pages=4)
    yield folder_path
    try:
        shutil.rmtree(folder_path)
    except OSError:
        pass


@pytest.fixture
def test_library(reader_fixtures):
    """Pytest fixture providing a complete test library."""
    library_path = reader_fixtures.create_test_library()
    yield library_path
    # Cleanup handled by reader_fixtures fixture


def create_test_chapter_data(
    series_id: str,
    chapter_number: float = 1.0,
    volume_number: int = 1,
    page_count: int = 5,
    file_format: str = "cbz",
) -> dict:
    """Create test chapter data for database insertion.

    Args:
        series_id: ID of the parent series
        chapter_number: Chapter number
        volume_number: Volume number
        page_count: Number of pages
        file_format: File format (cbz, cbr, pdf, folder)

    Returns:
        Dictionary with chapter data
    """
    file_extensions = {"cbz": ".cbz", "cbr": ".cbr", "pdf": ".pdf", "folder": ""}

    ext = file_extensions.get(file_format, ".cbz")
    file_path = f"/test/series/chapter_{int(chapter_number):03d}{ext}"

    return {
        "series_id": series_id,
        "chapter_number": chapter_number,
        "volume_number": volume_number,
        "title": f"Test Chapter {chapter_number}",
        "file_path": file_path,
        "file_size": 1024000,  # 1MB
        "page_count": page_count,
        "is_read": False,
        "last_read_page": 0,
    }


def create_mock_image_response(width: int = 800, height: int = 1200) -> bytes:
    """Create a mock image response for API mocking.

    Args:
        width: Image width
        height: Image height

    Returns:
        PNG image data as bytes
    """
    return create_test_image(width, height)


# Performance test helpers
def create_large_chapter_files(base_dir: str, pages: int = 100) -> list[str]:
    """Create large chapter files for performance testing.

    Args:
        base_dir: Directory to create files in
        pages: Number of pages per chapter

    Returns:
        List of created file paths
    """
    file_paths = []

    # Create multiple large chapters
    for i in range(5):
        cbz_path = os.path.join(base_dir, f"large_chapter_{i + 1}.cbz")
        create_test_cbz(pages, cbz_path)
        file_paths.append(cbz_path)

    return file_paths


def benchmark_page_extraction(file_path: str, iterations: int = 10) -> float:
    """Benchmark page extraction performance.

    Args:
        file_path: Path to test file
        iterations: Number of iterations to run

    Returns:
        Average time per extraction in seconds
    """
    import time

    from kiremisu.api.reader import _extract_page_from_archive, _extract_page_from_pdf

    _, ext = os.path.splitext(file_path.lower())

    total_time = 0
    for _ in range(iterations):
        start_time = time.time()

        if ext in {".cbz", ".zip"}:
            _extract_page_from_archive(file_path, 0, ext)
        elif ext == ".pdf":
            _extract_page_from_pdf(file_path, 0)

        end_time = time.time()
        total_time += end_time - start_time

    return total_time / iterations
