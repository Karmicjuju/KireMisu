from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.users import current_active_user
from app.db.database import get_async_session
from app.services.library_path import LibraryPathService
from app.schemas.library_path import (
    LibraryPathCreate,
    LibraryPathUpdate,
    LibraryPathResponse,
    DirectoryBrowseResponse,
    PathValidationResult,
    StorageInfo
)
from app.models.user import User

router = APIRouter()


def get_library_path_service(db: AsyncSession = Depends(get_async_session)) -> LibraryPathService:
    """Dependency to get LibraryPathService instance."""
    return LibraryPathService(db)


@router.get("/", response_model=List[LibraryPathResponse])
async def get_library_paths(
    include_inactive: bool = Query(False, description="Include inactive library paths"),
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Get all library paths ordered by priority."""
    library_paths = await library_path_service.get_all_library_paths(include_inactive=include_inactive)
    return library_paths


@router.post("/", response_model=LibraryPathResponse, status_code=status.HTTP_201_CREATED)
async def create_library_path(
    library_path_data: LibraryPathCreate,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Create a new library path."""
    try:
        library_path = await library_path_service.create_library_path(library_path_data)
        return library_path
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create library path: {str(e)}"
        )


@router.get("/{library_path_id}", response_model=LibraryPathResponse)
async def get_library_path(
    library_path_id: int,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Get a library path by ID."""
    library_path = await library_path_service.get_library_path_by_id(library_path_id)
    if not library_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )
    return library_path


@router.put("/{library_path_id}", response_model=LibraryPathResponse)
async def update_library_path(
    library_path_id: int,
    library_path_data: LibraryPathUpdate,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Update a library path."""
    try:
        library_path = await library_path_service.update_library_path(library_path_id, library_path_data)
        if not library_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library path not found"
            )
        return library_path
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update library path: {str(e)}"
        )


@router.delete("/{library_path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library_path(
    library_path_id: int,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Delete a library path."""
    success = await library_path_service.delete_library_path(library_path_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )


@router.post("/validate-path", response_model=PathValidationResult)
async def validate_path(
    path: str = Query(..., description="Path to validate"),
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Validate a filesystem path for library usage."""
    try:
        validation_result = library_path_service.validate_path(path)
        return validation_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate path: {str(e)}"
        )


@router.post("/{library_path_id}/validate", response_model=PathValidationResult)
async def validate_library_path(
    library_path_id: int,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Validate an existing library path's accessibility."""
    library_path = await library_path_service.get_library_path_by_id(library_path_id)
    if not library_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )
    
    try:
        validation_result = library_path_service.validate_path(library_path.path)
        return validation_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate library path: {str(e)}"
        )


@router.get("/browse/{path:path}", response_model=DirectoryBrowseResponse)
async def browse_directory(
    path: str,
    show_hidden: bool = Query(False, description="Show hidden files and directories"),
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Browse directory structure for path selection."""
    try:
        browse_result = library_path_service.browse_directory(path, show_hidden=show_hidden)
        return browse_result
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found"
        )
    except NotADirectoryError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a directory"
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Directory is not accessible"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse directory: {str(e)}"
        )


@router.get("/{library_path_id}/storage-info", response_model=StorageInfo)
async def get_storage_info(
    library_path_id: int,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Get storage information for a library path."""
    storage_info = await library_path_service.get_storage_info(library_path_id)
    if not storage_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found or storage information unavailable"
        )
    return storage_info


@router.patch("/{library_path_id}/activate", response_model=LibraryPathResponse)
async def activate_library_path(
    library_path_id: int,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Activate a library path."""
    library_path = await library_path_service.activate_library_path(library_path_id)
    if not library_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )
    return library_path


@router.patch("/{library_path_id}/deactivate", response_model=LibraryPathResponse)
async def deactivate_library_path(
    library_path_id: int,
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Deactivate a library path."""
    library_path = await library_path_service.deactivate_library_path(library_path_id)
    if not library_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )
    return library_path


@router.patch("/{library_path_id}/priority", response_model=LibraryPathResponse)
async def update_priority(
    library_path_id: int,
    new_priority: int = Query(..., description="New priority value"),
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Update the priority of a library path."""
    library_path = await library_path_service.update_priority(library_path_id, new_priority)
    if not library_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )
    return library_path


@router.get("/{library_path_id}/scan-manga", response_model=List[str])
async def scan_for_manga_directories(
    library_path_id: int,
    max_depth: int = Query(2, ge=1, le=5, description="Maximum directory depth to scan"),
    library_path_service: LibraryPathService = Depends(get_library_path_service),
    current_user: User = Depends(current_active_user)
):
    """Scan a library path for directories that might contain manga."""
    library_path = await library_path_service.get_library_path_by_id(library_path_id)
    if not library_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library path not found"
        )
    
    try:
        manga_directories = await library_path_service.scan_for_manga_directories(
            library_path_id, max_depth=max_depth
        )
        return manga_directories
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan for manga directories: {str(e)}"
        )