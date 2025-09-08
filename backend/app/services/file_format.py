"""Service layer for file format detection and validation."""

import os
import zipfile
import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class SupportedFormat(str, Enum):
    """Supported manga file formats."""
    CBZ = "cbz"           # Comic Book Zip
    CBR = "cbr"           # Comic Book RAR  
    PDF = "pdf"           # Portable Document Format
    ZIP = "zip"           # Generic ZIP archive
    RAR = "rar"           # Generic RAR archive
    FOLDER = "folder"     # Directory with images


class FileFormatInfo:
    """Information about a detected file format."""
    
    def __init__(
        self,
        path: str,
        format_type: Optional[SupportedFormat] = None,
        is_supported: bool = False,
        is_valid: bool = False,
        is_corrupted: bool = False,
        file_size: int = 0,
        page_count: Optional[int] = None,
        has_images: bool = False,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.path = path
        self.format_type = format_type
        self.is_supported = is_supported
        self.is_valid = is_valid
        self.is_corrupted = is_corrupted
        self.file_size = file_size
        self.page_count = page_count
        self.has_images = has_images
        self.error_message = error_message
        self.metadata = metadata or {}


class FileFormatService:
    """Service for detecting and validating manga file formats."""
    
    # Magic number signatures for file type detection
    MAGIC_SIGNATURES = {
        SupportedFormat.PDF: [b'%PDF'],
        SupportedFormat.ZIP: [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
        SupportedFormat.RAR: [b'Rar!', b'Rar!\x1a\x07\x00', b'Rar!\x1a\x07\x01\x00'],
    }
    
    # Common image extensions for validating comic archives
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
    
    # File extensions to format mapping
    EXTENSION_MAP = {
        '.cbz': SupportedFormat.CBZ,
        '.cbr': SupportedFormat.CBR,
        '.pdf': SupportedFormat.PDF,
        '.zip': SupportedFormat.ZIP,
        '.rar': SupportedFormat.RAR,
    }

    def detect_format(self, file_path: str) -> FileFormatInfo:
        """
        Detect and validate the format of a manga file or directory.
        
        Args:
            file_path: Path to the file or directory to analyze
            
        Returns:
            FileFormatInfo object with detection results
        """
        path_obj = Path(file_path)
        
        # Initialize result object
        result = FileFormatInfo(path=file_path)
        
        try:
            # Check if path exists
            if not path_obj.exists():
                result.error_message = "File or directory does not exist"
                return result
                
            # Get file size (0 for directories)
            result.file_size = path_obj.stat().st_size if path_obj.is_file() else 0
            
            # Handle directories (folder-based manga)
            if path_obj.is_dir():
                return self._analyze_directory(result, path_obj)
            
            # Handle regular files
            if path_obj.is_file():
                return self._analyze_file(result, path_obj)
            
            result.error_message = "Path is neither a file nor a directory"
            return result
            
        except PermissionError:
            result.error_message = "Permission denied accessing file"
            logger.warning(f"Permission denied accessing {file_path}")
        except OSError as e:
            result.error_message = f"System error: {str(e)}"
            logger.error(f"OS error analyzing {file_path}: {e}")
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error analyzing {file_path}: {e}")
            
        return result

    def _analyze_directory(self, result: FileFormatInfo, path_obj: Path) -> FileFormatInfo:
        """Analyze a directory for manga images."""
        try:
            # Get all files in directory (non-recursive for now)
            files = [f for f in path_obj.iterdir() if f.is_file()]
            
            # Find image files
            image_files = [
                f for f in files 
                if f.suffix.lower() in self.IMAGE_EXTENSIONS
            ]
            
            if not image_files:
                result.error_message = "No image files found in directory"
                return result
            
            # Sort image files naturally (important for reading order)
            image_files.sort(key=lambda x: self._natural_sort_key(x.name))
            
            # Validate that we can read the images
            valid_images = []
            for img_file in image_files[:10]:  # Check first 10 for performance
                if self._is_valid_image_file(img_file):
                    valid_images.append(img_file)
            
            if not valid_images:
                result.error_message = "No valid image files found"
                return result
            
            # Success!
            result.format_type = SupportedFormat.FOLDER
            result.is_supported = True
            result.is_valid = True
            result.has_images = True
            result.page_count = len(image_files)
            
            # Calculate total size of image files
            total_size = sum(f.stat().st_size for f in image_files)
            result.file_size = total_size
            
            # Add metadata
            result.metadata = {
                'image_files': [f.name for f in image_files],
                'first_image': image_files[0].name,
                'image_extensions': list(set(f.suffix.lower() for f in image_files)),
                'total_files': len(files),
                'image_file_count': len(image_files)
            }
            
        except Exception as e:
            result.error_message = f"Error analyzing directory: {str(e)}"
            logger.error(f"Error analyzing directory {path_obj}: {e}")
            
        return result

    def _analyze_file(self, result: FileFormatInfo, path_obj: Path) -> FileFormatInfo:
        """Analyze a single file."""
        # Get format from extension first
        extension = path_obj.suffix.lower()
        format_from_ext = self.EXTENSION_MAP.get(extension)
        
        # Read file header for magic number detection
        try:
            with open(path_obj, 'rb') as f:
                header = f.read(32)  # Read first 32 bytes
                
        except Exception as e:
            result.error_message = f"Cannot read file header: {str(e)}"
            return result
        
        # Detect format by magic number
        format_from_magic = self._detect_format_by_magic(header)
        
        # Determine actual format (prefer magic number over extension)
        detected_format = format_from_magic or format_from_ext
        
        if not detected_format:
            result.error_message = "Unsupported file format"
            return result
        
        result.format_type = detected_format
        result.is_supported = True
        
        # Validate the file based on its format
        if detected_format == SupportedFormat.PDF:
            return self._validate_pdf(result, path_obj)
        elif detected_format in (SupportedFormat.CBZ, SupportedFormat.ZIP):
            return self._validate_zip_archive(result, path_obj)
        elif detected_format in (SupportedFormat.CBR, SupportedFormat.RAR):
            return self._validate_rar_archive(result, path_obj)
        else:
            result.error_message = f"Validation not implemented for format: {detected_format}"
            
        return result

    def _detect_format_by_magic(self, header: bytes) -> Optional[SupportedFormat]:
        """Detect file format using magic number signatures."""
        for format_type, signatures in self.MAGIC_SIGNATURES.items():
            for signature in signatures:
                if header.startswith(signature):
                    return format_type
        return None

    def _validate_pdf(self, result: FileFormatInfo, path_obj: Path) -> FileFormatInfo:
        """Validate a PDF file."""
        try:
            # Basic PDF validation - check if file starts with PDF header and ends properly
            with open(path_obj, 'rb') as f:
                # Check header
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    result.error_message = "Invalid PDF header"
                    result.is_corrupted = True
                    return result
                
                # Try to read the end of the file for EOF marker
                f.seek(-1024, 2)  # Go to last 1024 bytes
                tail = f.read()
                
                # Look for PDF EOF marker
                if b'%%EOF' not in tail:
                    logger.warning(f"PDF {path_obj} may be incomplete - no EOF marker found")
                    result.metadata = {'warning': 'Incomplete PDF - no EOF marker'}
                
            # For more thorough PDF validation, we'd need a PDF library
            # For now, basic validation is sufficient
            result.is_valid = True
            result.has_images = True  # Assume PDFs can have images
            result.metadata = result.metadata or {}
            result.metadata.update({
                'pdf_version': header.decode('ascii', errors='ignore')[5:8] if len(header) >= 8 else 'unknown'
            })
            
        except Exception as e:
            result.error_message = f"Error validating PDF: {str(e)}"
            result.is_corrupted = True
            logger.error(f"Error validating PDF {path_obj}: {e}")
            
        return result

    def _validate_zip_archive(self, result: FileFormatInfo, path_obj: Path) -> FileFormatInfo:
        """Validate a ZIP archive (CBZ or ZIP)."""
        try:
            with zipfile.ZipFile(path_obj, 'r') as zip_file:
                # Test if archive can be read
                bad_file = zip_file.testzip()
                if bad_file:
                    result.error_message = f"Corrupted file in archive: {bad_file}"
                    result.is_corrupted = True
                    return result
                
                # ZIP bomb protection - check file sizes before extraction
                MAX_EXTRACTED_SIZE = 100 * 1024 * 1024  # 100MB limit per archive
                MAX_COMPRESSION_RATIO = 100  # Maximum compression ratio
                total_compressed_size = 0
                total_uncompressed_size = 0
                
                for file_info in zip_file.infolist():
                    # Skip directories
                    if file_info.is_dir():
                        continue
                        
                    compressed_size = file_info.compress_size
                    uncompressed_size = file_info.file_size
                    
                    # Check individual file size
                    if uncompressed_size > MAX_EXTRACTED_SIZE:
                        result.error_message = f"Archive contains file that is too large: {file_info.filename}"
                        result.is_corrupted = True
                        return result
                    
                    # Check compression ratio for ZIP bomb detection
                    if compressed_size > 0 and (uncompressed_size / compressed_size) > MAX_COMPRESSION_RATIO:
                        result.error_message = f"Suspicious compression ratio detected in file: {file_info.filename}"
                        result.is_corrupted = True
                        return result
                    
                    total_compressed_size += compressed_size
                    total_uncompressed_size += uncompressed_size
                    
                    # Check total extracted size
                    if total_uncompressed_size > MAX_EXTRACTED_SIZE:
                        result.error_message = "Archive total extracted size exceeds limit"
                        result.is_corrupted = True
                        return result
                
                # Get list of files in archive
                file_list = zip_file.namelist()
                
                # Find image files
                image_files = [
                    name for name in file_list
                    if Path(name).suffix.lower() in self.IMAGE_EXTENSIONS
                    and not name.startswith('__MACOSX/')  # Skip macOS metadata
                    and not name.endswith('/')  # Skip directories
                ]
                
                if not image_files:
                    result.error_message = "No image files found in archive"
                    return result
                
                # Sort image files for proper reading order
                image_files.sort(key=self._natural_sort_key)
                
                # Try to read a few images to validate
                valid_images = 0
                for img_name in image_files[:5]:  # Check first 5 images
                    try:
                        with zip_file.open(img_name) as img_file:
                            # Read first few bytes to validate image header
                            img_header = img_file.read(16)
                            if self._is_valid_image_header(img_header):
                                valid_images += 1
                    except Exception:
                        continue
                
                if valid_images == 0:
                    result.error_message = "No valid image files found in archive"
                    return result
                
                # Success!
                result.is_valid = True
                result.has_images = True
                result.page_count = len(image_files)
                
                result.metadata = {
                    'total_files': len(file_list),
                    'image_files': image_files[:10],  # First 10 for metadata
                    'image_file_count': len(image_files),
                    'first_image': image_files[0] if image_files else None,
                    'archive_type': 'zip',
                    'compression_method': 'deflate' if any(zip_file.getinfo(f).compress_type for f in file_list[:5]) else 'store'
                }
                
        except zipfile.BadZipFile:
            result.error_message = "Invalid or corrupted ZIP archive"
            result.is_corrupted = True
        except Exception as e:
            result.error_message = f"Error validating ZIP archive: {str(e)}"
            result.is_corrupted = True
            logger.error(f"Error validating ZIP {path_obj}: {e}")
            
        return result

    def _validate_rar_archive(self, result: FileFormatInfo, path_obj: Path) -> FileFormatInfo:
        """Validate a RAR archive (CBR or RAR)."""
        # RAR validation is more complex as it requires external tools or libraries
        # For now, we'll do basic validation and assume the archive is valid if it has the RAR signature
        
        try:
            with open(path_obj, 'rb') as f:
                header = f.read(32)
                
            # Check for RAR signature
            if not any(header.startswith(sig) for sig in self.MAGIC_SIGNATURES[SupportedFormat.RAR]):
                result.error_message = "Invalid RAR archive signature"
                result.is_corrupted = True
                return result
            
            # Without a RAR library, we can't fully validate the archive contents
            # We'll mark it as valid but note the limitation
            result.is_valid = True
            result.has_images = True  # Assume it contains images
            result.metadata = {
                'archive_type': 'rar',
                'validation_level': 'basic',
                'note': 'Full RAR validation requires additional libraries'
            }
            
        except Exception as e:
            result.error_message = f"Error validating RAR archive: {str(e)}"
            result.is_corrupted = True
            logger.error(f"Error validating RAR {path_obj}: {e}")
            
        return result

    def _is_valid_image_file(self, file_path: Path) -> bool:
        """Check if a file is a valid image by reading its header."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                return self._is_valid_image_header(header)
        except Exception:
            return False

    def _is_valid_image_header(self, header: bytes) -> bool:
        """Check if bytes represent a valid image file header."""
        # Common image file signatures
        image_signatures = [
            b'\xff\xd8\xff',           # JPEG
            b'\x89PNG\r\n\x1a\n',      # PNG
            b'GIF87a',                 # GIF87a
            b'GIF89a',                 # GIF89a
            b'BM',                     # BMP
            b'RIFF',                   # WebP (starts with RIFF)
            b'II*\x00',                # TIFF (little endian)
            b'MM\x00*',                # TIFF (big endian)
        ]
        
        return any(header.startswith(sig) for sig in image_signatures)

    def _natural_sort_key(self, text: str) -> List:
        """
        Generate a key for natural sorting (handles numeric sequences properly).
        Example: ['1.jpg', '2.jpg', '10.jpg'] instead of ['1.jpg', '10.jpg', '2.jpg']
        """
        import re
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        
        return [convert(c) for c in re.split(r'(\d+)', text)]

    def batch_analyze(self, file_paths: List[str]) -> List[FileFormatInfo]:
        """
        Analyze multiple files or directories for format detection.
        
        Args:
            file_paths: List of file or directory paths to analyze
            
        Returns:
            List of FileFormatInfo objects with detection results
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = self.detect_format(file_path)
                results.append(result)
            except Exception as e:
                # Create error result for failed analysis
                error_result = FileFormatInfo(
                    path=file_path,
                    error_message=f"Analysis failed: {str(e)}"
                )
                results.append(error_result)
                logger.error(f"Failed to analyze {file_path}: {e}")
        
        return results

    def get_supported_formats(self) -> List[Dict[str, Any]]:
        """Get information about all supported formats."""
        formats = []
        
        for format_type in SupportedFormat:
            format_info = {
                'format': format_type.value,
                'name': self._get_format_name(format_type),
                'description': self._get_format_description(format_type),
                'extensions': self._get_format_extensions(format_type),
                'validation_level': self._get_validation_level(format_type)
            }
            formats.append(format_info)
        
        return formats

    def _get_format_name(self, format_type: SupportedFormat) -> str:
        """Get human-readable name for format."""
        names = {
            SupportedFormat.CBZ: "Comic Book Archive (ZIP)",
            SupportedFormat.CBR: "Comic Book Archive (RAR)",
            SupportedFormat.PDF: "Portable Document Format",
            SupportedFormat.ZIP: "ZIP Archive",
            SupportedFormat.RAR: "RAR Archive",
            SupportedFormat.FOLDER: "Image Directory"
        }
        return names.get(format_type, format_type.value)

    def _get_format_description(self, format_type: SupportedFormat) -> str:
        """Get description for format."""
        descriptions = {
            SupportedFormat.CBZ: "ZIP archive containing comic book pages as images",
            SupportedFormat.CBR: "RAR archive containing comic book pages as images", 
            SupportedFormat.PDF: "PDF document with embedded images or pages",
            SupportedFormat.ZIP: "Generic ZIP archive (may contain images)",
            SupportedFormat.RAR: "Generic RAR archive (may contain images)",
            SupportedFormat.FOLDER: "Directory containing image files"
        }
        return descriptions.get(format_type, "Unknown format")

    def _get_format_extensions(self, format_type: SupportedFormat) -> List[str]:
        """Get file extensions for format."""
        extensions = {
            SupportedFormat.CBZ: ['.cbz'],
            SupportedFormat.CBR: ['.cbr'],
            SupportedFormat.PDF: ['.pdf'],
            SupportedFormat.ZIP: ['.zip'],
            SupportedFormat.RAR: ['.rar'],
            SupportedFormat.FOLDER: []  # No extension for directories
        }
        return extensions.get(format_type, [])

    def _get_validation_level(self, format_type: SupportedFormat) -> str:
        """Get validation level for format."""
        levels = {
            SupportedFormat.CBZ: "full",
            SupportedFormat.CBR: "basic",  # Limited without RAR library
            SupportedFormat.PDF: "basic",  # Limited without PDF library
            SupportedFormat.ZIP: "full",
            SupportedFormat.RAR: "basic",  # Limited without RAR library
            SupportedFormat.FOLDER: "full"
        }
        return levels.get(format_type, "none")