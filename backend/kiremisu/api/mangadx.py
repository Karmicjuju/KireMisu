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
    DownloadJobRequest,
    DownloadJobResponse,
)
from kiremisu.services.mangadx_client import (
    MangaDxClient,
    MangaDxError,
    MangaDxNotFoundError,
    MangaDxRateLimitError,
    MangaDxServerError,
)
from kiremisu.services.mangadx_import import MangaDxImportService, MangaDxImportError
from kiremisu.services.download_service import DownloadService

logger = logging.getLogger(__name__)

# Router configuration
router = APIRouter(prefix="/api/mangadx", tags=["mangadx"])

# Global instances (will be initialized in dependency)
_mangadx_client: Optional[MangaDxClient] = None
_import_service: Optional[MangaDxImportService] = None
_download_service: Optional[DownloadService] = None


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


async def get_download_service() -> DownloadService:
    """Get download service instance."""
    global _download_service
    
    if _download_service is None:
        _download_service = DownloadService()
    
    return _download_service


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
                        cover_art_url = await client.get_cover_art_url(manga.id, cover_filename, size="512")
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
                    cover_art_url = await client.get_cover_art_url(manga.id, cover_filename, size="512")
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


# Download integration endpoints
@router.post("/manga/{manga_id}/download", response_model=DownloadJobResponse, status_code=status.HTTP_201_CREATED)
async def download_manga_series(
    manga_id: str,
    download_request: DownloadJobRequest,
    db_session: AsyncSession = Depends(get_db),
    download_service: DownloadService = Depends(get_download_service),
):
    """
    Create a download job for a MangaDx manga.
    
    Creates a download job for the specified manga, supporting different
    download types (single chapter, batch, or entire series).
    
    Args:
        manga_id: MangaDx manga UUID
        download_request: Download configuration
        db_session: Database session
        download_service: Download service instance
        
    Returns:
        DownloadJobResponse with created job details
        
    Raises:
        HTTPException: For download scheduling errors
    """
    logger.info(f"Creating download job for MangaDx manga: {manga_id}")
    
    try:
        # Validate that the manga exists on MangaDx first
        client = await get_mangadx_client()
        try:
            await client.get_manga(manga_id)
        except MangaDxNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manga {manga_id} not found on MangaDx"
            )
        
        # Override the manga_id from the URL
        download_request.manga_id = manga_id
        
        # Create the download job based on type
        if download_request.download_type == "single":
            if not download_request.chapter_ids or len(download_request.chapter_ids) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Single download requires exactly one chapter_id"
                )
            
            job_id = await download_service.enqueue_single_chapter_download(
                db=db_session,
                manga_id=manga_id,
                chapter_id=download_request.chapter_ids[0],
                series_id=download_request.series_id,
                priority=download_request.priority,
                destination_path=download_request.destination_path,
            )
            
        elif download_request.download_type == "batch":
            if not download_request.chapter_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Batch download requires chapter_ids"
                )
            
            job_id = await download_service.enqueue_batch_download(
                db=db_session,
                manga_id=manga_id,
                chapter_ids=download_request.chapter_ids,
                batch_type="multiple",
                series_id=download_request.series_id,
                volume_number=download_request.volume_number,
                priority=download_request.priority,
                destination_path=download_request.destination_path,
            )
            
        elif download_request.download_type == "series":
            job_id = await download_service.enqueue_series_download(
                db=db_session,
                manga_id=manga_id,
                series_id=download_request.series_id,
                priority=download_request.priority,
                destination_path=download_request.destination_path,
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid download_type: {download_request.download_type}"
            )
        
        # Get the created job to return
        from sqlalchemy import select
        from kiremisu.database.models import JobQueue
        
        result = await db_session.execute(select(JobQueue).where(JobQueue.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created download job"
            )
        
        return DownloadJobResponse.from_job_model(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create download job for manga {manga_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create download job: {str(e)}"
        )
    finally:
        await download_service.cleanup()


@router.post("/import-and-download", response_model=dict, status_code=status.HTTP_201_CREATED)
async def import_and_download_manga(
    import_request: MangaDxImportRequest,
    download_chapters: bool = False,
    download_priority: int = 3,
    db_session: AsyncSession = Depends(get_db),
    import_service: MangaDxImportService = Depends(get_import_service),
    download_service: DownloadService = Depends(get_download_service),
):
    """
    Import manga metadata from MangaDx and optionally download chapters.
    
    This is a convenience endpoint that combines metadata import with
    optional chapter downloading in a single operation.
    
    Args:
        import_request: Import configuration
        download_chapters: Whether to also download all chapters
        download_priority: Priority for download job (if downloading)
        db_session: Database session
        import_service: Import service instance
        download_service: Download service instance
        
    Returns:
        Combined import and download results
        
    Raises:
        HTTPException: For import or download errors
    """
    logger.info(f"Import and download operation for MangaDx manga: {import_request.mangadx_id}")
    
    try:
        # First, import the metadata
        import_result = await import_service.import_manga_metadata(
            db_session=db_session,
            mangadx_id=import_request.mangadx_id,
            target_series_id=import_request.target_series_id,
            import_cover_art=import_request.import_cover_art,
            import_chapters=import_request.import_chapters,
            overwrite_existing=import_request.overwrite_existing,
            custom_title=import_request.custom_title,
        )
        
        result = {
            "import_result": {
                "success": import_result.success,
                "series_id": import_result.series_id,
                "operation": import_result.operation,
                "metadata_fields_updated": import_result.metadata_fields_updated,
                "cover_art_downloaded": import_result.cover_art_downloaded,
                "chapters_imported": import_result.chapters_imported,
            },
            "download_result": None
        }
        
        # If import was successful and download requested, create download job
        if download_chapters and import_result.success and import_result.series_id:
            try:
                download_job_id = await download_service.enqueue_series_download(
                    db=db_session,
                    manga_id=import_request.mangadx_id,
                    series_id=import_result.series_id,
                    priority=download_priority,
                )
                
                # Get the created download job
                from sqlalchemy import select
                from kiremisu.database.models import JobQueue
                
                job_result = await db_session.execute(select(JobQueue).where(JobQueue.id == download_job_id))
                download_job = job_result.scalar_one_or_none()
                
                if download_job:
                    result["download_result"] = {
                        "job_id": str(download_job_id),
                        "status": download_job.status,
                        "priority": download_job.priority,
                        "scheduled_at": download_job.scheduled_at.isoformat(),
                    }
                    
            except Exception as download_error:
                logger.warning(f"Import succeeded but download failed: {download_error}")
                result["download_result"] = {
                    "error": str(download_error),
                    "message": "Import completed successfully but download job creation failed"
                }
        
        return result
        
    except Exception as e:
        raise _handle_mangadx_error(e, f"import and download manga {import_request.mangadx_id}") from e
    finally:
        await download_service.cleanup()


# Cleanup function for application shutdown
async def cleanup_mangadx_services():
    """Clean up MangaDx services on application shutdown."""
    global _mangadx_client, _download_service
    
    if _mangadx_client:
        await _mangadx_client.close()
        _mangadx_client = None
    
    if _download_service:
        await _download_service.cleanup()
        _download_service = None
    
    logger.info("MangaDx services cleaned up")