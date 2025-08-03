"""Library management API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    LibraryPathCreate,
    LibraryPathList,
    LibraryPathResponse,
    LibraryPathUpdate,
)
from kiremisu.services.library_path import LibraryPathService

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/paths", response_model=LibraryPathList)
async def get_library_paths(db: AsyncSession = Depends(get_db)) -> LibraryPathList:
    """Get all library paths."""
    paths = await LibraryPathService.get_all(db)
    return LibraryPathList(
        paths=[LibraryPathResponse.model_validate(path) for path in paths],
        total=len(paths),
    )


@router.get("/paths/{path_id}", response_model=LibraryPathResponse)
async def get_library_path(
    path_id: UUID, db: AsyncSession = Depends(get_db)
) -> LibraryPathResponse:
    """Get a specific library path by ID."""
    path = await LibraryPathService.get_by_id(db, path_id)
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Library path not found: {path_id}",
        )
    return LibraryPathResponse.model_validate(path)


@router.post("/paths", response_model=LibraryPathResponse, status_code=status.HTTP_201_CREATED)
async def create_library_path(
    library_path_data: LibraryPathCreate, db: AsyncSession = Depends(get_db)
) -> LibraryPathResponse:
    """Create a new library path."""
    try:
        path = await LibraryPathService.create(db, library_path_data)
        return LibraryPathResponse.model_validate(path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/paths/{path_id}", response_model=LibraryPathResponse)
async def update_library_path(
    path_id: UUID,
    update_data: LibraryPathUpdate,
    db: AsyncSession = Depends(get_db),
) -> LibraryPathResponse:
    """Update an existing library path."""
    try:
        path = await LibraryPathService.update(db, path_id, update_data)
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Library path not found: {path_id}",
            )
        return LibraryPathResponse.model_validate(path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/paths/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library_path(path_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a library path."""
    success = await LibraryPathService.delete(db, path_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Library path not found: {path_id}",
        )


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_library_scan(db: AsyncSession = Depends(get_db)) -> dict:
    """Trigger a manual scan of all enabled library paths."""
    # This will be implemented in LL-4 when we add the importer
    # For now, just return a placeholder response
    enabled_paths = await LibraryPathService.get_enabled_paths(db)
    return {
        "message": "Library scan initiated",
        "paths_to_scan": len(enabled_paths),
        "status": "queued",
    }
