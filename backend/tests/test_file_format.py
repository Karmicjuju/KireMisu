"""Tests for file format detection functionality."""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, mock_open

from app.services.file_format import FileFormatService, SupportedFormat, FileFormatInfo


class TestFileFormatService:
    """Test file format detection service."""

    @pytest.fixture
    def service(self):
        """Create file format service instance."""
        return FileFormatService()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_get_supported_formats(self, service):
        """Test getting list of supported formats."""
        formats = service.get_supported_formats()
        
        assert len(formats) == 6  # CBZ, CBR, PDF, ZIP, RAR, FOLDER
        format_names = [f['format'] for f in formats]
        assert 'cbz' in format_names
        assert 'cbr' in format_names
        assert 'pdf' in format_names
        assert 'zip' in format_names
        assert 'rar' in format_names
        assert 'folder' in format_names

    def test_detect_format_nonexistent_file(self, service):
        """Test format detection for non-existent file."""
        result = service.detect_format("/nonexistent/file.cbz")
        
        assert result.is_supported is False
        assert result.is_valid is False
        assert result.error_message == "File or directory does not exist"

    def test_detect_format_by_extension_cbz(self, service):
        """Test format detection by file extension."""
        # We'll mock the file operations since we're testing logic, not file I/O
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            
            # Mock file reading for ZIP header
            with patch('builtins.open', mock_open(read_data=b'PK\x03\x04' + b'\x00' * 28)):
                result = service.detect_format("/test/manga.cbz")
                
                assert result.format_type == SupportedFormat.CBZ
                assert result.is_supported is True

    def test_detect_format_by_magic_number_pdf(self, service):
        """Test PDF detection by magic number."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            
            # Mock file reading for PDF header
            with patch('builtins.open', mock_open(read_data=b'%PDF-1.4' + b'\x00' * 24)):
                result = service.detect_format("/test/document.pdf")
                
                assert result.format_type == SupportedFormat.PDF
                assert result.is_supported is True

    def test_detect_format_folder_with_images(self, service, temp_dir):
        """Test format detection for folder with image files."""
        # Create test image files
        temp_path = Path(temp_dir)
        
        # Create fake image files
        (temp_path / "page01.jpg").touch()
        (temp_path / "page02.jpg").touch()
        (temp_path / "page03.png").touch()
        
        # Mock image validation to return True
        with patch.object(service, '_is_valid_image_file', return_value=True):
            result = service.detect_format(temp_dir)
            
            assert result.format_type == SupportedFormat.FOLDER
            assert result.is_supported is True
            assert result.is_valid is True
            assert result.has_images is True
            assert result.page_count == 3

    def test_detect_format_folder_no_images(self, service, temp_dir):
        """Test format detection for folder without images."""
        # Create non-image files
        temp_path = Path(temp_dir)
        (temp_path / "readme.txt").touch()
        (temp_path / "metadata.xml").touch()
        
        result = service.detect_format(temp_dir)
        
        assert result.is_supported is False
        assert result.error_message == "No image files found in directory"

    def test_validate_zip_archive_success(self, service, temp_dir):
        """Test successful ZIP archive validation."""
        zip_path = Path(temp_dir) / "test.cbz"
        
        # Create a valid ZIP file with image files
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("page01.jpg", b"fake_jpg_data")
            zf.writestr("page02.png", b"fake_png_data")
        
        # Mock image header validation
        with patch.object(service, '_is_valid_image_header', return_value=True):
            result = service.detect_format(str(zip_path))
            
            assert result.format_type == SupportedFormat.CBZ
            assert result.is_supported is True
            assert result.is_valid is True
            assert result.page_count == 2
            assert result.has_images is True

    def test_validate_zip_archive_zip_bomb_protection(self, service):
        """Test ZIP bomb protection."""
        result = FileFormatInfo("/fake/path.zip")
        
        # Mock a ZIP file with suspicious compression ratio
        with patch('zipfile.ZipFile') as mock_zip:
            mock_zip.return_value.__enter__.return_value.testzip.return_value = None
            
            # Create mock file info with high compression ratio
            mock_file_info = type('MockFileInfo', (), {
                'is_dir': lambda: False,
                'compress_size': 1000,  # 1KB compressed
                'file_size': 200000000,  # 200MB uncompressed (200:1 ratio)
                'filename': 'suspicious.txt'
            })()
            
            mock_zip.return_value.__enter__.return_value.infolist.return_value = [mock_file_info]
            
            service._validate_zip_archive(result, Path("/fake/path.zip"))
            
            assert result.is_corrupted is True
            assert "Suspicious compression ratio" in result.error_message

    def test_validate_zip_archive_size_limit(self, service):
        """Test ZIP archive size limit protection."""
        result = FileFormatInfo("/fake/path.zip")
        
        with patch('zipfile.ZipFile') as mock_zip:
            mock_zip.return_value.__enter__.return_value.testzip.return_value = None
            
            # Create mock file info exceeding size limit
            mock_file_info = type('MockFileInfo', (), {
                'is_dir': lambda: False,
                'compress_size': 1000000,  # 1MB compressed
                'file_size': 200000000,   # 200MB uncompressed (exceeds 100MB limit)
                'filename': 'large_file.txt'
            })()
            
            mock_zip.return_value.__enter__.return_value.infolist.return_value = [mock_file_info]
            
            service._validate_zip_archive(result, Path("/fake/path.zip"))
            
            assert result.is_corrupted is True
            assert "too large" in result.error_message

    def test_image_header_validation_jpeg(self, service):
        """Test JPEG image header validation."""
        jpeg_header = b'\xff\xd8\xff\xe0'  # JPEG header
        result = service._is_valid_image_header(jpeg_header)
        assert result is True

    def test_image_header_validation_png(self, service):
        """Test PNG image header validation."""
        png_header = b'\x89PNG\r\n\x1a\n'  # PNG header
        result = service._is_valid_image_header(png_header)
        assert result is True

    def test_image_header_validation_invalid(self, service):
        """Test invalid image header."""
        invalid_header = b'NOT_AN_IMAGE'
        result = service._is_valid_image_header(invalid_header)
        assert result is False

    def test_natural_sort_key(self, service):
        """Test natural sorting for file names."""
        filenames = ["page1.jpg", "page10.jpg", "page2.jpg", "page11.jpg"]
        sorted_names = sorted(filenames, key=service._natural_sort_key)
        expected = ["page1.jpg", "page2.jpg", "page10.jpg", "page11.jpg"]
        assert sorted_names == expected

    def test_batch_analyze_multiple_files(self, service):
        """Test batch analysis of multiple files."""
        file_paths = ["/fake/file1.cbz", "/fake/file2.pdf", "/nonexistent/file.rar"]
        
        # Mock individual analysis results
        mock_results = [
            FileFormatInfo("/fake/file1.cbz", SupportedFormat.CBZ, True, True),
            FileFormatInfo("/fake/file2.pdf", SupportedFormat.PDF, True, True),
            FileFormatInfo("/nonexistent/file.rar", error_message="File not found")
        ]
        
        with patch.object(service, 'detect_format', side_effect=mock_results):
            results = service.batch_analyze(file_paths)
            
            assert len(results) == 3
            assert results[0].format_type == SupportedFormat.CBZ
            assert results[1].format_type == SupportedFormat.PDF
            assert results[2].error_message == "File not found"

    def test_rar_validation_basic(self, service):
        """Test basic RAR file validation."""
        result = FileFormatInfo("/fake/path.rar")
        
        with patch('builtins.open', mock_open(read_data=b'Rar!\x1a\x07\x00' + b'\x00' * 25)):
            service._validate_rar_archive(result, Path("/fake/path.rar"))
            
            assert result.is_valid is True
            assert result.has_images is True  # Assumed for RAR files
            assert "basic" in result.metadata.get('validation_level', '')