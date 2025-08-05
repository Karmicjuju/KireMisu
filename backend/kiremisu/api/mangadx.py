"""MangaDx integration API endpoints."""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    MangaDxBulkImportRequest,
    MangaDxBulkImportResponse,
    MangaDxEnrichmentRequest,
    MangaDxEnrichmentResponse,
    MangaDxHealthResponse,
    MangaDxImportRequest,
    MangaDxImportResponse,
    MangaDxMangaInfo,
    MangaDxSearchRequest,
    MangaDxSearchResponse,
)
from kiremisu.services.mangadx_client import (
    MangaDxClient,
    MangaDxError,
    MangaDxNotFoundError,
    MangaDxRateLimitError,
    MangaDxServerError,
)
from kiremisu.services.mangadx_import import MangaDxImportService, MangaDxImportError

logger = logging.getLogger(__name__)

# Router configuration
router = APIRouter(prefix="/api/mangadx", tags=["mangadx"])

# Global instances (will be initialized in dependency)
_mangadx_client: Optional[MangaDxClient] = None
_import_service: Optional[MangaDxImportService] = None


async def get_mangadx_client() -> MangaDxClient:
    """Get MangaDx client instance."""
    global _mangadx_client
    
    if _mangadx_client is None:
        _mangadx_client = MangaDxClient(
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            requests_per_second=5.0,  # MangaDx rate limit
        )
    
    return _mangadx_client


async def get_import_service() -> MangaDxImportService:
    """Get MangaDx import service instance."""
    global _import_service
    
    if _import_service is None:
        client = await get_mangadx_client()
        _import_service = MangaDxImportService(
            mangadx_client=client,
            cover_storage_path="/app/data/covers",  # Docker path
            max_title_similarity_threshold=0.6,
            auto_confidence_threshold=0.85,
        )
    
    return _import_service


def _handle_mangadx_error(error: Exception, operation: str) -> HTTPException:
    """
    Convert MangaDx errors to appropriate HTTP exceptions.
    
    Args:
        error: The caught exception
        operation: Description of the operation that failed
        
    Returns:
        HTTPException with appropriate status and message
    """
    if isinstance(error, MangaDxRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"MangaDx API rate limit exceeded during {operation}",
                "retry_after": error.retry_after,
            }
        )
    
    elif isinstance(error, MangaDxNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Resource not found during {operation}",
            }
        )
    
    elif isinstance(error, MangaDxServerError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "external_service_error",
                "message": f"MangaDx API server error during {operation}",
            }
        )
    
    elif isinstance(error, MangaDxError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "external_api_error",
                "message": f"MangaDx API error during {operation}: {str(error)}",
            }
        )
    
    elif isinstance(error, MangaDxImportError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "import_error",
                "message": f"Import error during {operation}: {str(error)}",
            }
        )
    
    else:
        logger.error(f"Unexpected error during {operation}: {error}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Internal server error during {operation}",
            }
        )


@router.get("/health", response_model=MangaDxHealthResponse)
async def mangadx_health_check(
    client: MangaDxClient = Depends(get_mangadx_client),
) -> MangaDxHealthResponse:
    """
    Check MangaDx API health and connectivity.
    
    Returns:
        MangaDxHealthResponse with health status
    """
    start_time = time.time()
    
    try:
        is_healthy = await client.health_check()
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return MangaDxHealthResponse(
            api_accessible=is_healthy,
            response_time_ms=response_time_ms,
            last_check=datetime.now(timezone.utc),
            error_message=None if is_healthy else "API health check failed",
        )
    
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return MangaDxHealthResponse(
            api_accessible=False,
            response_time_ms=response_time_ms,
            last_check=datetime.now(timezone.utc),
            error_message=str(e),
        )


