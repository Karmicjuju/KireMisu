"""Tests for library scanning functionality."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from app.services.library_scan import LibraryScanService, ScanProgress
from app.models.storage_path import StoragePath


class TestScanProgress:
    """Test scan progress tracking."""

    def test_scan_progress_initialization(self):
        """Test scan progress initialization."""
        scan_id = "test_scan_123"
        progress = ScanProgress(scan_id)
        
        assert progress.scan_id == scan_id
        assert progress.status == "running"
        assert progress.total_files == 0
        assert progress.processed_files == 0
        assert progress.new_series == 0
        assert progress.errors == []

    def test_scan_progress_to_dict(self):
        """Test scan progress serialization."""
        progress = ScanProgress("test_scan")
        progress.total_files = 100
        progress.processed_files = 50
        progress.new_series = 5
        
        result = progress.to_dict()
        
        assert result['scan_id'] == "test_scan"
        assert result['status'] == "running"
        assert result['progress']['total_files'] == 100
        assert result['progress']['processed_files'] == 50
        assert result['progress']['percentage'] == 50.0
        assert result['results']['new_series'] == 5

    def test_scan_progress_add_error(self):
        """Test adding errors to scan progress."""
        progress = ScanProgress("test_scan")
        progress.add_error("Test error", "/test/path")
        
        assert len(progress.errors) == 1
        assert progress.errors[0]['message'] == "Test error"
        assert progress.errors[0]['path'] == "/test/path"

    def test_scan_progress_add_warning(self):
        """Test adding warnings to scan progress."""
        progress = ScanProgress("test_scan")
        progress.add_warning("Test warning", "/test/path")
        
        assert len(progress.warnings) == 1
        assert progress.warnings[0]['message'] == "Test warning"
        assert progress.warnings[0]['path'] == "/test/path"

    def test_scan_progress_complete(self):
        """Test completing a scan."""
        progress = ScanProgress("test_scan")
        progress.complete("completed")
        
        assert progress.status == "completed"
        assert progress.end_time is not None


class TestLibraryScanService:
    """Test library scanning service."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        mock_db = AsyncMock()
        return mock_db

    @pytest.fixture
    def service(self, mock_db):
        """Create library scan service."""
        return LibraryScanService(mock_db)

    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service."""
        return AsyncMock()

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.MAX_SCAN_DURATION == 3600
        assert service.MAX_FILES_PER_SCAN == 10000
        assert service.MAX_CONCURRENT_SCANS == 3

    @pytest.mark.asyncio
    async def test_start_manual_scan_success(self, service):
        """Test starting a manual scan successfully."""
        # Mock storage paths
        mock_storage_path = Mock()
        mock_storage_path.id = 1
        mock_storage_path.path = "/test/manga"
        mock_storage_path.name = "Test Library"
        
        with patch.object(service.storage_service, 'get_all', return_value=[mock_storage_path]):
            scan_id = await service.start_manual_scan()
            
            assert scan_id is not None
            assert scan_id.startswith("scan_")
            assert scan_id in service._active_scans

    @pytest.mark.asyncio
    async def test_start_manual_scan_no_paths(self, service):
        """Test starting a scan with no storage paths."""
        with patch.object(service.storage_service, 'get_all', return_value=[]):
            scan_id = await service.start_manual_scan()
            
            progress = service.get_scan_progress(scan_id)
            assert progress.status == "failed"
            assert len(progress.errors) > 0

    @pytest.mark.asyncio
    async def test_start_manual_scan_concurrent_limit(self, service):
        """Test concurrent scan limit enforcement."""
        # Create maximum number of active scans
        for i in range(service.MAX_CONCURRENT_SCANS):
            scan_id = f"existing_scan_{i}"
            service._active_scans[scan_id] = ScanProgress(scan_id)
        
        # Try to start another scan
        scan_id = await service.start_manual_scan()
        progress = service.get_scan_progress(scan_id)
        
        assert progress.status == "failed"
        assert "Maximum concurrent scans limit reached" in progress.errors[0]['message']

    def test_get_scan_progress_existing(self, service):
        """Test getting progress for existing scan."""
        scan_id = "test_scan"
        expected_progress = ScanProgress(scan_id)
        service._active_scans[scan_id] = expected_progress
        
        result = service.get_scan_progress(scan_id)
        assert result == expected_progress

    def test_get_scan_progress_nonexistent(self, service):
        """Test getting progress for non-existent scan."""
        result = service.get_scan_progress("nonexistent_scan")
        assert result is None

    def test_get_active_scans(self, service):
        """Test getting all active scans."""
        # Create test scans
        scan1 = ScanProgress("scan1")
        scan2 = ScanProgress("scan2")
        service._active_scans = {"scan1": scan1, "scan2": scan2}
        
        active_scans = service.get_active_scans()
        
        assert len(active_scans) == 2
        assert any(scan['scan_id'] == "scan1" for scan in active_scans)
        assert any(scan['scan_id'] == "scan2" for scan in active_scans)

    @pytest.mark.asyncio
    async def test_discover_files(self, service):
        """Test file discovery in storage path."""
        # Mock os.walk to return test files
        mock_walk_data = [
            ("/manga", ["series1", "series2"], ["file1.cbz"]),
            ("/manga/series1", [], ["chapter1.cbz", "chapter2.cbz", "image.jpg", "image.png", "image.gif"]),
            ("/manga/series2", [], ["vol1.pdf", "readme.txt"]),
        ]
        
        with patch('os.walk', return_value=mock_walk_data):
            files = await service._discover_files("/manga")
            
            # Should find CBZ files and PDF files, plus one folder with enough images
            assert len(files) >= 3  # At least the archives
            assert "/manga/file1.cbz" in files
            assert "/manga/series1/chapter1.cbz" in files
            assert "/manga/series1/chapter2.cbz" in files
            assert "/manga/series2/vol1.pdf" in files
            # series1 folder should be included as it has 3+ images
            assert "/manga/series1" in files

    def test_extract_metadata_from_path_file(self, service):
        """Test metadata extraction from file path."""
        file_path = "/manga/Attack on Titan/Chapter 001.cbz"
        
        series_info, chapter_info = service._extract_metadata_from_path(file_path)
        
        assert series_info['title'] == "Attack on Titan"
        assert chapter_info['number'] == 1.0

    def test_extract_metadata_from_path_folder(self, service):
        """Test metadata extraction from folder path."""
        folder_path = "/manga/One Piece"
        
        series_info, chapter_info = service._extract_metadata_from_path(folder_path)
        
        assert series_info['title'] == "One Piece"
        assert chapter_info['number'] == 1.0  # Default for folders

    def test_extract_chapter_number_patterns(self, service):
        """Test chapter number extraction from various filename patterns."""
        test_cases = [
            ("Chapter 001.cbz", 1.0),
            ("Ch 123.cbz", 123.0),
            ("Vol 1 Ch 05.cbz", 5.0),
            ("One Piece - 001.cbz", 1.0),
            ("attack_on_titan_042.cbz", 42.0),
            ("chapter-15.5.cbz", 15.5),
            ("no_numbers.cbz", 1.0),  # Default fallback
        ]
        
        for filename, expected in test_cases:
            result = service._extract_chapter_number(filename)
            assert result == expected, f"Failed for {filename}, got {result}, expected {expected}"

    def test_clean_title(self, service):
        """Test title cleaning functionality."""
        test_cases = [
            ("Attack on Titan [Scanlator]", "Attack on Titan"),
            ("One Piece (2023)", "One Piece"),
            ("Naruto_Chapter_001", "Naruto Chapter 001"),
            ("My_Hero_Academia.cbz", "My Hero Academia"),
            ("   Spaced   Title   ", "Spaced Title"),
            ("", "Untitled"),
            (None, "Untitled"),
        ]
        
        for input_title, expected in test_cases:
            result = service._clean_title(input_title)
            assert result == expected, f"Failed for '{input_title}', got '{result}', expected '{expected}'"

    def test_cancel_scan_success(self, service):
        """Test successful scan cancellation."""
        scan_id = "test_scan"
        progress = ScanProgress(scan_id)
        service._active_scans[scan_id] = progress
        
        result = service.cancel_scan(scan_id)
        
        assert result is True
        assert progress.status == "cancelled"

    def test_cancel_scan_nonexistent(self, service):
        """Test cancelling non-existent scan."""
        result = service.cancel_scan("nonexistent_scan")
        assert result is False

    def test_cancel_scan_already_completed(self, service):
        """Test cancelling already completed scan."""
        scan_id = "completed_scan"
        progress = ScanProgress(scan_id)
        progress.complete("completed")
        service._active_scans[scan_id] = progress
        
        result = service.cancel_scan(scan_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_perform_scan_file_limit_exceeded(self, service):
        """Test scan stops when file limit is exceeded."""
        progress = ScanProgress("test_scan")
        service._active_scans["test_scan"] = progress
        
        mock_storage_path = Mock()
        mock_storage_path.id = 1
        mock_storage_path.path = "/test"
        
        # Mock file discovery to return too many files
        with patch.object(service, '_discover_files', return_value=['file'] * (service.MAX_FILES_PER_SCAN + 1)):
            await service._perform_scan(progress, [mock_storage_path], False)
            
            assert progress.status == "failed"
            assert "exceeds maximum limit" in progress.errors[0]['message']

    @pytest.mark.asyncio 
    async def test_process_file_format_detection_integration(self, service):
        """Test file processing integrates with format detection."""
        progress = ScanProgress("test_scan")
        mock_storage_path = Mock()
        mock_storage_path.id = 1
        
        # Mock format service to return valid CBZ
        mock_format_info = Mock()
        mock_format_info.is_supported = True
        mock_format_info.is_valid = True
        mock_format_info.is_corrupted = False
        mock_format_info.format_type = "cbz"
        
        with patch.object(service.format_service, 'detect_format', return_value=mock_format_info), \
             patch.object(service, '_extract_metadata_from_path', return_value=({}, {})), \
             patch.object(service, '_find_or_create_series', return_value=Mock()):
            
            await service._process_file(progress, mock_storage_path, "/test/file.cbz", False)
            
            assert progress.supported_files == 1
            assert progress.corrupted_files == 0