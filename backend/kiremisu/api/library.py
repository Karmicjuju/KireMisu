"""Library management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    LibraryPathCreate,
    LibraryPathList,
    LibraryPathResponse,
    LibraryPathUpdate,
    LibraryScanRequest,
    LibraryScanResponse,
    LibraryScanStats,
)
from kiremisu.services.importer import ImporterService
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


@router.post("/scan", response_model=LibraryScanResponse)
async def scan_library(
    scan_request: LibraryScanRequest, db: AsyncSession = Depends(get_db)
) -> LibraryScanResponse:
    """Scan library paths and import/update series and chapters.

    Args:
        scan_request: Request containing optional library_path_id to scan specific path
        db: Database session

    Returns:
        LibraryScanResponse: Scan results with statistics
    """
    # Validate library_path_id exists if provided
    if scan_request.library_path_id:
        library_path = await LibraryPathService.get_by_id(db, scan_request.library_path_id)
        if not library_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Library path not found: {scan_request.library_path_id}",
            )

    importer = ImporterService()

    try:
        # Execute the scan (synchronous for now, will be async job in LL-5)
        stats = await importer.scan_library_paths(
            db=db, library_path_id=scan_request.library_path_id
        )

        # Determine status based on errors
        status_text = "completed" if stats.errors == 0 else "completed_with_errors"

        # Build message
        if scan_request.library_path_id:
            message = f"Library path scan {status_text}"
        else:
            message = f"Library scan {status_text}"

        if stats.errors > 0:
            message += f" ({stats.errors} errors encountered)"

        return LibraryScanResponse(
            status=status_text, message=message, stats=LibraryScanStats(**stats.to_dict())
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Library scan failed: {str(e)}",
        )
