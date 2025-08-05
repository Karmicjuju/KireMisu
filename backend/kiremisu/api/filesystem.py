"""
Filesystem browsing API endpoints.
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


class DirectoryItem(BaseModel):
    """A filesystem item (file or directory)."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[int] = None


class DirectoryListing(BaseModel):
    """Response for directory listing."""
    current_path: str
    parent_path: Optional[str]
    items: List[DirectoryItem]


@router.get("/browse", response_model=DirectoryListing)
async def browse_directory(
    path: str = Query("/manga-storage", description="Directory path to browse"),
    show_hidden: bool = Query(False, description="Show hidden files and directories")
) -> DirectoryListing:
    """
    Browse manga storage directories on the server.
    
    Security considerations:
    - Only allows browsing within /manga-storage (manga library mount point)
    - Uses whitelist approach to prevent any path traversal attacks
    - Validates all paths are within the allowed storage directory
    """
    try:
        # Define the allowed base directory for manga storage
        MANGA_STORAGE_BASE = Path("/manga-storage").resolve()
        
        # Normalize and resolve the requested path
        requested_path = Path(path).resolve()
        
        # Security check: ensure the resolved path is within manga storage
        try:
            # This will raise ValueError if requested_path is not within MANGA_STORAGE_BASE
            requested_path.relative_to(MANGA_STORAGE_BASE)
        except ValueError:
            raise HTTPException(
                status_code=403, 
                detail="Access denied. Only manga storage directories are accessible."
            )
        
        # Additional security: ensure we haven't been tricked by symlinks or other path traversal
        if not str(requested_path).startswith(str(MANGA_STORAGE_BASE)):
            raise HTTPException(
                status_code=403, 
                detail="Access denied. Path is outside manga storage area."
            )
        
        # Check if directory exists and is accessible
        if not requested_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        if not requested_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        if not os.access(requested_path, os.R_OK):
            raise HTTPException(status_code=403, detail="Directory is not readable")
        
        # Use the validated path
        dir_path = requested_path
        
        # Get parent directory (only if it's still within manga storage)
        parent_path = None
        if dir_path.parent != dir_path and dir_path != MANGA_STORAGE_BASE:
            try:
                # Ensure parent is still within manga storage
                dir_path.parent.relative_to(MANGA_STORAGE_BASE)
                parent_path = str(dir_path.parent)
            except ValueError:
                # Parent is outside manga storage, don't provide it
                pass
        
        # List directory contents
        items = []
        try:
            for item in dir_path.iterdir():
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                try:
                    stat = item.stat()
                    items.append(DirectoryItem(
                        name=item.name,
                        path=str(item),
                        is_directory=item.is_dir(),
                        size=stat.st_size if item.is_file() else None,
                        modified=int(stat.st_mtime)
                    ))
                except (OSError, PermissionError):
                    # Skip items we can't access
                    continue
                    
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Sort items: directories first, then files, both alphabetically
        items.sort(key=lambda x: (not x.is_directory, x.name.lower()))
        
        return DirectoryListing(
            current_path=str(dir_path),
            parent_path=parent_path,
            items=items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error browsing directory: {str(e)}")


@router.get("/validate-path")
async def validate_path(path: str = Query(..., description="Path to validate")) -> dict:
    """
    Validate if a path exists and is a directory within manga storage.
    """
    try:
        # Define the allowed base directory for manga storage
        MANGA_STORAGE_BASE = Path("/manga-storage").resolve()
        
        # Normalize and resolve the requested path
        requested_path = Path(path).resolve()
        
        # Security check: ensure the resolved path is within manga storage
        try:
            requested_path.relative_to(MANGA_STORAGE_BASE)
        except ValueError:
            return {
                "exists": False,
                "is_directory": False,
                "readable": False,
                "error": "Path is outside manga storage area",
                "path": path
            }
        
        # Additional security check
        if not str(requested_path).startswith(str(MANGA_STORAGE_BASE)):
            return {
                "exists": False,
                "is_directory": False,
                "readable": False,
                "error": "Path is outside manga storage area",
                "path": path
            }
        
        return {
            "exists": requested_path.exists(),
            "is_directory": requested_path.is_dir() if requested_path.exists() else False,
            "readable": os.access(requested_path, os.R_OK) if requested_path.exists() else False,
            "path": str(requested_path)
        }
    except Exception as e:
        return {
            "exists": False,
            "is_directory": False,
            "readable": False,
            "error": str(e),
            "path": path
        }