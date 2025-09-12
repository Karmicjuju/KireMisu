"""Service layer for manga reader functionality."""

import os
import hashlib
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging
from PIL import Image
from io import BytesIO

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.chapter import Chapter
from app.models.series import Series
from app.models.user import User
from app.services.archive_extractor import ArchiveExtractor, ArchiveExtractorError, SecurityError
from app.db.database import get_db

logger = logging.getLogger(__name__)


class ReadingProgress:
    """Represents user's reading progress for a chapter."""
    
    def __init__(self, chapter_id: int, user_id: int, current_page: int = 0, total_pages: int = 0):
        self.chapter_id = chapter_id
        self.user_id = user_id
        self.current_page = current_page
        self.total_pages = total_pages
        self.last_read = datetime.utcnow()
        self.is_completed = current_page >= total_pages - 1 if total_pages > 0 else False


class ImageCache:
    """Simple in-memory cache for extracted images."""
    
    def __init__(self, max_size_mb: int = 100):
        self.cache: Dict[str, Tuple[bytes, str, datetime]] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.cache_ttl = timedelta(hours=1)  # Cache for 1 hour
    
    def _generate_key(self, chapter_id: int, page_filename: str, max_width: Optional[int] = None) -> str:
        """Generate cache key for image."""
        key_data = f"{chapter_id}:{page_filename}:{max_width or 'original'}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, chapter_id: int, page_filename: str, max_width: Optional[int] = None) -> Optional[Tuple[bytes, str]]:
        """Get cached image if available and not expired."""
        key = self._generate_key(chapter_id, page_filename, max_width)
        
        if key in self.cache:
            image_data, content_type, cached_time = self.cache[key]
            
            # Check if cache entry is still valid
            if datetime.utcnow() - cached_time < self.cache_ttl:
                return image_data, content_type
            else:
                # Remove expired entry
                self._remove_entry(key)
        
        return None
    
    def put(self, chapter_id: int, page_filename: str, image_data: bytes, content_type: str, max_width: Optional[int] = None):
        """Cache image data."""
        key = self._generate_key(chapter_id, page_filename, max_width)
        entry_size = len(image_data)
        
        # Make room if needed
        while self.current_size + entry_size > self.max_size_bytes and self.cache:
            self._evict_oldest()
        
        # Add to cache
        self.cache[key] = (image_data, content_type, datetime.utcnow())
        self.current_size += entry_size
        
        logger.debug(f"Cached image {key}, cache size: {self.current_size / 1024 / 1024:.1f}MB")
    
    def _remove_entry(self, key: str):
        """Remove entry from cache."""
        if key in self.cache:
            image_data, _, _ = self.cache[key]
            self.current_size -= len(image_data)
            del self.cache[key]
    
    def _evict_oldest(self):
        """Evict oldest cache entry."""
        if not self.cache:
            return
        
        # Find oldest entry
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][2])
        self._remove_entry(oldest_key)
        
        logger.debug(f"Evicted cache entry {oldest_key}")
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.current_size = 0