@router.post("/search", response_model=MangaDxSearchResponse)
async def search_manga(
    search_request: MangaDxSearchRequest,
    client: MangaDxClient = Depends(get_mangadx_client),
) -> MangaDxSearchResponse:
    """
    Search for manga on MangaDx.
    
    This endpoint acts as a proxy to the MangaDx API, providing search functionality
    with rate limiting and error handling.
    
    Args:
        search_request: Search parameters
        
    Returns:
        MangaDxSearchResponse with search results
        
    Raises:
        HTTPException: For various API errors (rate limiting, not found, server errors)
    """
    logger.info(f"Searching MangaDx: title='{search_request.title}', author='{search_request.author}', limit={search_request.limit}")
    
    try:
        # Perform MangaDx search
        search_response = await client.search_manga(
            title=search_request.title,
            author=search_request.author,
            artist=search_request.artist,
            year=search_request.year,
            status=search_request.status,
            content_rating=search_request.content_rating,
            original_language=search_request.original_language,
            limit=search_request.limit,
            offset=search_request.offset,
        )
        
        # Convert to our schema format
        results = []
        for manga in search_response.data:
            # Convert MangaDx response to our standardized format
            title_info = manga.get_title_info()
            genres, tags = manga.get_genres_and_tags()
            author, artist = manga.get_author_info()
            
            # Get cover art URL
            cover_art_url = None
            for relationship in manga.relationships:
                if relationship.get("type") == "cover_art":
                    cover_filename = relationship.get("attributes", {}).get("fileName")
                    if cover_filename:
                        cover_art_url = client.get_cover_art_url(manga.id, cover_filename, size="512")
                    break
            
            manga_info = MangaDxMangaInfo(
                id=manga.id,
                title=title_info.get_primary_title(),
                alternative_titles=title_info.get_alternative_titles(),
                description=manga.get_description(),
                author=author,
                artist=artist,
                genres=genres,
                tags=tags,
                status=manga.status,
                content_rating=manga.content_rating,
                original_language=manga.original_language,
                publication_year=manga.year,
                last_volume=manga.last_volume,
                last_chapter=manga.last_chapter,
                cover_art_url=cover_art_url,
            )
            
            results.append(manga_info)
        
        has_more = search_response.offset + len(results) < search_response.total
        
        return MangaDxSearchResponse(
            results=results,
            total=search_response.total,
            limit=search_response.limit,
            offset=search_response.offset,
            has_more=has_more,
        )
    
    except Exception as e:
        raise _handle_mangadx_error(e, "manga search") from e


@router.get("/manga/{manga_id}", response_model=MangaDxMangaInfo)
async def get_manga_details(
    manga_id: str,
    client: MangaDxClient = Depends(get_mangadx_client),
) -> MangaDxMangaInfo:
    """
    Get detailed information for a specific manga from MangaDx.
    
    Args:
        manga_id: MangaDx manga UUID
        
    Returns:
        MangaDxMangaInfo with detailed manga information
        
    Raises:
        HTTPException: For various API errors (not found, rate limiting, server errors)
    """
    logger.info(f"Fetching MangaDx manga details: {manga_id}")
    
    try:
        # Get manga details from MangaDx
        manga = await client.get_manga(manga_id)
        
        # Convert to our schema format
        title_info = manga.get_title_info()
        genres, tags = manga.get_genres_and_tags()
        author, artist = manga.get_author_info()
        
        # Get cover art URL
        cover_art_url = None
        for relationship in manga.relationships:
            if relationship.get("type") == "cover_art":
                cover_filename = relationship.get("attributes", {}).get("fileName")
                if cover_filename:
                    cover_art_url = client.get_cover_art_url(manga.id, cover_filename, size="512")
                break
        
        return MangaDxMangaInfo(
            id=manga.id,
            title=title_info.get_primary_title(),
            alternative_titles=title_info.get_alternative_titles(),
            description=manga.get_description(),
            author=author,
            artist=artist,
            genres=genres,
            tags=tags,
            status=manga.status,
            content_rating=manga.content_rating,
            original_language=manga.original_language,
            publication_year=manga.year,
            last_volume=manga.last_volume,
            last_chapter=manga.last_chapter,
            cover_art_url=cover_art_url,
        )
    
    except Exception as e:
        raise _handle_mangadx_error(e, f"get manga details for {manga_id}") from e


