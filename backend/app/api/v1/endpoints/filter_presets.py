"""API endpoints for filter preset management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_async_session
from app.services.filter_preset import FilterPresetService
from app.schemas.filters import (
    FilterPresetCreate, 
    FilterPresetUpdate, 
    FilterPresetResponse, 
    FilterPresetListResponse
)
from app.users import current_active_user
from app.core.rate_limit import create_rate_limit_dependency

# Setup logging
logger = logging.getLogger(__name__)

# Rate limiting dependencies
read_rate_limit = create_rate_limit_dependency(max_requests=100, window_seconds=3600)  # 100 reads per hour
write_rate_limit = create_rate_limit_dependency(max_requests=20, window_seconds=3600)   # 20 writes per hour

router = APIRouter()


def get_filter_preset_service(db: AsyncSession = Depends(get_async_session)) -> FilterPresetService:
    """Dependency to get FilterPresetService instance."""
    return FilterPresetService(db)


@router.get("/", response_model=FilterPresetListResponse)
async def get_filter_presets(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    include_public: bool = Query(True, description="Include public presets"),
    search: Optional[str] = Query(None, description="Search presets by name or description"),
    current_user = Depends(current_active_user),
    preset_service: FilterPresetService = Depends(get_filter_preset_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get paginated list of filter presets for the current user.
    
    - **page**: Page number (starts from 1)
    - **size**: Number of items per page (max 100)
    - **include_public**: Whether to include public presets
    - **search**: Search in preset name or description
    """
    try:
        if search:
            return await preset_service.search_presets_paginated(
                query=search,
                user_id=str(current_user.id),
                page=page,
                size=size,
                include_public=include_public
            )
        else:
            return await preset_service.get_user_presets_paginated(
                user_id=str(current_user.id),
                page=page,
                size=size,
                include_public=include_public
            )
    except ValueError as e:
        logger.warning(f"Invalid request in get_filter_presets: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_filter_presets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving filter presets"
        )


@router.post("/", response_model=FilterPresetResponse, status_code=status.HTTP_201_CREATED)
async def create_filter_preset(
    request: Request,
    preset_data: FilterPresetCreate,
    current_user = Depends(current_active_user),
    preset_service: FilterPresetService = Depends(get_filter_preset_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Create a new filter preset.
    
    - **name**: Preset name (required)
    - **description**: Preset description (optional)
    - **filters**: Filter parameters (required)
    - **sorting**: Sort parameters (optional)
    - **is_public**: Whether preset is accessible to other users (default: false)
    """
    try:
        preset = await preset_service.create_preset(preset_data, str(current_user.id))
        return preset_service._convert_to_response(preset)
    except ValueError as e:
        logger.warning(f"Invalid request in create_filter_preset: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_filter_preset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the filter preset"
        )


@router.get("/{preset_id}", response_model=FilterPresetResponse)
async def get_filter_preset_by_id(
    request: Request,
    preset_id: int,
    current_user = Depends(current_active_user),
    preset_service: FilterPresetService = Depends(get_filter_preset_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get a filter preset by ID.
    
    - **preset_id**: The ID of the preset to retrieve
    """
    preset = await preset_service.get_preset_by_id(preset_id, str(current_user.id))
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Filter preset with ID {preset_id} not found"
        )
    
    return preset_service._convert_to_response(preset)


@router.patch("/{preset_id}", response_model=FilterPresetResponse)
async def update_filter_preset(
    request: Request,
    preset_id: int,
    preset_data: FilterPresetUpdate,
    current_user = Depends(current_active_user),
    preset_service: FilterPresetService = Depends(get_filter_preset_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Update a filter preset.
    
    - **preset_id**: The ID of the preset to update
    - All fields are optional and will only be updated if provided
    """
    try:
        updated_preset = await preset_service.update_preset(
            preset_id=preset_id,
            preset_data=preset_data,
            user_id=str(current_user.id)
        )
        
        if not updated_preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Filter preset with ID {preset_id} not found or access denied"
            )
        
        return preset_service._convert_to_response(updated_preset)
    except ValueError as e:
        logger.warning(f"Invalid request in update_filter_preset: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in update_filter_preset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the filter preset"
        )


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter_preset(
    request: Request,
    preset_id: int,
    current_user = Depends(current_active_user),
    preset_service: FilterPresetService = Depends(get_filter_preset_service),
    _rate_limit = Depends(write_rate_limit),
):
    """
    Delete a filter preset.
    
    - **preset_id**: The ID of the preset to delete
    """
    try:
        success = await preset_service.delete_preset(preset_id, str(current_user.id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Filter preset with ID {preset_id} not found or access denied"
            )
    except ValueError as e:
        logger.warning(f"Invalid request in delete_filter_preset: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in delete_filter_preset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the filter preset"
        )


@router.get("/public/", response_model=FilterPresetListResponse)
async def get_public_filter_presets(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user = Depends(current_active_user),
    preset_service: FilterPresetService = Depends(get_filter_preset_service),
    _rate_limit = Depends(read_rate_limit),
):
    """
    Get paginated list of public filter presets.
    
    - **page**: Page number (starts from 1)
    - **size**: Number of items per page (max 100)
    """
    try:
        return await preset_service.get_public_presets_paginated(page=page, size=size)
    except ValueError as e:
        logger.warning(f"Invalid request in get_public_filter_presets: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_public_filter_presets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving public filter presets"
        )