"""Search API endpoints for manga library search functionality."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.users import current_active_user
from app.core.rate_limit import create_rate_limit_dependency
from app.models.user import User
from app.services.search import SearchService
from app.schemas.search import (
    SearchQuery,
    SearchResponse,
    AutocompleteQuery,
    AutocompleteResponse,
    RecentSearchesResponse,
)

logger = logging.getLogger(__name__)

# Rate limiting dependencies
search_rate_limit = create_rate_limit_dependency(max_requests=100, window_seconds=3600)  # 100 searches per hour
autocomplete_rate_limit = create_rate_limit_dependency(max_requests=200, window_seconds=3600)  # 200 autocompletes per hour

router = APIRouter()


def get_search_service(db: AsyncSession = Depends(get_async_session)) -> SearchService:
    """Dependency to get SearchService instance."""
    return SearchService(db)


@router.get("/", response_model=SearchResponse)
async def search_series(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(current_active_user),
    search_service: SearchService = Depends(get_search_service),
    _rate_limit = Depends(search_rate_limit),
) -> SearchResponse:
    """
    Search manga series with full-text search.
    
    Supports:
    - Full-text search across title, author, artist, description
    - Advanced filters like author:name, status:completed
    - Search ranking by relevance
    - Pagination
    - Search history tracking (for authenticated users)
    """
    try:
        # Validate search query
        search_query = SearchQuery(q=q, limit=limit or 20, offset=offset or 0)
        
        # Get user ID if authenticated
        user_id = current_user.id if current_user else None
        
        # Perform search
        results, total = await search_service.search_series(
            query=search_query.q,
            user_id=user_id,
            limit=search_query.limit,
            offset=search_query.offset
        )
        
        return SearchResponse(
            results=results,
            total=total,
            limit=search_query.limit,
            offset=search_query.offset,
            query=search_query.q
        )
        
    except ValueError as e:
        # Log the full error for debugging but return generic message
        logger.error(f"Search validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid search parameters")
    except Exception as e:
        # Log the detailed error internally
        logger.error(f"Search service error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search service temporarily unavailable")


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def get_autocomplete_suggestions(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Partial search query"),
    limit: Optional[int] = Query(10, ge=1, le=20, description="Maximum suggestions"),
    search_service: SearchService = Depends(get_search_service),
    _rate_limit = Depends(autocomplete_rate_limit),
) -> AutocompleteResponse:
    """
    Get autocomplete suggestions for search queries.
    
    Returns suggestions from:
    - Series titles
    - Author names
    - Artist names
    
    Results are ranked by relevance and popularity.
    """
    try:
        # Validate autocomplete query
        autocomplete_query = AutocompleteQuery(q=q, limit=limit or 10)
        
        # Get suggestions
        suggestions = await search_service.get_search_suggestions(
            partial_query=autocomplete_query.q,
            limit=autocomplete_query.limit
        )
        
        return AutocompleteResponse(
            suggestions=suggestions,
            query=autocomplete_query.q
        )
        
    except ValueError as e:
        # Log the full error for debugging but return generic message
        logger.error(f"Autocomplete validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid autocomplete parameters")
    except Exception as e:
        # Log the detailed error internally
        logger.error(f"Autocomplete service error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Autocomplete service temporarily unavailable")


@router.get("/recent", response_model=RecentSearchesResponse)
async def get_recent_searches(
    request: Request,
    limit: Optional[int] = Query(10, ge=1, le=20, description="Maximum recent searches"),
    current_user = Depends(current_active_user),
    search_service: SearchService = Depends(get_search_service),
    _rate_limit = Depends(search_rate_limit),
) -> RecentSearchesResponse:
    """
    Get recent search queries for the current user.
    
    Requires authentication.
    Returns the user's recent searches ordered by recency.
    """
    try:
        # Get recent searches
        recent_searches = await search_service.get_recent_searches(
            user_id=current_user.id,
            limit=limit or 10
        )
        
        return RecentSearchesResponse(searches=recent_searches)
        
    except Exception as e:
        # Log the detailed error internally
        logger.error(f"Recent searches error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to retrieve recent searches")


@router.delete("/recent")
async def clear_recent_searches(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(current_active_user),
    _rate_limit = Depends(search_rate_limit),
):
    """
    Clear all recent searches for the current user.
    
    Requires authentication.
    """
    try:
        from app.models.search_history import SearchHistory
        
        # Delete all search history for the user
        from sqlalchemy import delete
        
        stmt = delete(SearchHistory).where(
            SearchHistory.user_id == current_user.id
        )
        result = await db.execute(stmt)
        deleted_count = result.rowcount
        
        await db.commit()
        
        return {"message": f"Cleared {deleted_count} recent searches"}
        
    except Exception as e:
        await db.rollback()
        # Log the detailed error internally
        logger.error(f"Clear recent searches error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to clear recent searches")