@router.post("/import", response_model=MangaDxImportResponse)
async def import_manga_metadata(
    import_request: MangaDxImportRequest,
    db_session: AsyncSession = Depends(get_db),
    import_service: MangaDxImportService = Depends(get_import_service),
) -> MangaDxImportResponse:
    """
    Import or enrich manga metadata from MangaDx.
    
    This endpoint can either create a new series from MangaDx metadata or
    enrich an existing series with additional metadata.
    
    Args:
        import_request: Import parameters
        db_session: Database session
        import_service: MangaDx import service
        
    Returns:
        MangaDxImportResponse with import results
        
    Raises:
        HTTPException: For various import errors
    """
    logger.info(f"Importing MangaDx metadata: {import_request.mangadx_id}")
    
    try:
        # Perform the import
        result = await import_service.import_series_metadata(db_session, import_request)
        
        if result.success:
            status_msg = "success"
            message = f"Successfully {result.operation} series with MangaDx metadata"
        else:
            status_msg = "failed"
            message = f"Failed to import MangaDx metadata: {', '.join(result.errors)}"
        
        return MangaDxImportResponse(
            status=status_msg,
            message=message,
            result=result,
        )
    
    except Exception as e:
        raise _handle_mangadx_error(e, f"import metadata for {import_request.mangadx_id}") from e


@router.post("/enrich/{series_id}", response_model=MangaDxEnrichmentResponse)
async def find_enrichment_candidates(
    series_id: UUID,
    enrichment_request: MangaDxEnrichmentRequest,
    db_session: AsyncSession = Depends(get_db),
    import_service: MangaDxImportService = Depends(get_import_service),
) -> MangaDxEnrichmentResponse:
    """
    Find MangaDx enrichment candidates for an existing series.
    
    This endpoint searches MangaDx for potential matches to a local series
    and returns candidates with confidence scores for manual or automatic selection.
    
    Args:
        series_id: Local series ID to find matches for
        enrichment_request: Enrichment parameters
        db_session: Database session
        import_service: MangaDx import service
        
    Returns:
        MangaDxEnrichmentResponse with potential matches
        
    Raises:
        HTTPException: For various enrichment errors
    """
    logger.info(f"Finding MangaDx enrichment candidates for series: {series_id}")
    
    try:
        # Update the series_id in the request
        enrichment_request.series_id = series_id
        
        # Find potential matches
        enrichment_response = await import_service.search_and_match_series(
            db_session=db_session,
            series_id=series_id,
            search_query=enrichment_request.search_query,
            auto_select_best_match=enrichment_request.auto_select_best_match,
            confidence_threshold=enrichment_request.confidence_threshold,
        )
        
        return enrichment_response
    
    except Exception as e:
        raise _handle_mangadx_error(e, f"find enrichment candidates for series {series_id}") from e


@router.post("/bulk-import", response_model=MangaDxBulkImportResponse)
async def bulk_import_manga_metadata(
    bulk_request: MangaDxBulkImportRequest,
    db_session: AsyncSession = Depends(get_db),
) -> MangaDxBulkImportResponse:
    """
    Schedule bulk import of manga metadata from MangaDx.
    
    This endpoint schedules background jobs for importing multiple manga
    metadata records. The actual imports are processed asynchronously.
    
    Args:
        bulk_request: Bulk import parameters
        db_session: Database session
        
    Returns:
        MangaDxBulkImportResponse with job scheduling status
        
    Raises:
        HTTPException: For scheduling errors
    """
    logger.info(f"Scheduling bulk import of {len(bulk_request.import_requests)} manga metadata records")
    
    try:
        # TODO: Implement background job scheduling for bulk imports
        # For now, return a placeholder response
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": "not_implemented",
                "message": "Bulk import functionality is not yet implemented. Use individual import endpoints for now.",
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_mangadx_error(e, "schedule bulk import") from e


# Cleanup function for application shutdown
async def cleanup_mangadx_services():
    """Clean up MangaDx services on application shutdown."""
    global _mangadx_client
    
    if _mangadx_client:
        await _mangadx_client.close()
        _mangadx_client = None
    
    logger.info("MangaDx services cleaned up")