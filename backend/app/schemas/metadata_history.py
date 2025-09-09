from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MetadataHistoryBase(BaseModel):
    """Base schema for metadata history."""
    entity_type: str = Field(..., description="Type of entity (series or chapter)")
    entity_id: int = Field(..., description="ID of the entity")
    action: str = Field(..., description="Action performed (create, update, delete)")
    description: Optional[str] = Field(None, description="Optional description of the change")


class MetadataHistoryResponse(MetadataHistoryBase):
    """Schema for metadata history responses."""
    id: int
    user_id: Optional[int] = None
    previous_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MetadataHistoryWithUserResponse(MetadataHistoryResponse):
    """Schema for metadata history responses with user details."""
    user: Optional[Dict[str, Any]] = None  # Will contain username and email
    
    class Config:
        from_attributes = True


class ChangePreviewResponse(BaseModel):
    """Schema for previewing changes before applying them."""
    changes: Dict[str, Dict[str, Any]] = Field(..., description="Fields that will be modified")
    additions: Dict[str, Any] = Field(..., description="New fields that will be added")
    removals: Dict[str, Any] = Field(..., description="Fields that will be removed")


class EntityStatisticsResponse(BaseModel):
    """Schema for entity change statistics."""
    total_changes: int = Field(..., description="Total number of changes")
    change_types: Dict[str, int] = Field(..., description="Count of each change type")
    most_active_users: List[tuple] = Field(..., description="Most active users by change count")
    most_changed_fields: List[tuple] = Field(..., description="Most frequently changed fields")


class HistoryListResponse(BaseModel):
    """Schema for paginated history list responses."""
    items: List[MetadataHistoryWithUserResponse]
    total: int
    page: int
    size: int
    
    class Config:
        from_attributes = True