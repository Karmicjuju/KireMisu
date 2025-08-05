"""API endpoints for safe file operations."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    FileOperationRequest,
    FileOperationResponse,
    FileOperationConfirmationRequest,
    FileOperationListResponse,
    ValidationResult,
)
from kiremisu.services.file_operations import FileOperationService, FileOperationError

router = APIRouter(prefix="/api/file-operations", tags=["file-operations"])


@router.post("/", response_model=FileOperationResponse)
async def create_file_operation(
    request: FileOperationRequest,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Create a new file operation with initial validation.
    
    This endpoint creates a file operation record and performs basic validation.
    The operation is not executed until explicitly confirmed.
    """
    try:
        async with FileOperationService() as service:
            return await service.create_operation(db, request)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{operation_id}/validate", response_model=ValidationResult)
async def validate_file_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ValidationResult:
    """Perform comprehensive validation of a file operation.
    
    This endpoint validates the operation and returns detailed results including:
    - File system validation
    - Database consistency checks  
    - Risk assessment
    - Conflict detection
    """
    try:
        async with FileOperationService() as service:
            return await service.validate_operation(db, operation_id)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{operation_id}/execute", response_model=FileOperationResponse)
async def execute_file_operation(
    operation_id: UUID,
    confirmation: FileOperationConfirmationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Execute a validated file operation after user confirmation.
    
    This endpoint executes the file operation if the user has confirmed it.
    The operation includes backup creation and database updates.
    """
    if confirmation.operation_id != operation_id:
        raise HTTPException(status_code=400, detail="Operation ID mismatch")
    
    if not confirmation.confirmed:
        raise HTTPException(status_code=400, detail="Operation not confirmed by user")

    try:
        async with FileOperationService() as service:
            return await service.execute_operation(db, operation_id)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{operation_id}/rollback", response_model=FileOperationResponse)
async def rollback_file_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Rollback a completed or failed file operation.
    
    This endpoint attempts to rollback the file operation using stored backups
    and reverting database changes.
    """
    try:
        async with FileOperationService() as service:
            return await service.rollback_operation(db, operation_id)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{operation_id}", response_model=FileOperationResponse)
async def get_file_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Get details of a specific file operation."""
    try:
        async with FileOperationService() as service:
            operation = await service.get_operation(db, operation_id)
            if not operation:
                raise HTTPException(status_code=404, detail="Operation not found")
            return operation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/", response_model=FileOperationListResponse)
async def list_file_operations(
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by operation status"),
    operation_type_filter: Optional[str] = Query(None, description="Filter by operation type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of operations to return"),
    offset: int = Query(0, ge=0, description="Number of operations to skip"),
) -> FileOperationListResponse:
    """List file operations with optional filtering."""
    try:
        async with FileOperationService() as service:
            operations = await service.list_operations(
                db, status_filter, operation_type_filter, limit, offset
            )
            return FileOperationListResponse(
                operations=operations,
                total=len(operations),
                status_filter=status_filter,
                operation_type_filter=operation_type_filter,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/cleanup", response_model=dict)
async def cleanup_old_operations(
    db: AsyncSession = Depends(get_db),
    days_old: int = Query(30, ge=1, le=365, description="Clean up operations older than this many days"),
) -> dict:
    """Clean up old completed operations and their backups.
    
    This endpoint removes old operation records and associated backup files
    to free up disk space and keep the operation log manageable.
    """
    try:
        async with FileOperationService() as service:
            cleaned_count = await service.cleanup_old_operations(db, days_old)
            return {
                "status": "completed",
                "message": f"Cleaned up {cleaned_count} old operations",
                "cleaned_count": cleaned_count,
                "days_old": days_old,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Convenience endpoints for common operations
@router.post("/rename", response_model=FileOperationResponse)
async def rename_file_or_directory(
    source_path: str,
    target_path: str,
    force: bool = False,
    create_backup: bool = True,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Convenience endpoint for renaming files or directories.
    
    This endpoint creates a rename operation with default safety settings.
    """
    request = FileOperationRequest(
        operation_type="rename",
        source_path=source_path,
        target_path=target_path,
        force=force,
        create_backup=create_backup,
    )
    
    try:
        async with FileOperationService() as service:
            return await service.create_operation(db, request)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/delete", response_model=FileOperationResponse)
async def delete_file_or_directory(
    source_path: str,
    force: bool = False,
    create_backup: bool = True,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Convenience endpoint for deleting files or directories.
    
    This endpoint creates a delete operation with default safety settings.
    Always requires backup creation unless explicitly disabled.
    """
    request = FileOperationRequest(
        operation_type="delete",
        source_path=source_path,
        force=force,
        create_backup=create_backup,
    )
    
    try:
        async with FileOperationService() as service:
            return await service.create_operation(db, request)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/move", response_model=FileOperationResponse)
async def move_file_or_directory(
    source_path: str,
    target_path: str,
    force: bool = False,
    create_backup: bool = True,
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """Convenience endpoint for moving files or directories.
    
    This endpoint creates a move operation with default safety settings.
    """
    request = FileOperationRequest(
        operation_type="move",
        source_path=source_path,
        target_path=target_path,
        force=force,
        create_backup=create_backup,
    )
    
    try:
        async with FileOperationService() as service:
            return await service.create_operation(db, request)
    except FileOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")