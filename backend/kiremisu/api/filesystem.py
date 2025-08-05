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
    path: str = Query("/", description="Directory path to browse"),
    show_hidden: bool = Query(False, description="Show hidden files and directories")
) -> DirectoryListing:
    """
    Browse filesystem directories on the server.
    
    Security considerations:
    - Only allows browsing within the container filesystem
    - Validates path to prevent directory traversal attacks
    - Does not expose sensitive system directories
    """
    try:
        # Normalize the path
        dir_path = Path(path).resolve()
        
        # Security check: ensure we're not browsing sensitive system directories
        forbidden_paths = [
            "/etc", "/proc", "/sys", "/dev", "/boot", "/root",
            "/var/log", "/usr/bin", "/usr/sbin", "/sbin", "/bin"
        ]
        
        # Check if the path starts with any forbidden directory
        path_str = str(dir_path)
        if any(path_str.startswith(forbidden) for forbidden in forbidden_paths):
            raise HTTPException(
                status_code=403, 
                detail="Access to this directory is not allowed"
            )
        
        # Check if directory exists and is accessible
        if not dir_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        if not os.access(dir_path, os.R_OK):
            raise HTTPException(status_code=403, detail="Directory is not readable")
        
        # Get parent directory
        parent_path = str(dir_path.parent) if dir_path.parent != dir_path else None
        
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
    Validate if a path exists and is a directory.
    """
    try:
        dir_path = Path(path).resolve()
        
        return {
            "exists": dir_path.exists(),
            "is_directory": dir_path.is_dir() if dir_path.exists() else False,
            "readable": os.access(dir_path, os.R_OK) if dir_path.exists() else False,
            "path": str(dir_path)
        }
    except Exception as e:
        return {
            "exists": False,
            "is_directory": False,
            "readable": False,
            "error": str(e),
            "path": path
        }