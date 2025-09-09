"""Service for securely extracting pages from manga archives."""

import os
import io
import re
import zipfile
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO, Tuple
from PIL import Image
from PIL.Image import DecompressionBombError

from app.services.file_format import FileFormatService, SupportedFormat, FileFormatInfo

logger = logging.getLogger(__name__)


class ArchiveExtractorError(Exception):
    """Base exception for archive extraction errors."""
    pass


class SecurityError(ArchiveExtractorError):
    """Raised when security validation fails."""
    pass


class ExtractionError(ArchiveExtractorError):
    """Raised when file extraction fails."""
    pass


class ArchiveExtractor:
    """Service for securely extracting pages from manga archives."""
    
    def __init__(self):
        self.format_service = FileFormatService()
        
        # Security limits
        self.MAX_EXTRACTED_SIZE = 100 * 1024 * 1024  # 100MB per archive
        self.MAX_IMAGE_PIXELS = 50 * 1024 * 1024  # 50 megapixels per image
        self.MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB per image file
        self.MAX_COMPRESSION_RATIO = 100  # Maximum compression ratio
        
        # Allowed image formats for security
        self.ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'GIF', 'BMP', 'WEBP'}
        self.ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    def get_page_list(self, chapter_file_path: str) -> List[str]:
        """
        Get list of page filenames from a chapter archive or directory.
        
        Args:
            chapter_file_path: Path to the chapter file or directory
            
        Returns:
            List of page filenames in reading order
            
        Raises:
            ArchiveExtractorError: If the file cannot be processed
        """
        try:
            # Validate the file path for security
            safe_path = self._validate_file_path(chapter_file_path)
            
            # Detect file format
            format_info = self.format_service.detect_format(safe_path)
            if not format_info.is_supported or not format_info.is_valid:
                raise ArchiveExtractorError(f"Unsupported or invalid file: {format_info.error_message}")
            
            if format_info.format_type == SupportedFormat.FOLDER:
                return self._get_folder_pages(safe_path)
            elif format_info.format_type in (SupportedFormat.CBZ, SupportedFormat.ZIP):
                return self._get_zip_pages(safe_path)
            elif format_info.format_type in (SupportedFormat.CBR, SupportedFormat.RAR):
                return self._get_rar_pages(safe_path)
            elif format_info.format_type == SupportedFormat.PDF:
                return self._get_pdf_pages(safe_path)
            else:
                raise ArchiveExtractorError(f"Unsupported format: {format_info.format_type}")
                
        except Exception as e:
            logger.error(f"Error getting page list for {chapter_file_path}: {e}")
            raise ArchiveExtractorError(f"Failed to get page list: {str(e)}")

    def extract_page(self, chapter_file_path: str, page_filename: str, max_width: Optional[int] = None) -> Tuple[bytes, str]:
        """
        Extract and optionally resize a single page from a chapter archive.
        
        Args:
            chapter_file_path: Path to the chapter file or directory
            page_filename: Filename of the page to extract
            max_width: Optional maximum width for resizing (maintains aspect ratio)
            
        Returns:
            Tuple of (image_bytes, content_type)
            
        Raises:
            ArchiveExtractorError: If extraction fails
            SecurityError: If security validation fails
        """
        try:
            # Validate inputs
            safe_path = self._validate_file_path(chapter_file_path)
            safe_filename = self._validate_page_filename(page_filename)
            
            # Detect file format
            format_info = self.format_service.detect_format(safe_path)
            if not format_info.is_supported or not format_info.is_valid:
                raise ArchiveExtractorError(f"Unsupported or invalid file: {format_info.error_message}")
            
            # Extract based on format
            image_data = None
            if format_info.format_type == SupportedFormat.FOLDER:
                image_data = self._extract_from_folder(safe_path, safe_filename)
            elif format_info.format_type in (SupportedFormat.CBZ, SupportedFormat.ZIP):
                image_data = self._extract_from_zip(safe_path, safe_filename)
            elif format_info.format_type in (SupportedFormat.CBR, SupportedFormat.RAR):
                image_data = self._extract_from_rar(safe_path, safe_filename)
            elif format_info.format_type == SupportedFormat.PDF:
                image_data = self._extract_from_pdf(safe_path, safe_filename)
            else:
                raise ArchiveExtractorError(f"Unsupported format: {format_info.format_type}")
            
            if not image_data:
                raise ExtractionError(f"Failed to extract page: {page_filename}")
            
            # Validate and process the image
            return self._process_image(image_data, max_width)
            
        except (SecurityError, ArchiveExtractorError):
            raise
        except Exception as e:
            logger.error(f"Error extracting page {page_filename} from {chapter_file_path}: {e}")
            raise ExtractionError(f"Failed to extract page: {str(e)}")

    def _validate_file_path(self, file_path: str) -> str:
        """Validate and sanitize file path to prevent directory traversal."""
        try:
            # Convert to Path object for safer handling
            path_obj = Path(file_path).resolve()
            original_path = Path(file_path)
            
            # Check for path traversal attempts
            if '..' in str(original_path) or str(original_path).startswith('/'):
                raise SecurityError(f"Path traversal attempt detected: {file_path}")
            
            # Additional checks for suspicious patterns
            suspicious_patterns = ['../', '..\\', '/etc/', '/proc/', '/sys/', 'C:\\Windows']
            for pattern in suspicious_patterns:
                if pattern.lower() in file_path.lower():
                    raise SecurityError(f"Suspicious path pattern detected: {file_path}")
            
            # Check if path exists
            if not path_obj.exists():
                raise SecurityError(f"File does not exist: {file_path}")
            
            # Ensure the resolved path is still under reasonable bounds
            # This prevents symlink attacks and other path manipulation
            if not path_obj.is_file() and not path_obj.is_dir():
                raise SecurityError(f"Path is not a valid file or directory: {file_path}")
            
            # Get the absolute path and verify it hasn't been manipulated
            abs_path = str(path_obj.absolute())
            
            # Check file size if it's a file to prevent processing extremely large files
            if path_obj.is_file():
                file_size = path_obj.stat().st_size
                max_file_size = 500 * 1024 * 1024  # 500MB max archive size
                if file_size > max_file_size:
                    raise SecurityError(f"File too large: {file_size} bytes (max: {max_file_size})")
            
            return abs_path
            
        except SecurityError:
            raise
        except Exception as e:
            raise SecurityError(f"Invalid file path: {str(e)}")

    def _validate_page_filename(self, filename: str) -> str:
        """Validate and sanitize page filename."""
        # Remove directory traversal attempts
        safe_name = os.path.basename(filename)
        
        # More comprehensive checks for path traversal
        dangerous_patterns = ['..', '/', '\\', '~', '$', '|', '&', ';', '`', '(', ')', '{', '}', '[', ']', '<', '>', '"', "'"]
        for pattern in dangerous_patterns:
            if pattern in safe_name:
                raise SecurityError(f"Invalid characters in page filename: {filename}")
        
        # Check for null bytes and other control characters
        if '\x00' in safe_name or any(ord(c) < 32 for c in safe_name if ord(c) != 9):  # Allow tabs
            raise SecurityError(f"Invalid control characters in filename: {filename}")
        
        # Ensure filename is reasonable length
        if len(safe_name) > 255 or len(safe_name) < 1:
            raise SecurityError(f"Invalid filename length: {filename}")
        
        # Check file extension
        ext = Path(safe_name).suffix.lower()
        if ext not in self.ALLOWED_IMAGE_EXTENSIONS:
            raise SecurityError(f"Invalid image file extension: {ext}")
        
        # Additional validation: only allow alphanumeric, spaces, dots, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\s\._-]+\.[a-zA-Z0-9]+$', safe_name):
            raise SecurityError(f"Filename contains invalid characters: {filename}")
        
        return safe_name

    def _get_folder_pages(self, folder_path: str) -> List[str]:
        """Get page list from a folder containing images."""
        folder = Path(folder_path)
        
        # Get all image files
        image_files = [
            f.name for f in folder.iterdir() 
            if f.is_file() and f.suffix.lower() in self.ALLOWED_IMAGE_EXTENSIONS
        ]
        
        # Sort naturally for proper reading order
        image_files.sort(key=self.format_service._natural_sort_key)
        
        return image_files

    def _get_zip_pages(self, zip_path: str) -> List[str]:
        """Get page list from ZIP/CBZ archive."""
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            # Get all files in archive
            file_list = zip_file.namelist()
            
            # Filter image files
            image_files = [
                name for name in file_list
                if Path(name).suffix.lower() in self.ALLOWED_IMAGE_EXTENSIONS
                and not name.startswith('__MACOSX/')  # Skip macOS metadata
                and not name.endswith('/')  # Skip directories
            ]
            
            # Sort for proper reading order
            image_files.sort(key=self.format_service._natural_sort_key)
            
            return image_files

    def _get_rar_pages(self, rar_path: str) -> List[str]:
        """Get page list from RAR/CBR archive."""
        # For now, return empty list as RAR support is limited
        # In a full implementation, you would use rarfile library
        logger.warning(f"RAR archive support is limited: {rar_path}")
        return []

    def _get_pdf_pages(self, pdf_path: str) -> List[str]:
        """Get page list from PDF."""
        # For now, return page numbers as strings
        # In a full implementation, you would use PyPDF2 or similar
        # to get actual page count
        logger.warning(f"PDF page extraction is limited: {pdf_path}")
        return [f"page_{i+1}.jpg" for i in range(10)]  # Placeholder

    def _extract_from_folder(self, folder_path: str, filename: str) -> bytes:
        """Extract image from folder."""
        file_path = Path(folder_path) / filename
        
        if not file_path.exists():
            raise ExtractionError(f"Page not found: {filename}")
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.MAX_IMAGE_SIZE:
            raise SecurityError(f"Image file too large: {file_size} bytes")
        
        # Read the file
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise ExtractionError(f"Failed to read image file: {str(e)}")

    def _extract_from_zip(self, zip_path: str, filename: str) -> bytes:
        """Extract image from ZIP/CBZ archive."""
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            try:
                # Validate that the filename exists in the archive
                if filename not in zip_file.namelist():
                    raise ExtractionError(f"Page not found in archive: {filename}")
                
                # Get file info for security checks
                file_info = zip_file.getinfo(filename)
                
                # Check for path traversal in the archive entry
                if os.path.isabs(file_info.filename) or '..' in file_info.filename:
                    raise SecurityError(f"Archive contains unsafe path: {file_info.filename}")
                
                # Check uncompressed size
                if file_info.file_size > self.MAX_IMAGE_SIZE:
                    raise SecurityError(f"Extracted file too large: {file_info.file_size} bytes")
                
                # Check compression ratio for ZIP bomb detection
                if file_info.compress_size > 0:
                    ratio = file_info.file_size / file_info.compress_size
                    if ratio > self.MAX_COMPRESSION_RATIO:
                        raise SecurityError(f"Suspicious compression ratio: {ratio}")
                
                # Additional safety check: verify the filename matches what we expect
                if not self._is_safe_archive_path(file_info.filename):
                    raise SecurityError(f"Unsafe archive path: {file_info.filename}")
                
                # Extract the file with size limit
                with zip_file.open(filename) as file:
                    data = file.read(self.MAX_IMAGE_SIZE + 1)  # Read one byte more to detect oversize
                    if len(data) > self.MAX_IMAGE_SIZE:
                        raise SecurityError(f"Extracted file exceeds size limit: {len(data)} bytes")
                    return data
                    
            except KeyError:
                raise ExtractionError(f"Page not found in archive: {filename}")
            except SecurityError:
                raise
            except Exception as e:
                raise ExtractionError(f"Failed to extract from ZIP: {str(e)}")

    def _extract_from_rar(self, rar_path: str, filename: str) -> bytes:
        """Extract image from RAR/CBR archive."""
        # RAR extraction would require rarfile library or external tools
        raise ExtractionError("RAR extraction not yet implemented")

    def _extract_from_pdf(self, pdf_path: str, filename: str) -> bytes:
        """Extract page from PDF."""
        # PDF page extraction would require PyPDF2/PyMuPDF
        raise ExtractionError("PDF extraction not yet implemented")

    def _process_image(self, image_data: bytes, max_width: Optional[int] = None) -> Tuple[bytes, str]:
        """
        Process and validate image data, optionally resizing.
        
        Args:
            image_data: Raw image bytes
            max_width: Optional maximum width for resizing
            
        Returns:
            Tuple of (processed_image_bytes, content_type)
        """
        try:
            # Validate image data size before processing
            if len(image_data) > self.MAX_IMAGE_SIZE:
                raise SecurityError(f"Image data too large: {len(image_data)} bytes")
            
            # Check for malicious headers/magic bytes
            if not self._validate_image_magic_bytes(image_data):
                raise SecurityError("Invalid or suspicious image format")
            
            # Security: Limit image size to prevent decompression bombs
            Image.MAX_IMAGE_PIXELS = self.MAX_IMAGE_PIXELS
            
            # Set additional PIL security limits
            original_max_pixels = Image.MAX_IMAGE_PIXELS
            try:
                # Open and validate the image with strict limits
                with Image.open(io.BytesIO(image_data)) as img:
                    # Verify image format is allowed
                    if img.format not in self.ALLOWED_IMAGE_FORMATS:
                        raise SecurityError(f"Unsupported image format: {img.format}")
                    
                    # Additional size checks after opening
                    width, height = img.size
                    if width * height > self.MAX_IMAGE_PIXELS:
                        raise SecurityError(f"Image resolution too large: {width}x{height}")
                    
                    # Check for reasonable dimensions
                    if width > 10000 or height > 10000:
                        raise SecurityError(f"Image dimensions too large: {width}x{height}")
                    
                    # Verify the image is not corrupted
                    try:
                        img.verify()
                    except Exception:
                        raise SecurityError("Image verification failed - possibly corrupted")
                    
                    # Re-open for processing (verify() closes the image)
                    img = Image.open(io.BytesIO(image_data))
                    
                    # Convert RGBA to RGB for JPEG compatibility if needed
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Create white background
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize if requested
                    if max_width and img.width > max_width:
                        # Validate max_width is reasonable
                        if max_width > 4000:
                            max_width = 4000
                        # Calculate new height maintaining aspect ratio
                        aspect_ratio = img.height / img.width
                        new_height = int(max_width * aspect_ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save to bytes with quality limits
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    processed_data = output.getvalue()
                    
                    # Final size check
                    if len(processed_data) > self.MAX_IMAGE_SIZE:
                        raise SecurityError(f"Processed image too large: {len(processed_data)} bytes")
                    
                    return processed_data, 'image/jpeg'
                    
            finally:
                # Restore original limit
                Image.MAX_IMAGE_PIXELS = original_max_pixels
                
        except DecompressionBombError:
            raise SecurityError("Image too large (potential decompression bomb)")
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise ExtractionError(f"Failed to process image: {str(e)}")

    def get_chapter_info(self, chapter_file_path: str) -> Dict[str, Any]:
        """
        Get information about a chapter file including page count and format.
        
        Args:
            chapter_file_path: Path to the chapter file
            
        Returns:
            Dictionary with chapter information
        """
        try:
            safe_path = self._validate_file_path(chapter_file_path)
            format_info = self.format_service.detect_format(safe_path)
            
            if not format_info.is_supported or not format_info.is_valid:
                raise ArchiveExtractorError(f"Invalid chapter file: {format_info.error_message}")
            
            pages = self.get_page_list(safe_path)
            
            return {
                'path': safe_path,
                'format': format_info.format_type.value if format_info.format_type else 'unknown',
                'page_count': len(pages),
                'file_size': format_info.file_size,
                'pages': pages[:10],  # First 10 pages for preview
                'is_valid': format_info.is_valid,
                'metadata': format_info.metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Error getting chapter info for {chapter_file_path}: {e}")
            raise ArchiveExtractorError(f"Failed to get chapter info: {str(e)}")
    
    def _is_safe_archive_path(self, path: str) -> bool:
        """Check if an archive path is safe from traversal attacks."""
        # Check for path traversal attempts in original path first
        if '..' in path:
            return False
            
        # Check for absolute paths in original path
        if path.startswith('/') or path.startswith('\\'):
            return False
            
        # Check for Windows drive letters
        if len(path) >= 2 and path[1] == ':':
            return False
        
        # Normalize the path after initial checks
        normalized = os.path.normpath(path)
        
        # Additional checks on normalized path
        if normalized.startswith('../') or '/../' in normalized or normalized == '..':
            return False
        
        # Check for absolute paths after normalization
        if os.path.isabs(normalized):
            return False
            
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        if any(char in normalized for char in dangerous_chars):
            return False
            
        # Ensure path doesn't escape current directory when resolved
        try:
            # This will raise an exception if path tries to escape
            resolved = os.path.abspath(os.path.join('/', normalized))
            if not resolved.startswith('/'):
                return False
        except (OSError, ValueError):
            return False
            
        return True
    
    def _validate_image_magic_bytes(self, data: bytes) -> bool:
        """
        Validate image file by checking magic bytes/headers.
        
        Args:
            data: Image data bytes
            
        Returns:
            True if valid image format, False otherwise
        """
        if len(data) < 12:  # Minimum bytes needed for magic byte detection
            return False
            
        # Check for valid image format magic bytes
        # JPEG
        if data[:3] == b'\xff\xd8\xff':
            return True
        # PNG
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return True
        # GIF
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return True
        # BMP
        if data[:2] == b'BM':
            return True
        # WebP
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return True
            
        return False