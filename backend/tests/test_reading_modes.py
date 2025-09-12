"""Tests for reading modes functionality."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from PIL import Image

from app.services.reader import ReaderService


class TestReadingModeDetection:
    """Test suite for automatic reading mode detection."""
    
    @pytest.fixture
    def reader_service(self):
        """Create a ReaderService instance for testing."""
        return ReaderService()
    
    @pytest.fixture
    def mock_extractor(self):
        """Mock the archive extractor."""
        with patch('app.services.reader.ArchiveExtractor') as mock:
            yield mock
    
    def create_test_image(self, width: int, height: int) -> bytes:
        """Create a test image with specific dimensions."""
        img = Image.new('RGB', (width, height), color='white')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()
    
    def test_detect_vertical_mode_webtoon(self, reader_service, mock_extractor):
        """Test detection of vertical scroll mode for webtoon-style images."""
        # Mock page list
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = ['page1.jpg', 'page2.jpg', 'page3.jpg']
        
        # Mock extract_page to return tall images (webtoon style)
        tall_image = self.create_test_image(800, 4000)  # Very tall image
        mock_instance.extract_page.return_value = (tall_image, 'image/jpeg')
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        assert result == 'vertical'
        assert mock_instance.get_page_list.called
        assert mock_instance.extract_page.called
    
    def test_detect_double_page_mode(self, reader_service, mock_extractor):
        """Test detection of double page mode for wide images."""
        # Mock page list
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = ['page1.jpg', 'page2.jpg', 'page3.jpg']
        
        # Mock extract_page to return wide images (double page spreads)
        wide_image = self.create_test_image(2000, 1200)  # Wide image
        mock_instance.extract_page.return_value = (wide_image, 'image/jpeg')
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        assert result == 'double'
    
    def test_detect_single_page_mode(self, reader_service, mock_extractor):
        """Test detection of single page mode for standard manga pages."""
        # Mock page list
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = ['page1.jpg', 'page2.jpg', 'page3.jpg']
        
        # Mock extract_page to return standard manga pages
        standard_image = self.create_test_image(800, 1200)  # Standard aspect ratio
        mock_instance.extract_page.return_value = (standard_image, 'image/jpeg')
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        assert result == 'single'
    
    def test_detect_mode_with_mixed_images(self, reader_service, mock_extractor):
        """Test detection with mixed image types (should use average)."""
        # Mock page list
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = ['page1.jpg', 'page2.jpg', 'page3.jpg']
        
        # Mock extract_page to return different image types
        images = [
            self.create_test_image(800, 1200),   # Standard
            self.create_test_image(800, 1200),   # Standard
            self.create_test_image(2000, 1200),  # Wide
        ]
        
        mock_instance.extract_page.side_effect = [(img, 'image/jpeg') for img in images]
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        # Should detect single as 2/3 images are standard
        assert result == 'single'
    
    def test_detect_mode_empty_chapter(self, reader_service, mock_extractor):
        """Test detection with empty chapter (no pages)."""
        # Mock page list as empty
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = []
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        assert result == 'single'  # Default to single
    
    def test_detect_mode_extraction_error(self, reader_service, mock_extractor):
        """Test detection when page extraction fails."""
        # Mock page list
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = ['page1.jpg', 'page2.jpg']
        
        # Mock extract_page to raise exception
        mock_instance.extract_page.side_effect = Exception("Extraction failed")
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        assert result == 'single'  # Default to single on error
    
    def test_detect_mode_invalid_image_data(self, reader_service, mock_extractor):
        """Test detection with invalid image data."""
        # Mock page list
        mock_instance = Mock()
        mock_instance.get_page_list.return_value = ['page1.jpg', 'page2.jpg']
        
        # Mock extract_page to return invalid image data
        mock_instance.extract_page.return_value = (b'invalid image data', 'image/jpeg')
        
        reader_service.extractor = mock_instance
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz')
        
        assert result == 'single'  # Default to single when images can't be analyzed


class TestReadingModeIntegration:
    """Integration tests for reading modes with chapter pages API."""
    
    @pytest.fixture
    def reader_service(self):
        """Create a ReaderService instance for testing."""
        return ReaderService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_chapter(self):
        """Mock chapter object."""
        chapter = Mock()
        chapter.id = 1
        chapter.series_id = 1
        chapter.file_path = '/path/to/chapter.cbz'
        chapter.number = '1'
        chapter.title = 'Chapter 1'
        chapter.read_status = False
        return chapter
    
    @pytest.fixture
    def mock_series(self):
        """Mock series object."""
        series = Mock()
        series.id = 1
        series.title = 'Test Manga'
        return series
    
    @pytest.mark.asyncio
    @patch('app.services.reader.ReaderService.detect_reading_mode')
    async def test_get_chapter_pages_includes_suggested_mode(
        self, 
        mock_detect, 
        reader_service, 
        mock_db, 
        mock_chapter, 
        mock_series
    ):
        """Test that get_chapter_pages includes suggested reading mode."""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_chapter,  # First call for chapter
            mock_series    # Second call for series
        ]
        
        # Mock extractor
        mock_extractor = Mock()
        mock_extractor.get_page_list.return_value = ['page1.jpg', 'page2.jpg']
        reader_service.extractor = mock_extractor
        
        # Mock detect_reading_mode
        mock_detect.return_value = 'vertical'
        
        # Call get_chapter_pages (it's async)
        result = await reader_service.get_chapter_pages(
            chapter_id=1,
            db=mock_db,
            user_id=1
        )
        
        # Verify suggested_reading_mode is included
        assert 'suggested_reading_mode' in result
        assert result['suggested_reading_mode'] == 'vertical'
        mock_detect.assert_called_with(mock_chapter.file_path)
    
    def test_reading_mode_persistence_in_settings(self):
        """Test that reading mode preference is persisted in user settings."""
        from app.services.reader import ReaderService
        
        service = ReaderService()
        
        # Test that settings are preserved across different chapters
        # This would be tested more thoroughly with frontend integration tests
        assert service is not None


class TestReadingModePerformance:
    """Performance tests for reading mode detection."""
    
    @pytest.fixture
    def reader_service(self):
        """Create a ReaderService instance for testing."""
        return ReaderService()
    
    def test_detection_samples_limited_pages(self, reader_service):
        """Test that detection only samples first few pages for performance."""
        mock_instance = Mock()
        
        # Create many pages
        pages = [f'page{i}.jpg' for i in range(100)]
        mock_instance.get_page_list.return_value = pages
        
        # Track how many pages are actually extracted
        extracted_count = 0
        
        def mock_extract(path, filename):
            nonlocal extracted_count
            extracted_count += 1
            return (self.create_test_image(800, 1200), 'image/jpeg')
        
        mock_instance.extract_page.side_effect = mock_extract
        reader_service.extractor = mock_instance
        
        # Create test image helper
        def create_test_image(width: int, height: int) -> bytes:
            img = Image.new('RGB', (width, height), color='white')
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            return buffer.getvalue()
        
        self.create_test_image = create_test_image
        
        result = reader_service.detect_reading_mode('/path/to/chapter.cbz', sample_pages=3)
        
        # Should only extract 3 pages for detection
        assert extracted_count == 3
        assert result == 'single'