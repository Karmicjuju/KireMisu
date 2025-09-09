"""Pydantic schemas for search functionality."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SearchQuery(BaseModel):
    """Schema for search query parameters."""
    
    q: str = Field(..., min_length=1, max_length=200, description="Search query")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: Optional[int] = Field(0, ge=0, description="Offset for pagination")
    
    @field_validator('q')
    @classmethod
    def validate_query(cls, v):
        """Validate and sanitize search query."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        
        # Basic sanitization
        sanitized = v.strip()
        
        # Check for minimum length after stripping
        if len(sanitized) < 1:
            raise ValueError("Search query too short")
            
        return sanitized


class AutocompleteQuery(BaseModel):
    """Schema for autocomplete query parameters."""
    
    q: str = Field(..., min_length=2, max_length=100, description="Partial search query")
    limit: Optional[int] = Field(10, ge=1, le=20, description="Maximum suggestions to return")
    
    @field_validator('q')
    @classmethod
    def validate_query(cls, v):
        """Validate autocomplete query."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        
        sanitized = v.strip()
        if len(sanitized) < 2:
            raise ValueError("Query must be at least 2 characters")
            
        return sanitized


class SearchResultSeries(BaseModel):
    """Schema for series in search results."""
    
    id: int
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    artist: Optional[str] = None
    status: Optional[str] = None
    cover_path: Optional[str] = None
    
    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Schema for search response."""
    
    results: List[SearchResultSeries]
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Results limit used")
    offset: int = Field(..., description="Results offset used")
    query: str = Field(..., description="Original search query")
    
    
class AutocompleteResponse(BaseModel):
    """Schema for autocomplete response."""
    
    suggestions: List[str] = Field(..., description="List of search suggestions")
    query: str = Field(..., description="Original partial query")


class RecentSearchesResponse(BaseModel):
    """Schema for recent searches response."""
    
    searches: List[str] = Field(..., description="List of recent search queries")