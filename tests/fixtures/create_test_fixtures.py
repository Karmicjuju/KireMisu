#!/usr/bin/env python3
"""Create test fixtures for filesystem parser testing.

This script creates sample manga files and directories to test the filesystem parser.
It generates CBZ files, folder structures, and sample PDFs for comprehensive testing.
"""

import os
import tempfile
import zipfile
from pathlib import Path

from PIL import Image


def create_sample_image(width=800, height=1200, color=(255, 255, 255)):
    """Create a simple test image."""
    img = Image.new("RGB", (width, height), color=color)
    return img


def create_test_fixtures(fixtures_dir: Path):
    """Create all test fixtures."""
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Create series directories with different structures
    series_dirs = ["One Piece", "Attack on Titan", "Naruto", "Dragon Ball Z"]

    for series in series_dirs:
        series_path = fixtures_dir / series
        series_path.mkdir(exist_ok=True)

        if series == "One Piece":
            # Create CBZ files for chapters
            for i in range(1, 6):
                chapter_name = f"One Piece - Chapter {i:03d}.cbz"
                create_cbz_chapter(series_path / chapter_name, pages=20)

            # Create a cover image
            cover_img = create_sample_image(color=(255, 0, 0))
            cover_img.save(series_path / "cover.jpg")

        elif series == "Attack on Titan":
            # Create volume-based structure with CBZ
            for vol in range(1, 4):
                for ch in range(1, 5):
                    chapter_num = (vol - 1) * 4 + ch
                    chapter_name = f"Vol {vol:02d} Ch {chapter_num:03d} - Attack on Titan.cbz"
                    create_cbz_chapter(series_path / chapter_name, pages=25)

        elif series == "Naruto":
            # Create folder-based chapters with loose images
            for i in range(1, 4):
                chapter_dir = series_path / f"Chapter {i:03d}"
                chapter_dir.mkdir(exist_ok=True)

                # Create sample pages
                for page in range(1, 16):
                    img = create_sample_image(color=(0, 255, 0))
                    img.save(chapter_dir / f"page_{page:03d}.jpg")

        elif series == "Dragon Ball Z":
            # Mixed structure - some CBZ, some folders
            # CBZ chapters
            for i in range(1, 3):
                chapter_name = f"DBZ Chapter {i}.cbz"
                create_cbz_chapter(series_path / chapter_name, pages=18)

            # Folder chapters
            for i in range(3, 5):
                chapter_dir = series_path / f"Chapter {i}"
                chapter_dir.mkdir(exist_ok=True)
                for page in range(1, 20):
                    img = create_sample_image(color=(0, 0, 255))
                    img.save(chapter_dir / f"{page:02d}.png")

    # Create single file series (standalone CBZ/PDF)
    standalone_dir = fixtures_dir / "standalone"
    standalone_dir.mkdir(exist_ok=True)

    # Single CBZ file
    create_cbz_chapter(standalone_dir / "My Hero Academia - Chapter 001.cbz", pages=22)

    # Create test files with edge cases
    edge_cases_dir = fixtures_dir / "edge_cases"
    edge_cases_dir.mkdir(exist_ok=True)

    # Fractional chapter numbers
    create_cbz_chapter(edge_cases_dir / "Test Series" / "Chapter 1.5.cbz", pages=10)
    create_cbz_chapter(edge_cases_dir / "Test Series" / "Chapter 2.5.cbz", pages=12)

    # Various naming patterns
    naming_patterns_dir = edge_cases_dir / "naming_patterns"
    naming_patterns_dir.mkdir(parents=True, exist_ok=True)

    # Different naming conventions
    test_names = [
        "Ch001.cbz",
        "c001.cbz",
        "Chapter_01.cbz",
        "Vol01_Ch001.cbz",
        "Series Name - 001.cbz",
        "001 - Chapter Title.cbz",
    ]

    for name in test_names:
        create_cbz_chapter(naming_patterns_dir / name, pages=15)


def create_cbz_chapter(file_path: Path, pages: int = 20):
    """Create a CBZ file with sample pages."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(file_path, "w") as zf:
        for page_num in range(1, pages + 1):
            # Create temporary image
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                img = create_sample_image()
                img.save(tmp.name, "JPEG")

                # Add to zip with proper naming
                zf.write(tmp.name, f"page_{page_num:03d}.jpg")

                # Clean up temp file
                os.unlink(tmp.name)


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent / "manga-samples"
    create_test_fixtures(fixtures_dir)
    print(f"Test fixtures created in {fixtures_dir}")
