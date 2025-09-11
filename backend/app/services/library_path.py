import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library_path import LibraryPath
from app.repositories.library_path import LibraryPathRepository
from app.schemas.library_path import (
    LibraryPathCreate,
    LibraryPathUpdate,
    DirectoryItem,
    DirectoryBrowseResponse,
    PathValidationResult,
    StorageInfo
)


class LibraryPathService:
    """Service layer for library path management and validation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.library_path_repo = LibraryPathRepository(db)
    
    async def create_library_path(self, library_path_data: LibraryPathCreate) -> LibraryPath:
        """Create a new library path with validation."""
        # Normalize the path
        normalized_path = os.path.normpath(library_path_data.path)
        library_path_data.path = normalized_path
        
        # Check if path already exists
        if await self.library_path_repo.is_path_taken(normalized_path):
            raise ValueError(f"Path '{normalized_path}' is already configured")
        
        # Check if name already exists
        if await self.library_path_repo.is_name_taken(library_path_data.name):
            raise ValueError(f"Name '{library_path_data.name}' is already in use")
        
        return await self.library_path_repo.create_library_path(library_path_data)
    
    async def get_library_path_by_id(self, library_path_id: int) -> Optional[LibraryPath]:
        """Get library path by ID."""
        return await self.library_path_repo.get_library_path_by_id(library_path_id)
    
    async def get_all_library_paths(self, include_inactive: bool = False) -> List[LibraryPath]:
        """Get all library paths ordered by priority."""
        return await self.library_path_repo.get_all_library_paths(include_inactive)
    
    async def get_active_library_paths(self) -> List[LibraryPath]:
        """Get only active library paths."""
        return await self.library_path_repo.get_active_library_paths()
    
    async def update_library_path(self, library_path_id: int, library_path_data: LibraryPathUpdate) -> Optional[LibraryPath]:
        """Update library path with validation."""
        existing_path = await self.library_path_repo.get_library_path_by_id(library_path_id)
        if not existing_path:
            return None
        
        # Check if new name would conflict with another path
        if library_path_data.name is not None:
            if await self.library_path_repo.is_name_taken(library_path_data.name, exclude_id=library_path_id):
                raise ValueError(f"Name '{library_path_data.name}' is already in use")
        
        return await self.library_path_repo.update_library_path(library_path_id, library_path_data)
    
    async def delete_library_path(self, library_path_id: int) -> bool:
        """Delete library path."""
        return await self.library_path_repo.delete_library_path(library_path_id)
    
    def validate_path(self, path: str) -> PathValidationResult:
        """Validate a filesystem path for library usage."""
        normalized_path = os.path.normpath(path)
        
        result = PathValidationResult(
            is_valid=False,
            exists=False,
            is_directory=False,
            is_readable=False,
            is_writable=False,
            error_message=None,
            total_space=None,
            free_space=None
        )
        
        try:
            # Check if path exists
            result.exists = os.path.exists(normalized_path)
            
            if not result.exists:
                result.error_message = "Path does not exist"
                return result
            
            # Check if it's a directory
            result.is_directory = os.path.isdir(normalized_path)
            
            if not result.is_directory:
                result.error_message = "Path is not a directory"
                return result
            
            # Check permissions
            result.is_readable = os.access(normalized_path, os.R_OK)
            result.is_writable = os.access(normalized_path, os.W_OK)
            
            if not result.is_readable:
                result.error_message = "Directory is not readable"
                return result
            
            # Get disk usage information
            try:
                total, used, free = shutil.disk_usage(normalized_path)
                result.total_space = total
                result.free_space = free
            except Exception:
                # Not critical if we can't get disk usage
                pass
            
            # Path is valid if it exists, is a directory, and is readable
            result.is_valid = result.exists and result.is_directory and result.is_readable
            
            if not result.is_writable:
                # Warning but still valid for read-only libraries
                result.error_message = "Directory is read-only (will be accessible but not writable)"
            
        except Exception as e:
            result.error_message = f"Error validating path: {str(e)}"
        
        return result
    
    def browse_directory(self, path: str, show_hidden: bool = False) -> DirectoryBrowseResponse:
        """Browse directory contents for path selection."""
        normalized_path = os.path.normpath(path)
        
        if not os.path.exists(normalized_path):
            raise FileNotFoundError(f"Path does not exist: {normalized_path}")
        
        if not os.path.isdir(normalized_path):
            raise NotADirectoryError(f"Path is not a directory: {normalized_path}")
        
        if not os.access(normalized_path, os.R_OK):
            raise PermissionError(f"Directory is not readable: {normalized_path}")
        
        items = []
        
        try:
            for entry in os.listdir(normalized_path):
                # Skip hidden files/directories unless requested
                if not show_hidden and entry.startswith('.'):
                    continue
                
                item_path = os.path.join(normalized_path, entry)
                
                try:
                    stat_info = os.stat(item_path)
                    is_directory = os.path.isdir(item_path)
                    
                    item = DirectoryItem(
                        name=entry,
                        path=item_path,
                        is_directory=is_directory,
                        size=stat_info.st_size if not is_directory else None,
                        modified_at=datetime.fromtimestamp(stat_info.st_mtime)
                    )
                    items.append(item)
                    
                except (OSError, PermissionError):
                    # Skip items we can't access
                    continue
            
            # Sort items: directories first, then by name
            items.sort(key=lambda x: (not x.is_directory, x.name.lower()))
            
        except Exception as e:
            raise PermissionError(f"Error reading directory: {str(e)}")
        
        # Get parent directory path
        parent_path = None
        path_obj = Path(normalized_path)
        if path_obj.parent != path_obj:  # Not root directory
            parent_path = str(path_obj.parent)
        
        return DirectoryBrowseResponse(
            current_path=normalized_path,
            parent_path=parent_path,
            items=items,
            total_items=len(items)
        )
    
    async def get_storage_info(self, library_path_id: int) -> Optional[StorageInfo]:
        """Get storage information for a library path."""
        library_path = await self.library_path_repo.get_library_path_by_id(library_path_id)
        if not library_path:
            return None
        
        try:
            total, used, free = shutil.disk_usage(library_path.path)
            usage_percentage = (used / total) * 100 if total > 0 else 0
            
            return StorageInfo(
                total_space=total,
                used_space=used,
                free_space=free,
                usage_percentage=round(usage_percentage, 2)
            )
        except Exception:
            return None
    
    async def update_priority(self, library_path_id: int, new_priority: int) -> Optional[LibraryPath]:
        """Update the priority of a library path."""
        return await self.library_path_repo.update_priority(library_path_id, new_priority)
    
    async def activate_library_path(self, library_path_id: int) -> Optional[LibraryPath]:
        """Activate a library path."""
        return await self.library_path_repo.activate_library_path(library_path_id)
    
    async def deactivate_library_path(self, library_path_id: int) -> Optional[LibraryPath]:
        """Deactivate a library path."""
        return await self.library_path_repo.deactivate_library_path(library_path_id)
    
    async def reorder_priorities(self, path_id_priority_pairs: List[Tuple[int, int]]) -> List[LibraryPath]:
        """Reorder multiple library paths by updating their priorities."""
        updated_paths = []
        
        for path_id, priority in path_id_priority_pairs:
            updated_path = await self.library_path_repo.update_priority(path_id, priority)
            if updated_path:
                updated_paths.append(updated_path)
        
        return updated_paths
    
    async def get_next_priority(self) -> int:
        """Get the next available priority value (one higher than current max)."""
        highest_priority = await self.library_path_repo.get_highest_priority()
        return highest_priority + 1
    
    async def scan_for_manga_directories(self, library_path_id: int, max_depth: int = 2) -> List[str]:
        """Scan a library path for directories that might contain manga."""
        library_path = await self.library_path_repo.get_library_path_by_id(library_path_id)
        if not library_path:
            return []
        
        manga_directories = []
        
        def is_manga_directory(dir_path: str) -> bool:
            """Check if directory might contain manga based on file extensions."""
            manga_extensions = {'.cbz', '.cbr', '.zip', '.rar', '.pdf'}
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            
            try:
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        ext = os.path.splitext(item.lower())[1]
                        if ext in manga_extensions or ext in image_extensions:
                            return True
            except (OSError, PermissionError):
                pass
            
            return False
        
        def scan_directory(current_path: str, current_depth: int):
            """Recursively scan directories up to max_depth."""
            if current_depth > max_depth:
                return
            
            try:
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)
                    
                    if os.path.isdir(item_path):
                        # Check if this directory contains manga
                        if is_manga_directory(item_path):
                            manga_directories.append(item_path)
                        
                        # Continue scanning subdirectories
                        scan_directory(item_path, current_depth + 1)
                        
            except (OSError, PermissionError):
                pass
        
        try:
            scan_directory(library_path.path, 0)
        except Exception:
            pass
        
        return sorted(manga_directories)