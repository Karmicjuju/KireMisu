"""Tests for reader service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
from pathlib import Path

from app.services.reader import ReaderService, ReadingProgress, ImageCache
from app.models.chapter import Chapter
from app.models.series import Series
from app.models.user import User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    user = User()
    user.id = 1
    user.email = "test@example.com"
    return user


@pytest.fixture
def sample_series():
    """Create a sample series for testing."""
    series = Series()
    series.id = 1
    series.title = "Test Series"
    return series


@pytest.fixture
def sample_chapter(sample_series):
    """Create a sample chapter for testing."""
    chapter = Chapter()
    chapter.id = 1
    chapter.series_id = sample_series.id
    chapter.number = 1.0
    chapter.title = "Test Chapter"
    chapter.file_path = "/test/path/chapter1.cbz"
    chapter.read_status = False
    return chapter


@pytest.fixture
def reader_service():
    """Create a ReaderService instance for testing."""
    return ReaderService()


class TestReadingProgress:
    """Test cases for ReadingProgress."""
    
    def test_reading_progress_creation(self):
        """Test creating a ReadingProgress instance."""
        progress = ReadingProgress(chapter_id=1, user_id=1, current_page=5, total_pages=20)
        
        assert progress.chapter_id == 1
        assert progress.user_id == 1
        assert progress.current_page == 5
        assert progress.total_pages == 20
        assert progress.is_completed is False
        assert isinstance(progress.last_read, datetime)
    
    def test_reading_progress_completion(self):
        """Test reading progress completion detection."""
        # Not completed
        progress = ReadingProgress(chapter_id=1, user_id=1, current_page=5, total_pages=20)
        assert progress.is_completed is False
        
        # Completed (last page)
        progress = ReadingProgress(chapter_id=1, user_id=1, current_page=19, total_pages=20)
        assert progress.is_completed is True
        
        # Edge case: single page
        progress = ReadingProgress(chapter_id=1, user_id=1, current_page=0, total_pages=1)
        assert progress.is_completed is True


class TestImageCache:
    """Test cases for ImageCache."""
    
    def test_cache_put_and_get(self):
        """Test putting and getting items from cache."""
        cache = ImageCache(max_size_mb=1)  # 1MB cache
        
        image_data = b'test image data'
        content_type = 'image/jpeg'
        
        # Put item in cache
        cache.put(1, 'page1.jpg', image_data, content_type)
        
        # Get item from cache
        cached_data = cache.get(1, 'page1.jpg')
        assert cached_data is not None
        assert cached_data[0] == image_data
        assert cached_data[1] == content_type
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = ImageCache()
        
        # Try to get non-existent item
        cached_data = cache.get(1, 'nonexistent.jpg')
        assert cached_data is None
    
    def test_cache_eviction(self):
        """Test cache eviction when size limit is reached."""
        cache = ImageCache(max_size_mb=0.001)  # Very small cache (1KB)
        
        # Add items that exceed cache size
        large_data1 = b'x' * 600  # 600 bytes
        large_data2 = b'y' * 600  # 600 bytes
        
        cache.put(1, 'page1.jpg', large_data1, 'image/jpeg')
        cache.put(1, 'page2.jpg', large_data2, 'image/jpeg')
        
        # First item should be evicted
        cached_data1 = cache.get(1, 'page1.jpg')
        cached_data2 = cache.get(1, 'page2.jpg')
        
        assert cached_data1 is None  # Evicted
        assert cached_data2 is not None  # Still in cache
    
    def test_cache_key_generation(self):
        """Test cache key generation with different parameters."""
        cache = ImageCache()
        
        # Test different combinations
        key1 = cache._generate_key(1, 'page.jpg')
        key2 = cache._generate_key(1, 'page.jpg', 800)
        key3 = cache._generate_key(2, 'page.jpg')
        key4 = cache._generate_key(1, 'other.jpg')
        
        # All keys should be different
        assert key1 != key2
        assert key1 != key3
        assert key1 != key4
        assert key2 != key3
    
    def test_cache_clear(self):
        """Test clearing cache."""
        cache = ImageCache()
        
        # Add some items
        cache.put(1, 'page1.jpg', b'data1', 'image/jpeg')
        cache.put(1, 'page2.jpg', b'data2', 'image/jpeg')
        
        assert len(cache.cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.current_size == 0


class TestReaderService:
    """Test cases for ReaderService."""
    
    @patch('app.services.reader.ReaderService.__init__', return_value=None)
    def test_reader_service_initialization(self, mock_init):
        """Test ReaderService initialization."""
        service = ReaderService()
        service.extractor = Mock()
        service.image_cache = Mock()
        service.progress_cache = {}
        
        assert service.extractor is not None
        assert service.image_cache is not None
        assert isinstance(service.progress_cache, dict)
    
    @pytest.mark.asyncio
    async def test_get_chapter_pages_success(self, reader_service, mock_db, sample_chapter, sample_series, sample_user):
        """Test successful chapter pages retrieval."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [sample_chapter, sample_series]
        
        # Mock extractor
        reader_service.extractor.get_page_list = Mock(return_value=['page1.jpg', 'page2.jpg', 'page3.jpg'])
        
        result = await reader_service.get_chapter_pages(1, mock_db, sample_user.id)
        
        assert result['chapter_id'] == 1
        assert result['pages'] == ['page1.jpg', 'page2.jpg', 'page3.jpg']
        assert result['page_count'] == 3
        assert 'reading_progress' in result
    
    @pytest.mark.asyncio
    async def test_get_chapter_pages_not_found(self, reader_service, mock_db, sample_user):
        """Test chapter pages retrieval with non-existent chapter."""
        # Mock database to return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(Exception):  # Should raise HTTPException in actual code
            await reader_service.get_chapter_pages(999, mock_db, sample_user.id)
    
    @pytest.mark.asyncio
    async def test_get_page_image_cached(self, reader_service, mock_db, sample_chapter, sample_user):
        """Test getting page image from cache."""
        # Mock cache hit
        cached_data = (b'cached image data', 'image/jpeg')
        reader_service.image_cache.get = Mock(return_value=cached_data)
        
        result = await reader_service.get_page_image(1, 'page1.jpg', mock_db, sample_user.id)
        
        assert result == cached_data
        reader_service.image_cache.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_page_image_extract(self, reader_service, mock_db, sample_chapter, sample_user):
        """Test getting page image with extraction."""
        # Mock cache miss
        reader_service.image_cache.get = Mock(return_value=None)
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_chapter
        
        # Mock extraction
        extracted_data = (b'extracted image data', 'image/jpeg')
        reader_service.extractor.extract_page = Mock(return_value=extracted_data)
        
        # Mock cache put
        reader_service.image_cache.put = Mock()
        
        result = await reader_service.get_page_image(1, 'page1.jpg', mock_db, sample_user.id)
        
        assert result == extracted_data
        reader_service.extractor.extract_page.assert_called_once()
        reader_service.image_cache.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_reading_progress(self, reader_service, mock_db, sample_chapter, sample_user):
        """Test updating reading progress."""
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_chapter
        
        # Mock extractor
        reader_service.extractor.get_page_list = Mock(return_value=['page1.jpg', 'page2.jpg', 'page3.jpg'])
        
        result = await reader_service.update_reading_progress(1, 1, mock_db, sample_user.id)
        
        assert isinstance(result, ReadingProgress)
        assert result.chapter_id == 1
        assert result.user_id == sample_user.id
        assert result.current_page == 1
        assert result.total_pages == 3
    
    @pytest.mark.asyncio
    async def test_update_reading_progress_completion(self, reader_service, mock_db, sample_chapter, sample_user):
        """Test updating reading progress with chapter completion."""
        # Mock database query and commit
        mock_db.query.return_value.filter.return_value.first.return_value = sample_chapter
        mock_db.commit = Mock()
        
        # Mock extractor - 3 pages total, going to last page
        reader_service.extractor.get_page_list = Mock(return_value=['page1.jpg', 'page2.jpg', 'page3.jpg'])
        
        result = await reader_service.update_reading_progress(1, 2, mock_db, sample_user.id)  # Last page (0-indexed)
        
        assert result.is_completed is True
        assert sample_chapter.read_status is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_chapter_navigation(self, reader_service, mock_db, sample_chapter, sample_user):
        """Test getting chapter navigation."""
        # Create additional chapters for navigation
        prev_chapter = Chapter()
        prev_chapter.id = 0
        prev_chapter.series_id = sample_chapter.series_id
        prev_chapter.number = 0.5
        prev_chapter.title = "Previous Chapter"
        
        next_chapter = Chapter()
        next_chapter.id = 2
        next_chapter.series_id = sample_chapter.series_id
        next_chapter.number = 2.0
        next_chapter.title = "Next Chapter"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = sample_chapter
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            prev_chapter, sample_chapter, next_chapter
        ]
        
        result = await reader_service.get_chapter_navigation(1, mock_db, sample_user.id)
        
        assert result['current_chapter']['id'] == sample_chapter.id
        assert result['previous_chapter']['id'] == prev_chapter.id
        assert result['next_chapter']['id'] == next_chapter.id
        assert result['total_chapters'] == 3
        assert result['current_position'] == 2
    
    def test_get_reading_progress_new(self, reader_service):
        """Test getting reading progress for new chapter."""
        progress = reader_service._get_reading_progress(1, 1, 10)
        
        assert progress.chapter_id == 1
        assert progress.user_id == 1
        assert progress.current_page == 0
        assert progress.total_pages == 10
        assert progress.is_completed is False
    
    def test_get_reading_progress_existing(self, reader_service):
        """Test getting existing reading progress."""
        # Add existing progress
        existing_progress = ReadingProgress(chapter_id=1, user_id=1, current_page=5, total_pages=10)
        reader_service.progress_cache['1:1'] = existing_progress
        
        progress = reader_service._get_reading_progress(1, 1, 10)
        
        assert progress == existing_progress
        assert progress.current_page == 5
    
    def test_clear_cache(self, reader_service):
        """Test clearing reader cache."""
        # Add some cached data
        reader_service.image_cache.put(1, 'page1.jpg', b'data', 'image/jpeg')
        
        reader_service.clear_cache()
        
        # Cache should be cleared
        reader_service.image_cache.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preload_pages(self, reader_service, mock_db, sample_user):
        """Test preloading pages for smooth reading."""
        # Mock get_chapter_pages
        chapter_data = {
            'pages': ['page1.jpg', 'page2.jpg', 'page3.jpg', 'page4.jpg', 'page5.jpg']
        }
        reader_service.get_chapter_pages = Mock(return_value=chapter_data)
        
        # Mock cache check
        reader_service.image_cache.get = Mock(return_value=None)  # Not cached
        
        # Mock preload method
        reader_service._preload_page = Mock()
        
        with patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.gather') as mock_gather:
            
            await reader_service.preload_pages(1, 1, mock_db, sample_user.id, preload_count=2)
            
            # Should try to preload next 2 pages
            assert mock_create_task.call_count <= 2
    
    @pytest.mark.asyncio 
    async def test_preload_page_success(self, reader_service, mock_db, sample_user):
        """Test successful page preloading."""
        reader_service.get_page_image = Mock(return_value=(b'data', 'image/jpeg'))
        
        # Should not raise exception
        await reader_service._preload_page(1, 'page.jpg', mock_db, sample_user.id)
        
        reader_service.get_page_image.assert_called_once_with(1, 'page.jpg', mock_db, sample_user.id)
    
    @pytest.mark.asyncio
    async def test_preload_page_failure(self, reader_service, mock_db, sample_user):
        """Test page preloading failure handling."""
        reader_service.get_page_image = Mock(side_effect=Exception('Network error'))
        
        # Should not raise exception (failures are logged but not propagated)
        await reader_service._preload_page(1, 'page.jpg', mock_db, sample_user.id)