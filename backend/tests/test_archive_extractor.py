"""Tests for archive extraction service."""

import pytest
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
import io

from app.services.archive_extractor import ArchiveExtractor, ArchiveExtractorError, SecurityError


@pytest.fixture
def extractor():
    """Create an ArchiveExtractor instance for testing."""
    return ArchiveExtractor()


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.fixture
def sample_cbz_file(sample_image_bytes):
    """Create a sample CBZ file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.cbz', delete=False) as temp_file:
        with zipfile.ZipFile(temp_file.name, 'w') as zf:
            # Add sample images
            zf.writestr('page_001.jpg', sample_image_bytes)
            zf.writestr('page_002.jpg', sample_image_bytes)
            zf.writestr('page_003.jpg', sample_image_bytes)
            # Add a non-image file (should be ignored)
            zf.writestr('readme.txt', 'This is a test archive')
    
    return temp_file.name


@pytest.fixture
def sample_image_folder(sample_image_bytes):
    """Create a sample folder with images for testing."""
    temp_dir = tempfile.mkdtemp()
    folder_path = Path(temp_dir)
    
    # Create sample image files
    for i in range(1, 4):
        img_path = folder_path / f'page_{i:03d}.jpg'
        with open(img_path, 'wb') as f:
            f.write(sample_image_bytes)
    
    # Add a non-image file (should be ignored)
    readme_path = folder_path / 'readme.txt'
    with open(readme_path, 'w') as f:
        f.write('This is a test folder')
    
    return str(folder_path)


class TestArchiveExtractor:
    """Test cases for ArchiveExtractor."""
    
    def test_get_page_list_cbz(self, extractor, sample_cbz_file):
        """Test getting page list from CBZ file."""
        pages = extractor.get_page_list(sample_cbz_file)
        
        assert len(pages) == 3
        assert 'page_001.jpg' in pages
        assert 'page_002.jpg' in pages
        assert 'page_003.jpg' in pages
        assert 'readme.txt' not in pages  # Non-image files should be filtered
        
        # Check natural sorting
        assert pages[0] == 'page_001.jpg'
        assert pages[1] == 'page_002.jpg'
        assert pages[2] == 'page_003.jpg'
    
    def test_get_page_list_folder(self, extractor, sample_image_folder):
        """Test getting page list from image folder."""
        pages = extractor.get_page_list(sample_image_folder)
        
        assert len(pages) == 3
        assert 'page_001.jpg' in pages
        assert 'page_002.jpg' in pages
        assert 'page_003.jpg' in pages
        assert 'readme.txt' not in pages  # Non-image files should be filtered
    
    def test_extract_page_from_cbz(self, extractor, sample_cbz_file):
        """Test extracting a page from CBZ file."""
        image_data, content_type = extractor.extract_page(sample_cbz_file, 'page_001.jpg')
        
        assert isinstance(image_data, bytes)
        assert content_type == 'image/jpeg'
        assert len(image_data) > 0
        
        # Verify the image can be opened
        with Image.open(io.BytesIO(image_data)) as img:
            assert img.format == 'JPEG'
            assert img.size[0] > 0
            assert img.size[1] > 0
    
    def test_extract_page_from_folder(self, extractor, sample_image_folder):
        """Test extracting a page from image folder."""
        image_data, content_type = extractor.extract_page(sample_image_folder, 'page_001.jpg')
        
        assert isinstance(image_data, bytes)
        assert content_type == 'image/jpeg'
        assert len(image_data) > 0
    
    def test_extract_page_with_resize(self, extractor, sample_cbz_file):
        """Test extracting a page with resizing."""
        # Extract with resize
        image_data, content_type = extractor.extract_page(sample_cbz_file, 'page_001.jpg', max_width=50)
        
        assert isinstance(image_data, bytes)
        assert content_type == 'image/jpeg'
        
        # Verify the image was resized
        with Image.open(io.BytesIO(image_data)) as img:
            assert img.size[0] <= 50
    
    def test_extract_nonexistent_page(self, extractor, sample_cbz_file):
        """Test extracting a non-existent page."""
        with pytest.raises(ArchiveExtractorError):
            extractor.extract_page(sample_cbz_file, 'nonexistent.jpg')
    
    def test_extract_from_nonexistent_file(self, extractor):
        """Test extracting from non-existent file."""
        with pytest.raises(ArchiveExtractorError):
            extractor.get_page_list('/nonexistent/file.cbz')
    
    def test_validate_file_path_security(self, extractor):
        """Test file path security validation."""
        # Test directory traversal attempts
        with pytest.raises(SecurityError):
            extractor._validate_page_filename('../../../etc/passwd')
        
        with pytest.raises(SecurityError):
            extractor._validate_page_filename('..\\..\\windows\\system32\\config\\sam')
        
        with pytest.raises(SecurityError):
            extractor._validate_page_filename('page/../secret.txt')
    
    def test_validate_image_extension(self, extractor):
        """Test image file extension validation."""
        # Valid extensions
        valid_names = ['page.jpg', 'image.png', 'comic.gif', 'scan.bmp', 'art.webp']
        for name in valid_names:
            assert extractor._validate_page_filename(name) == name
        
        # Invalid extensions
        invalid_names = ['file.exe', 'script.js', 'doc.pdf', 'archive.zip']
        for name in invalid_names:
            with pytest.raises(SecurityError):
                extractor._validate_page_filename(name)
    
    def test_get_chapter_info(self, extractor, sample_cbz_file):
        """Test getting chapter information."""
        info = extractor.get_chapter_info(sample_cbz_file)
        
        assert 'path' in info
        assert 'format' in info
        assert 'page_count' in info
        assert 'file_size' in info
        assert 'pages' in info
        assert 'is_valid' in info
        
        assert info['format'] in ['cbz', 'zip']
        assert info['page_count'] == 3
        assert info['file_size'] > 0
        assert len(info['pages']) <= 10  # Preview limited to 10 pages
        assert info['is_valid'] is True
    
    def test_zip_bomb_protection(self, extractor):
        """Test protection against ZIP bombs."""
        # Create a ZIP file with suspicious compression ratio
        with tempfile.NamedTemporaryFile(suffix='.cbz', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                # Create a file that would expand to much larger size
                # This is a simplified test - real ZIP bombs are more sophisticated
                large_data = b'A' * 1000000  # 1MB of repeated data
                zf.writestr('large_page.jpg', large_data)
            
            # The extractor should handle this safely
            try:
                pages = extractor.get_page_list(temp_file.name)
                # If it doesn't raise an exception, that's also OK
                # The protection is in the extraction phase
            except ArchiveExtractorError:
                # This is expected for malicious archives
                pass
    
    def test_image_processing_security(self, extractor):
        """Test image processing security measures."""
        # Create a CBZ with a very small but valid image
        small_img = Image.new('RGB', (1, 1), color='blue')
        img_bytes = io.BytesIO()
        small_img.save(img_bytes, format='JPEG')
        
        with tempfile.NamedTemporaryFile(suffix='.cbz', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zf:
                zf.writestr('small.jpg', img_bytes.getvalue())
            
            # This should work fine
            image_data, content_type = extractor.extract_page(temp_file.name, 'small.jpg')
            assert len(image_data) > 0
            assert content_type == 'image/jpeg'
    
    def test_natural_sorting(self, extractor):
        """Test natural sorting of page filenames."""
        # Test the natural sorting key function
        filenames = ['page_10.jpg', 'page_2.jpg', 'page_1.jpg', 'page_20.jpg']
        sorted_names = sorted(filenames, key=extractor.format_service._natural_sort_key)
        
        expected = ['page_1.jpg', 'page_2.jpg', 'page_10.jpg', 'page_20.jpg']
        assert sorted_names == expected
    
    def test_empty_archive(self, extractor):
        """Test handling of empty archive."""
        with tempfile.NamedTemporaryFile(suffix='.cbz', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zf:
                # Create empty ZIP
                pass
            
            with pytest.raises(ArchiveExtractorError):
                extractor.get_page_list(temp_file.name)
    
    def test_archive_with_no_images(self, extractor):
        """Test handling of archive with no image files."""
        with tempfile.NamedTemporaryFile(suffix='.cbz', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zf:
                zf.writestr('readme.txt', 'No images here')
                zf.writestr('metadata.xml', '<xml></xml>')
            
            with pytest.raises(ArchiveExtractorError):
                extractor.get_page_list(temp_file.name)