"""API endpoints for storage path management."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.users import current_active_user
from app.core.rate_limit import create_rate_limit_dependency
from app.services.storage import StoragePathService
from app.schemas.storage import (
    StoragePathCreate,
    StoragePathUpdate,
    StoragePathResponse,
    StoragePathValidationResult,
    StoragePathStats,
    BulkStoragePathOperation,
    BulkOperationResult,
    FileFormatInfo,
    FileFormatValidationRequest,
    FileFormatValidationResponse,
    SupportedFormatInfo,
    LibraryScanRequest,
    ScanProgressResponse,
    LibraryScanResponse
)

router = APIRouter()

# Rate limiters
read_rate_limit = create_rate_limit_dependency(max_requests=200, window_seconds=3600)  # 200 requests per hour
write_rate_limit = create_rate_limit_dependency(max_requests=50, window_seconds=3600)   # 50 requests per hour


def get_storage_service(db: AsyncSession = Depends(get_async_session)) -> StoragePathService:
    """Dependency to get StoragePathService instance."""
    return StoragePathService(db)


@router.get("/", response_model=List[StoragePathResponse])
async def get_storage_paths(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    accessible_only: bool = False,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(read_rate_limit),
) -> List[StoragePathResponse]:
    """Get all storage paths."""
    try:
        storage_paths = await service.get_all(
            skip=skip,
            limit=limit,
            active_only=active_only,
            accessible_only=accessible_only
        )
        return [StoragePathResponse.from_orm(sp) for sp in storage_paths]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve storage paths"
        )


@router.get("/stats", response_model=StoragePathStats)
async def get_storage_stats(
    request: Request,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(read_rate_limit),
) -> StoragePathStats:
    """Get storage path statistics."""
    try:
        return await service.get_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve storage statistics"
        )


@router.get("/{path_id}", response_model=StoragePathResponse)
async def get_storage_path(
    request: Request,
    path_id: int,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(read_rate_limit),
) -> StoragePathResponse:
    """Get a specific storage path."""
    try:
        storage_path = await service.get_by_id(path_id)
        
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage path not found"
            )
        
        return StoragePathResponse.from_orm(storage_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve storage path"
        )


@router.post("/", response_model=StoragePathResponse, status_code=status.HTTP_201_CREATED)
async def create_storage_path(
    request: Request,
    storage_path_in: StoragePathCreate,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> StoragePathResponse:
    """Create a new storage path."""
    try:
        storage_path = await service.create(storage_path_in)
        return StoragePathResponse.from_orm(storage_path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create storage path"
        )


@router.put("/{path_id}", response_model=StoragePathResponse)
async def update_storage_path(
    request: Request,
    path_id: int,
    storage_path_in: StoragePathUpdate,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> StoragePathResponse:
    """Update a storage path."""
    try:
        storage_path = await service.update(path_id, storage_path_in)
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage path not found"
            )
        
        return StoragePathResponse.from_orm(storage_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update storage path"
        )


@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_storage_path(
    request: Request,
    path_id: int,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> None:
    """Delete a storage path."""
    try:
        success = await service.delete(path_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage path not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete storage path"
        )


@router.post("/validate", response_model=StoragePathValidationResult)
async def validate_storage_path(
    request: Request,
    path: str,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(read_rate_limit),
) -> StoragePathValidationResult:
    """Validate a storage path without creating it."""
    try:
        return service.validate_path(path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate storage path"
        )


@router.post("/{path_id}/validate", response_model=StoragePathResponse)
async def revalidate_storage_path(
    request: Request,
    path_id: int,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> StoragePathResponse:
    """Revalidate an existing storage path."""
    try:
        storage_path = await service.revalidate_path(path_id)
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage path not found"
            )
        
        return StoragePathResponse.from_orm(storage_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revalidate storage path"
        )


@router.post("/bulk", response_model=BulkOperationResult)
async def bulk_storage_path_operation(
    request: Request,
    operation_in: BulkStoragePathOperation,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> BulkOperationResult:
    """Perform bulk operations on storage paths."""
    try:
        return await service.bulk_operation(operation_in.path_ids, operation_in.operation)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operation"
        )


@router.post("/{path_id}/activate", response_model=StoragePathResponse)
async def activate_storage_path(
    request: Request,
    path_id: int,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> StoragePathResponse:
    """Activate a storage path."""
    try:
        update_data = StoragePathUpdate(is_active=True)
        storage_path = await service.update(path_id, update_data)
        
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage path not found"
            )
        
        return StoragePathResponse.from_orm(storage_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate storage path"
        )


@router.post("/{path_id}/deactivate", response_model=StoragePathResponse)
async def deactivate_storage_path(
    request: Request,
    path_id: int,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> StoragePathResponse:
    """Deactivate a storage path."""
    try:
        update_data = StoragePathUpdate(is_active=False)
        storage_path = await service.update(path_id, update_data)
        
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage path not found"
            )
        
        return StoragePathResponse.from_orm(storage_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate storage path"
        )


# File Format Detection Endpoints

@router.get("/formats", response_model=List[SupportedFormatInfo])
async def get_supported_formats(
    request: Request,
    current_user = Depends(current_active_user),
    _rate_limit = Depends(read_rate_limit),
) -> List[SupportedFormatInfo]:
    """Get information about all supported file formats."""
    try:
        from app.services.file_format import FileFormatService
        service = FileFormatService()
        formats = service.get_supported_formats()
        return [SupportedFormatInfo(**fmt) for fmt in formats]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supported formats"
        )


@router.post("/validate-format", response_model=FileFormatInfo)
async def validate_single_file_format(
    request: Request,
    file_path: str,
    current_user = Depends(current_active_user),
    _rate_limit = Depends(read_rate_limit),
) -> FileFormatInfo:
    """Validate the format of a single file or directory."""
    try:
        from app.services.file_format import FileFormatService
        service = FileFormatService()
        result = service.detect_format(file_path)
        
        # Convert to Pydantic schema
        return FileFormatInfo(
            path=result.path,
            format_type=result.format_type,
            is_supported=result.is_supported,
            is_valid=result.is_valid,
            is_corrupted=result.is_corrupted,
            file_size=result.file_size,
            page_count=result.page_count,
            has_images=result.has_images,
            error_message=result.error_message,
            metadata=result.metadata
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate file format"
        )


@router.post("/validate-formats", response_model=FileFormatValidationResponse)
async def validate_multiple_file_formats(
    request: Request,
    validation_request: FileFormatValidationRequest,
    current_user = Depends(current_active_user),
    _rate_limit = Depends(read_rate_limit),
) -> FileFormatValidationResponse:
    """Validate the formats of multiple files or directories."""
    try:
        from app.services.file_format import FileFormatService
        service = FileFormatService()
        results = service.batch_analyze(validation_request.file_paths)
        
        # Convert to Pydantic schemas
        format_results = []
        supported_files = 0
        unsupported_files = 0
        corrupted_files = 0
        
        for result in results:
            format_info = FileFormatInfo(
                path=result.path,
                format_type=result.format_type,
                is_supported=result.is_supported,
                is_valid=result.is_valid,
                is_corrupted=result.is_corrupted,
                file_size=result.file_size,
                page_count=result.page_count,
                has_images=result.has_images,
                error_message=result.error_message,
                metadata=result.metadata
            )
            format_results.append(format_info)
            
            # Count statistics
            if result.is_supported:
                supported_files += 1
            else:
                unsupported_files += 1
                
            if result.is_corrupted:
                corrupted_files += 1
        
        return FileFormatValidationResponse(
            total_files=len(results),
            supported_files=supported_files,
            unsupported_files=unsupported_files,
            corrupted_files=corrupted_files,
            results=format_results
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate file formats"
        )


# Library Scan Endpoints

@router.post("/scan", response_model=LibraryScanResponse)
async def start_library_scan(
    request: Request,
    scan_request: LibraryScanRequest,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> LibraryScanResponse:
    """Start a manual library scan."""
    try:
        from app.services.library_scan import LibraryScanService
        scan_service = LibraryScanService(service.db)
        
        scan_id = await scan_service.start_manual_scan(
            storage_path_ids=scan_request.storage_path_ids,
            full_scan=scan_request.full_scan
        )
        
        return LibraryScanResponse(
            scan_id=scan_id,
            message="Library scan started successfully",
            status="running"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start library scan"
        )


@router.get("/scan/{scan_id}", response_model=ScanProgressResponse)
async def get_scan_progress(
    request: Request,
    scan_id: str,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(read_rate_limit),
) -> ScanProgressResponse:
    """Get progress information for a library scan."""
    try:
        from app.services.library_scan import LibraryScanService
        scan_service = LibraryScanService(service.db)
        
        progress = scan_service.get_scan_progress(scan_id)
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found"
            )
        
        progress_dict = progress.to_dict()
        return ScanProgressResponse(**progress_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scan progress"
        )


@router.get("/scans", response_model=List[ScanProgressResponse])
async def get_active_scans(
    request: Request,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(read_rate_limit),
) -> List[ScanProgressResponse]:
    """Get all active library scans."""
    try:
        from app.services.library_scan import LibraryScanService
        scan_service = LibraryScanService(service.db)
        
        active_scans = scan_service.get_active_scans()
        return [ScanProgressResponse(**scan) for scan in active_scans]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active scans"
        )


@router.post("/scan/{scan_id}/cancel", response_model=Dict[str, Any])
async def cancel_library_scan(
    request: Request,
    scan_id: str,
    current_user = Depends(current_active_user),
    service: StoragePathService = Depends(get_storage_service),
    _rate_limit = Depends(write_rate_limit),
) -> Dict[str, Any]:
    """Cancel a running library scan."""
    try:
        from app.services.library_scan import LibraryScanService
        scan_service = LibraryScanService(service.db)
        
        success = scan_service.cancel_scan(scan_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found or not running"
            )
        
        return {
            "scan_id": scan_id,
            "message": "Scan cancelled successfully",
            "status": "cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel scan"
        )