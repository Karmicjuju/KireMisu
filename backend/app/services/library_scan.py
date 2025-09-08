"""Service layer for library scanning and indexing."""

import os
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.storage_path import StoragePath
from app.models.series import Series
from app.models.chapter import Chapter
from app.services.file_format import FileFormatService, FileFormatInfo, SupportedFormat
from app.services.storage import StoragePathService

logger = logging.getLogger(__name__)


class ScanProgress:
    """Track progress of a library scan operation."""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.status = "running"  # running, completed, failed, cancelled
        
        # Progress tracking
        self.total_paths = 0
        self.processed_paths = 0
        self.total_files = 0
        self.processed_files = 0
        
        # Results
        self.new_series = 0
        self.new_chapters = 0
        self.updated_series = 0
        self.removed_series = 0
        self.removed_chapters = 0
        self.errors = []
        self.warnings = []
        
        # File format stats
        self.supported_files = 0
        self.unsupported_files = 0
        self.corrupted_files = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary for serialization."""
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            
        return {
            'scan_id': self.scan_id,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': duration,
            'progress': {
                'total_paths': self.total_paths,
                'processed_paths': self.processed_paths,
                'total_files': self.total_files,
                'processed_files': self.processed_files,
                'percentage': round((self.processed_files / self.total_files * 100) if self.total_files > 0 else 0, 2)
            },
            'results': {
                'new_series': self.new_series,
                'new_chapters': self.new_chapters,
                'updated_series': self.updated_series,
                'removed_series': self.removed_series,
                'removed_chapters': self.removed_chapters
            },
            'file_stats': {
                'supported_files': self.supported_files,
                'unsupported_files': self.unsupported_files,
                'corrupted_files': self.corrupted_files
            },
            'errors': self.errors,
            'warnings': self.warnings
        }

    def add_error(self, message: str, path: Optional[str] = None):
        """Add an error to the scan results."""
        error_entry = {
            'message': message,
            'path': path,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.errors.append(error_entry)
        logger.error(f"Scan {self.scan_id} error: {message} (path: {path})")

    def add_warning(self, message: str, path: Optional[str] = None):
        """Add a warning to the scan results."""
        warning_entry = {
            'message': message,
            'path': path,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.warnings.append(warning_entry)
        logger.warning(f"Scan {self.scan_id} warning: {message} (path: {path})")

    def complete(self, status: str = "completed"):
        """Mark the scan as completed."""
        self.status = status
        self.end_time = datetime.now(timezone.utc)
        logger.info(f"Scan {self.scan_id} completed with status: {status}")


class LibraryScanService:
    """Service for scanning library storage paths and indexing manga content."""
    
    # Class variable to track active scans
    _active_scans: Dict[str, ScanProgress] = {}
    
    # Resource limits for security and performance
    MAX_SCAN_DURATION = 3600  # 1 hour limit
    MAX_FILES_PER_SCAN = 10000  # File count limit
    MAX_CONCURRENT_SCANS = 3  # Maximum concurrent scans
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_service = StoragePathService(db)
        self.format_service = FileFormatService()

    def get_scan_progress(self, scan_id: str) -> Optional[ScanProgress]:
        """Get progress information for a scan."""
        return self._active_scans.get(scan_id)

    def get_active_scans(self) -> List[Dict[str, Any]]:
        """Get all active scans."""
        return [scan.to_dict() for scan in self._active_scans.values()]

    async def start_manual_scan(
        self,
        storage_path_ids: Optional[List[int]] = None,
        full_scan: bool = False
    ) -> str:
        """
        Start a manual library scan.
        
        Args:
            storage_path_ids: List of storage path IDs to scan. If None, scans all active paths.
            full_scan: If True, performs a full rescan ignoring last scan times.
            
        Returns:
            scan_id: Unique identifier for this scan operation
        """
        # Generate unique scan ID
        scan_id = f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(self._active_scans)}"
        
        # Create progress tracker
        progress = ScanProgress(scan_id)
        self._active_scans[scan_id] = progress
        
        try:
            # Check concurrent scan limit
            running_scans = sum(1 for scan in self._active_scans.values() if scan.status == "running")
            if running_scans >= self.MAX_CONCURRENT_SCANS:
                progress.add_error(f"Maximum concurrent scans limit reached ({self.MAX_CONCURRENT_SCANS})")
                progress.complete("failed")
                return scan_id
            
            # Get storage paths to scan
            if storage_path_ids:
                storage_paths = []
                for path_id in storage_path_ids:
                    path = await self.storage_service.get_by_id(path_id)
                    if path:
                        storage_paths.append(path)
                    else:
                        progress.add_warning(f"Storage path not found: {path_id}")
            else:
                storage_paths = await self.storage_service.get_all(active_only=True, accessible_only=True)
            
            if not storage_paths:
                progress.add_error("No accessible storage paths found")
                progress.complete("failed")
                return scan_id
                
            progress.total_paths = len(storage_paths)
            
            # Start the scan in background
            asyncio.create_task(self._perform_scan(progress, storage_paths, full_scan))
            
            logger.info(f"Started manual scan {scan_id} for {len(storage_paths)} storage paths")
            return scan_id
            
        except Exception as e:
            progress.add_error(f"Failed to start scan: {str(e)}")
            progress.complete("failed")
            logger.error(f"Failed to start scan {scan_id}: {e}")
            return scan_id

    async def _perform_scan(
        self,
        progress: ScanProgress,
        storage_paths: List[StoragePath],
        full_scan: bool
    ):
        """Perform the actual scanning operation."""
        try:
            # Set up timeout for the scan
            scan_start_time = datetime.now(timezone.utc)
            # First pass: Count total files to scan
            total_files = 0
            path_file_map = {}
            
            for storage_path in storage_paths:
                try:
                    files = await self._discover_files(storage_path.path)
                    path_file_map[storage_path.id] = files
                    total_files += len(files)
                except Exception as e:
                    progress.add_error(f"Failed to discover files in {storage_path.path}: {str(e)}", storage_path.path)
            
            progress.total_files = total_files
            
            if total_files == 0:
                progress.add_warning("No manga files found in any storage path")
                progress.complete("completed")
                return
            
            # Check file count limit
            if total_files > self.MAX_FILES_PER_SCAN:
                progress.add_error(f"File count ({total_files}) exceeds maximum limit ({self.MAX_FILES_PER_SCAN})")
                progress.complete("failed")
                return
            
            # Second pass: Process each file
            for storage_path in storage_paths:
                # Check scan timeout
                current_time = datetime.now(timezone.utc)
                if (current_time - scan_start_time).total_seconds() > self.MAX_SCAN_DURATION:
                    progress.add_warning(f"Scan timeout reached ({self.MAX_SCAN_DURATION}s), stopping early")
                    break
                    
                if storage_path.id not in path_file_map:
                    progress.processed_paths += 1
                    continue
                    
                files = path_file_map[storage_path.id]
                await self._process_storage_path(progress, storage_path, files, full_scan, scan_start_time)
                progress.processed_paths += 1
                
                # Update storage path statistics
                await self._update_storage_path_stats(storage_path, len(files))
            
            progress.complete("completed")
            
        except Exception as e:
            progress.add_error(f"Scan failed: {str(e)}")
            progress.complete("failed")
            logger.error(f"Scan {progress.scan_id} failed: {e}")
        finally:
            # Clean up scan from active scans after a delay to allow status checking
            await asyncio.sleep(60)  # Keep for 1 minute after completion
            self._active_scans.pop(progress.scan_id, None)

    async def _discover_files(self, base_path: str) -> List[str]:
        """Discover all manga files in a storage path."""
        files = []
        base_path_obj = Path(base_path)
        
        # Supported extensions for file discovery
        supported_extensions = {'.cbz', '.cbr', '.pdf', '.zip', '.rar'}
        
        try:
            # Recursive walk through directory
            for root, dirs, filenames in os.walk(base_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                root_path = Path(root)
                
                # Check if this directory itself contains images (folder format)
                image_files = [f for f in filenames if Path(f).suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}]
                if image_files and len(image_files) >= 3:  # Minimum 3 images to consider it a manga folder
                    files.append(str(root_path))
                
                # Add supported archive files
                for filename in filenames:
                    file_path = root_path / filename
                    if file_path.suffix.lower() in supported_extensions:
                        files.append(str(file_path))
                        
        except Exception as e:
            logger.error(f"Error discovering files in {base_path}: {e}")
            raise
        
        return files

    async def _process_storage_path(
        self,
        progress: ScanProgress,
        storage_path: StoragePath,
        files: List[str],
        full_scan: bool,
        scan_start_time: datetime
    ):
        """Process all files in a storage path."""
        for file_path in files:
            # Check timeout periodically
            if progress.processed_files % 100 == 0:  # Check every 100 files
                current_time = datetime.now(timezone.utc)
                if (current_time - scan_start_time).total_seconds() > self.MAX_SCAN_DURATION:
                    progress.add_warning("Scan timeout reached during file processing")
                    break
                    
            try:
                await self._process_file(progress, storage_path, file_path, full_scan)
                progress.processed_files += 1
                
                # Yield control occasionally to prevent blocking
                if progress.processed_files % 50 == 0:
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                progress.add_error(f"Failed to process file: {str(e)}", file_path)
                progress.processed_files += 1

    async def _process_file(
        self,
        progress: ScanProgress,
        storage_path: StoragePath,
        file_path: str,
        full_scan: bool
    ):
        """Process a single manga file or directory."""
        # Detect file format
        format_info = self.format_service.detect_format(file_path)
        
        # Update file stats
        if format_info.is_supported:
            progress.supported_files += 1
        else:
            progress.unsupported_files += 1
            
        if format_info.is_corrupted:
            progress.corrupted_files += 1
            progress.add_warning(f"Corrupted file detected: {format_info.error_message}", file_path)
            return
        
        if not format_info.is_supported or not format_info.is_valid:
            progress.add_warning(f"Unsupported or invalid file: {format_info.error_message}", file_path)
            return
        
        # Extract series and chapter information from file path
        series_info, chapter_info = self._extract_metadata_from_path(file_path)
        
        # Check if series already exists
        existing_series = await self._find_or_create_series(
            progress, storage_path, series_info, format_info
        )
        
        if existing_series:
            # Check if chapter already exists
            await self._find_or_create_chapter(
                progress, existing_series, chapter_info, file_path, format_info
            )

    def _extract_metadata_from_path(self, file_path: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract series and chapter metadata from file path."""
        path_obj = Path(file_path)
        
        # Basic series name extraction from parent directory or filename
        if path_obj.is_dir():
            # For folder format, use the directory name as series title
            series_title = path_obj.name
            chapter_title = None
            chapter_number = 1.0  # Default chapter number for folders
        else:
            # For files, try to extract series and chapter info
            parent_dir = path_obj.parent.name
            filename = path_obj.stem
            
            # Simple heuristic: if parent directory looks like a series name, use it
            # Otherwise, try to extract series name from filename
            if len(parent_dir) > 3 and not parent_dir.lower() in ['manga', 'comics', 'cbz', 'cbr']:
                series_title = parent_dir
                chapter_title = filename
            else:
                series_title = filename
                chapter_title = None
                
            # Try to extract chapter number from filename
            chapter_number = self._extract_chapter_number(filename)
        
        series_info = {
            'title': self._clean_title(series_title),
            'description': None,
            'author': None,
            'artist': None,
            'status': 'unknown'
        }
        
        chapter_info = {
            'number': chapter_number,
            'title': self._clean_title(chapter_title) if chapter_title else None
        }
        
        return series_info, chapter_info

    def _clean_title(self, title: str) -> str:
        """Clean up a title string."""
        if not title:
            return "Untitled"
            
        # Remove common prefixes/suffixes and clean up
        title = title.strip()
        
        # Remove file extensions that might have been missed
        for ext in ['.cbz', '.cbr', '.pdf', '.zip', '.rar']:
            if title.lower().endswith(ext):
                title = title[:-len(ext)]
                break
        
        # Remove common patterns
        import re
        # Remove patterns like [Group], (Year), etc.
        title = re.sub(r'\[[^\]]+\]', '', title)
        title = re.sub(r'\([^)]+\)', '', title)
        
        # Remove underscores and clean up
        title = title.replace('_', ' ')
        title = re.sub(r'\s+', ' ', title)  # Multiple spaces to single
        title = title.strip()
        
        return title if title else "Untitled"

    def _extract_chapter_number(self, filename: str) -> float:
        """Extract chapter number from filename."""
        import re
        
        # Common patterns for chapter numbers
        patterns = [
            r'[Cc]hapter?\s*(\d+(?:\.\d+)?)',
            r'[Cc]h\.?\s*(\d+(?:\.\d+)?)',
            r'[Vv]ol\.?\s*\d+\s*[Cc]h\.?\s*(\d+(?:\.\d+)?)',
            r'\b(\d+(?:\.\d+)?)\b',  # Any number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return 1.0  # Default chapter number

    async def _find_or_create_series(
        self,
        progress: ScanProgress,
        storage_path: StoragePath,
        series_info: Dict[str, Any],
        format_info: FileFormatInfo
    ) -> Optional[Series]:
        """Find existing series or create a new one."""
        try:
            # Look for existing series with the same title
            result = await self.db.execute(
                select(Series).where(Series.title == series_info['title'])
            )
            existing_series = result.scalars().first()
            
            if existing_series:
                # Update existing series if needed
                updated = False
                if not existing_series.description and series_info.get('description'):
                    existing_series.description = series_info['description']
                    updated = True
                    
                if updated:
                    await self.db.commit()
                    await self.db.refresh(existing_series)
                    progress.updated_series += 1
                    
                return existing_series
            else:
                # Create new series
                new_series = Series(
                    title=series_info['title'],
                    description=series_info.get('description'),
                    author=series_info.get('author'),
                    artist=series_info.get('artist'),
                    status=series_info.get('status', 'unknown')
                )
                
                self.db.add(new_series)
                await self.db.commit()
                await self.db.refresh(new_series)
                
                progress.new_series += 1
                logger.info(f"Created new series: {new_series.title}")
                return new_series
                
        except Exception as e:
            progress.add_error(f"Failed to find/create series '{series_info['title']}': {str(e)}")
            return None

    async def _find_or_create_chapter(
        self,
        progress: ScanProgress,
        series: Series,
        chapter_info: Dict[str, Any],
        file_path: str,
        format_info: FileFormatInfo
    ):
        """Find existing chapter or create a new one."""
        try:
            # Look for existing chapter with same series and number
            result = await self.db.execute(
                select(Chapter).where(
                    and_(
                        Chapter.series_id == series.id,
                        Chapter.number == chapter_info['number']
                    )
                )
            )
            existing_chapter = result.scalars().first()
            
            if existing_chapter:
                # Update chapter file path if different
                if existing_chapter.file_path != file_path:
                    existing_chapter.file_path = file_path
                    await self.db.commit()
                    logger.info(f"Updated chapter {existing_chapter.number} file path for series {series.title}")
            else:
                # Create new chapter
                new_chapter = Chapter(
                    series_id=series.id,
                    number=chapter_info['number'],
                    title=chapter_info.get('title'),
                    file_path=file_path
                )
                
                self.db.add(new_chapter)
                await self.db.commit()
                await self.db.refresh(new_chapter)
                
                progress.new_chapters += 1
                logger.info(f"Created new chapter {new_chapter.number} for series {series.title}")
                
        except Exception as e:
            progress.add_error(
                f"Failed to find/create chapter {chapter_info['number']} for series '{series.title}': {str(e)}",
                file_path
            )

    async def _update_storage_path_stats(self, storage_path: StoragePath, file_count: int):
        """Update statistics for a storage path after scanning."""
        try:
            # Update file count
            storage_path.file_count = file_count
            storage_path.last_scanned_at = datetime.now(timezone.utc)
            
            # Count series in this storage path (approximate)
            # This is a simplified count - in practice you'd want to track which series belong to which path
            result = await self.db.execute(select(Series))
            all_series = result.scalars().all()
            storage_path.series_count = len(all_series)
            
            await self.db.commit()
            await self.db.refresh(storage_path)
            
        except Exception as e:
            logger.error(f"Failed to update storage path stats for {storage_path.name}: {e}")

    def cancel_scan(self, scan_id: str) -> bool:
        """Cancel an active scan."""
        if scan_id in self._active_scans:
            progress = self._active_scans[scan_id]
            if progress.status == "running":
                progress.complete("cancelled")
                logger.info(f"Cancelled scan {scan_id}")
                return True
        return False