class ReaderService:
    """Service for manga reader operations."""
    
    def __init__(self):
        self.extractor = ArchiveExtractor()
        self.image_cache = ImageCache()
        self.progress_cache: Dict[str, ReadingProgress] = {}
    
    async def get_chapter_pages(self, chapter_id: int, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Get list of pages for a chapter.
        
        Args:
            chapter_id: ID of the chapter
            db: Database session
            user_id: ID of the requesting user
            
        Returns:
            Dictionary with chapter pages information
            
        Raises:
            HTTPException: If chapter not found or access denied
        """
        try:
            # Get chapter from database
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            
            # Check if user has access to this chapter (via series)
            series = db.query(Series).filter(Series.id == chapter.series_id).first()
            if not series:
                raise HTTPException(status_code=404, detail="Series not found")
            
            # Get page list from archive
            pages = self.extractor.get_page_list(chapter.file_path)
            if not pages:
                raise HTTPException(status_code=400, detail="No pages found in chapter")
            
            # Get or initialize reading progress
            progress = self._get_reading_progress(chapter_id, user_id, len(pages))
            
            # Detect optimal reading mode
            suggested_mode = self.detect_reading_mode(chapter.file_path)
            
            return {
                'chapter_id': chapter_id,
                'chapter_number': str(chapter.number),
                'chapter_title': chapter.title,
                'series_title': series.title,
                'pages': pages,
                'page_count': len(pages),
                'current_page': progress.current_page,
                'suggested_reading_mode': suggested_mode,
                'reading_progress': {
                    'current_page': progress.current_page,
                    'total_pages': progress.total_pages,
                    'is_completed': progress.is_completed,
                    'last_read': progress.last_read.isoformat()
                }
            }
            
        except HTTPException:
            raise
        except ArchiveExtractorError as e:
            logger.error(f"Archive extraction error for chapter {chapter_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to process chapter: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting chapter pages for {chapter_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_page_image(
        self, 
        chapter_id: int, 
        page_filename: str, 
        db: Session, 
        user_id: int,
        max_width: Optional[int] = None
    ) -> Tuple[bytes, str]:
        """
        Get image data for a specific page.
        
        Args:
            chapter_id: ID of the chapter
            page_filename: Filename of the page to retrieve
            db: Database session
            user_id: ID of the requesting user
            max_width: Optional maximum width for resizing
            
        Returns:
            Tuple of (image_bytes, content_type)
            
        Raises:
            HTTPException: If chapter/page not found or access denied
        """
        try:
            # Check cache first
            cached = self.image_cache.get(chapter_id, page_filename, max_width)
            if cached:
                logger.debug(f"Serving cached image: {page_filename}")
                return cached
            
            # Get chapter from database
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            
            # Extract page from archive
            image_data, content_type = self.extractor.extract_page(
                chapter.file_path, 
                page_filename, 
                max_width
            )
            
            # Cache the extracted image
            self.image_cache.put(chapter_id, page_filename, image_data, content_type, max_width)
            
            logger.debug(f"Extracted and cached page: {page_filename}")
            return image_data, content_type
            
        except HTTPException:
            raise
        except SecurityError as e:
            logger.warning(f"Security error extracting page {page_filename}: {e}")
            raise HTTPException(status_code=403, detail="Access denied")
        except ArchiveExtractorError as e:
            logger.error(f"Extraction error for page {page_filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to extract page: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting page image {page_filename} from chapter {chapter_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_reading_progress(
        self, 
        chapter_id: int, 
        page_number: int, 
        db: Session, 
        user_id: int
    ) -> ReadingProgress:
        """
        Update user's reading progress for a chapter.
        
        Args:
            chapter_id: ID of the chapter
            page_number: Current page number (0-indexed)
            db: Database session
            user_id: ID of the user
            
        Returns:
            Updated ReadingProgress object
            
        Raises:
            HTTPException: If chapter not found or invalid page number
        """
        try:
            # Get chapter from database
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            
            # Get total pages
            pages = self.extractor.get_page_list(chapter.file_path)
            total_pages = len(pages)
            
            if page_number < 0 or page_number >= total_pages:
                raise HTTPException(status_code=400, detail="Invalid page number")
            
            # Update progress
            progress_key = f"{chapter_id}:{user_id}"
            progress = ReadingProgress(
                chapter_id=chapter_id,
                user_id=user_id,
                current_page=page_number,
                total_pages=total_pages
            )
            
            self.progress_cache[progress_key] = progress
            
            # Update chapter read status if completed
            if progress.is_completed and not chapter.read_status:
                chapter.read_status = True
                db.commit()
                logger.info(f"Marked chapter {chapter_id} as read for user {user_id}")
            
            logger.debug(f"Updated reading progress: chapter {chapter_id}, page {page_number}")
            return progress
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating reading progress: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Unable to update reading progress")
    
    async def get_chapter_navigation(
        self, 
        chapter_id: int, 
        db: Session, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get navigation information for a chapter (previous/next chapters).
        
        Args:
            chapter_id: ID of the current chapter
            db: Database session
            user_id: ID of the requesting user
            
        Returns:
            Dictionary with navigation information
        """
        try:
            # Get current chapter
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")
            
            # Get all chapters in the same series, ordered by number
            all_chapters = (
                db.query(Chapter)
                .filter(Chapter.series_id == chapter.series_id)
                .order_by(Chapter.number.asc())
                .all()
            )
            
            # Find current chapter index
            current_index = None
            for i, ch in enumerate(all_chapters):
                if ch.id == chapter_id:
                    current_index = i
                    break
            
            if current_index is None:
                raise HTTPException(status_code=404, detail="Chapter not found in series")
            
            # Get previous and next chapters
            prev_chapter = all_chapters[current_index - 1] if current_index > 0 else None
            next_chapter = all_chapters[current_index + 1] if current_index < len(all_chapters) - 1 else None
            
            return {
                'current_chapter': {
                    'id': chapter.id,
                    'number': str(chapter.number),
                    'title': chapter.title
                },
                'previous_chapter': {
                    'id': prev_chapter.id,
                    'number': str(prev_chapter.number),
                    'title': prev_chapter.title
                } if prev_chapter else None,
                'next_chapter': {
                    'id': next_chapter.id,
                    'number': str(next_chapter.number),
                    'title': next_chapter.title
                } if next_chapter else None,
                'total_chapters': len(all_chapters),
                'current_position': current_index + 1
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting chapter navigation: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Unable to load navigation information")
    
    def _get_reading_progress(self, chapter_id: int, user_id: int, total_pages: int) -> ReadingProgress:
        """Get or create reading progress for a chapter."""
        progress_key = f"{chapter_id}:{user_id}"
        
        if progress_key in self.progress_cache:
            progress = self.progress_cache[progress_key]
            # Update total pages if different
            if progress.total_pages != total_pages:
                progress.total_pages = total_pages
                progress.is_completed = progress.current_page >= total_pages - 1 if total_pages > 0 else False
        else:
            # Create new progress
            progress = ReadingProgress(
                chapter_id=chapter_id,
                user_id=user_id,
                current_page=0,
                total_pages=total_pages
            )
            self.progress_cache[progress_key] = progress
        
        return progress
    
    def detect_reading_mode(self, chapter_path: str, sample_pages: int = 3) -> str:
        """
        Detect the optimal reading mode based on image dimensions.
        
        Args:
            chapter_path: Path to the chapter file
            sample_pages: Number of pages to sample for detection
            
        Returns:
            Reading mode: 'single', 'double', or 'vertical'
        """
        try:
            # Get page list
            pages = self.extractor.get_page_list(chapter_path)
            if not pages:
                return 'single'  # Default to single page
            
            # Sample first few pages
            pages_to_check = pages[:min(sample_pages, len(pages))]
            aspect_ratios = []
            
            for page_filename in pages_to_check:
                try:
                    # Extract page image
                    image_data, _ = self.extractor.extract_page(chapter_path, page_filename)
                    
                    # Analyze image dimensions
                    with Image.open(BytesIO(image_data)) as img:
                        width, height = img.size
                        aspect_ratio = width / height if height > 0 else 1.0
                        aspect_ratios.append(aspect_ratio)
                        
                        # Check for webtoon format (very tall images)
                        if height > width * 3:  # Height is more than 3x width
                            return 'vertical'
                
                except Exception as e:
                    logger.warning(f"Failed to analyze page {page_filename}: {e}")
                    continue
            
            if not aspect_ratios:
                return 'single'  # Default if no pages could be analyzed
            
            # Calculate average aspect ratio
            avg_aspect_ratio = sum(aspect_ratios) / len(aspect_ratios)
            
            # Determine reading mode based on aspect ratio
            if avg_aspect_ratio < 0.5:  # Very tall images (webtoon)
                return 'vertical'
            elif avg_aspect_ratio > 1.3:  # Wide images (likely double page spreads)
                return 'double'
            else:  # Standard manga pages
                return 'single'
                
        except Exception as e:
            logger.error(f"Error detecting reading mode: {e}")
            return 'single'  # Default to single page on error
    
    async def preload_pages(
        self, 
        chapter_id: int, 
        current_page: int, 
        db: Session, 
        user_id: int,
        preload_count: int = 3
    ):
        """
        Preload upcoming pages for smooth reading experience.
        
        Args:
            chapter_id: ID of the chapter
            current_page: Current page index
            db: Database session
            user_id: ID of the user
            preload_count: Number of pages to preload ahead
        """
        try:
            # Get chapter pages
            chapter_info = await self.get_chapter_pages(chapter_id, db, user_id)
            pages = chapter_info['pages']
            
            # Preload next few pages
            preload_tasks = []
            for i in range(1, preload_count + 1):
                next_page_index = current_page + i
                if next_page_index < len(pages):
                    page_filename = pages[next_page_index]
                    
                    # Check if already cached
                    if not self.image_cache.get(chapter_id, page_filename):
                        # Create preload task
                        task = asyncio.create_task(
                            self._preload_page(chapter_id, page_filename, db, user_id)
                        )
                        preload_tasks.append(task)
            
            # Execute preload tasks without waiting
            if preload_tasks:
                asyncio.gather(*preload_tasks, return_exceptions=True)
                logger.debug(f"Started preloading {len(preload_tasks)} pages for chapter {chapter_id}")
                
        except Exception as e:
            logger.error(f"Error preloading pages: {e}", exc_info=True)
            # Don't raise exception for preloading errors
    
    async def _preload_page(self, chapter_id: int, page_filename: str, db: Session, user_id: int):
        """Preload a single page."""
        try:
            await self.get_page_image(chapter_id, page_filename, db, user_id)
        except Exception as e:
            logger.debug(f"Failed to preload page {page_filename}: {e}")
    
    def clear_cache(self):
        """Clear image cache."""
        self.image_cache.clear()
        logger.info("Reader image cache cleared")