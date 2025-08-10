"""MangaDx metadata import and enrichment service."""

import asyncio
import difflib
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from dateutil.parser import parse as parse_datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Series
from kiremisu.database.schemas import (
    MangaDxEnrichmentCandidate,
    MangaDxEnrichmentResponse,
    MangaDxImportRequest,
    MangaDxImportResult,
    MangaDxMangaInfo,
    MangaDxSearchRequest,
)
from kiremisu.services.mangadx_client import MangaDxClient, MangaDxMangaResponse

logger = logging.getLogger(__name__)


class MangaDxImportError(Exception):
    """Base exception for MangaDx import errors."""

    pass


class MangaDxImportService:
    """
    Service for importing and enriching manga metadata from MangaDx.
    
    Handles mapping MangaDx API responses to local database models,
    downloading cover art, and managing metadata conflicts.
    """
    
    def __init__(
        self,
        mangadx_client: MangaDxClient,
        cover_storage_path: str = "/tmp/manga-covers",
        max_title_similarity_threshold: float = 0.6,
        auto_confidence_threshold: float = 0.85,
    ):
        """
        Initialize MangaDx import service.
        
        Args:
            mangadx_client: MangaDx API client instance
            cover_storage_path: Path to store downloaded cover art
            max_title_similarity_threshold: Minimum similarity for title matching
            auto_confidence_threshold: Minimum confidence for auto-selection
        """
        self.mangadx_client = mangadx_client
        self.cover_storage_path = Path(cover_storage_path)
        self.max_title_similarity_threshold = max_title_similarity_threshold
        self.auto_confidence_threshold = auto_confidence_threshold
        
        # Ensure cover storage directory exists
        self.cover_storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized MangaDx import service with cover storage: {cover_storage_path}")
    
    async def _convert_mangadx_to_manga_info(self, mangadx_response: MangaDxMangaResponse) -> MangaDxMangaInfo:
        """
        Convert MangaDx API response to standardized MangaDxMangaInfo.
        
        Args:
            mangadx_response: Raw MangaDx API response
            
        Returns:
            Standardized MangaDxMangaInfo object
        """
        title_info = mangadx_response.get_title_info()
        genres, tags = mangadx_response.get_genres_and_tags()
        author, artist = mangadx_response.get_author_info()
        
        # Parse timestamps
        mangadx_created_at = None
        mangadx_updated_at = None
        
        try:
            if mangadx_response.created_at:
                mangadx_created_at = parse_datetime(mangadx_response.created_at)
        except Exception as e:
            logger.warning(f"Failed to parse MangaDx created_at timestamp: {e}")
        
        try:
            if mangadx_response.updated_at:
                mangadx_updated_at = parse_datetime(mangadx_response.updated_at)
        except Exception as e:
            logger.warning(f"Failed to parse MangaDx updated_at timestamp: {e}")
        
        # Get cover art URL if available
        cover_art_url = None
        for relationship in mangadx_response.relationships:
            if relationship.get("type") == "cover_art":
                cover_filename = relationship.get("attributes", {}).get("fileName")
                if cover_filename:
                    cover_art_url = await self.mangadx_client.get_cover_art_url(
                        mangadx_response.id, cover_filename, size="512"
                    )
                break
        
        return MangaDxMangaInfo(
            id=mangadx_response.id,
            title=title_info.get_primary_title(),
            alternative_titles=title_info.get_alternative_titles(),
            description=mangadx_response.get_description(),
            author=author,
            artist=artist,
            genres=genres,
            tags=tags,
            status=mangadx_response.status,
            content_rating=mangadx_response.content_rating,
            original_language=mangadx_response.original_language,
            publication_year=mangadx_response.year,
            last_volume=mangadx_response.last_volume,
            last_chapter=mangadx_response.last_chapter,
            cover_art_url=cover_art_url,
            mangadx_created_at=mangadx_created_at,
            mangadx_updated_at=mangadx_updated_at,
        )
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles using difflib.
        
        Args:
            title1: First title to compare
            title2: Second title to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles (lowercase, strip whitespace)
        normalized_title1 = title1.lower().strip()
        normalized_title2 = title2.lower().strip()
        
        # Use SequenceMatcher for similarity calculation
        similarity = difflib.SequenceMatcher(None, normalized_title1, normalized_title2).ratio()
        
        return similarity
    
    def _calculate_match_confidence(
        self, 
        local_series: Series, 
        mangadx_info: MangaDxMangaInfo
    ) -> Tuple[float, List[str]]:
        """
        Calculate confidence score for a potential match.
        
        Args:
            local_series: Local series to match against
            mangadx_info: MangaDx manga information
            
        Returns:
            Tuple of (confidence_score, match_reasons)
        """
        confidence = 0.0
        reasons = []
        
        # Title matching (most important factor - 60% weight)
        primary_title_similarity = self._calculate_title_similarity(
            local_series.title_primary, mangadx_info.title
        )
        
        if primary_title_similarity >= self.max_title_similarity_threshold:
            title_confidence = primary_title_similarity * 0.6
            confidence += title_confidence
            reasons.append(f"Primary title match ({primary_title_similarity:.2f})")
        
        # Check alternative titles
        if mangadx_info.alternative_titles:
            best_alt_similarity = 0.0
            for alt_title in mangadx_info.alternative_titles:
                similarity = self._calculate_title_similarity(local_series.title_primary, alt_title)
                best_alt_similarity = max(best_alt_similarity, similarity)
            
            if best_alt_similarity >= self.max_title_similarity_threshold:
                alt_confidence = best_alt_similarity * 0.4  # Lower weight for alt titles
                confidence += alt_confidence
                reasons.append(f"Alternative title match ({best_alt_similarity:.2f})")
        
        # Author matching (20% weight)
        if local_series.author and mangadx_info.author:
            author_similarity = self._calculate_title_similarity(local_series.author, mangadx_info.author)
            if author_similarity >= 0.8:  # Stricter threshold for author names
                author_confidence = author_similarity * 0.2
                confidence += author_confidence
                reasons.append(f"Author match ({author_similarity:.2f})")
        
        # Artist matching (10% weight)
        if local_series.artist and mangadx_info.artist:
            artist_similarity = self._calculate_title_similarity(local_series.artist, mangadx_info.artist)
            if artist_similarity >= 0.8:  # Stricter threshold for artist names
                artist_confidence = artist_similarity * 0.1
                confidence += artist_confidence
                reasons.append(f"Artist match ({artist_similarity:.2f})")
        
        # Genre/tag overlap (10% weight)
        if local_series.genres and mangadx_info.genres:
            local_genres_set = set(g.lower() for g in local_series.genres)
            mangadx_genres_set = set(g.lower() for g in mangadx_info.genres)
            
            if local_genres_set and mangadx_genres_set:
                genre_overlap = len(local_genres_set & mangadx_genres_set) / len(local_genres_set | mangadx_genres_set)
                if genre_overlap > 0.2:  # At least 20% overlap
                    genre_confidence = genre_overlap * 0.1
                    confidence += genre_confidence
                    reasons.append(f"Genre overlap ({genre_overlap:.2f})")
        
        return min(confidence, 1.0), reasons
    
    async def _download_cover_art(self, cover_url: str, manga_id: str) -> Optional[str]:
        """
        Download cover art from MangaDx.
        
        Args:
            cover_url: URL to cover art image
            manga_id: MangaDx manga ID for filename
            
        Returns:
            Local file path to downloaded cover, or None if failed
        """
        if not cover_url:
            return None
        
        try:
            # Generate filename based on manga ID and URL hash
            url_hash = hashlib.md5(cover_url.encode()).hexdigest()[:8]
            filename = f"{manga_id}_{url_hash}.jpg"
            cover_path = self.cover_storage_path / filename
            
            # Skip if already exists
            if cover_path.exists():
                logger.debug(f"Cover art already exists: {cover_path}")
                return str(cover_path)
            
            logger.info(f"Downloading cover art from: {cover_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(cover_url)
                response.raise_for_status()
                
                # Validate content type
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.warning(f"Invalid content type for cover art: {content_type}")
                    return None
                
                # Write to file
                with open(cover_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded cover art to: {cover_path}")
                return str(cover_path)
        
        except Exception as e:
            logger.error(f"Failed to download cover art from {cover_url}: {e}")
            return None
    
    async def search_and_match_series(
        self,
        db_session: AsyncSession,
        series_id: UUID,
        search_query: Optional[str] = None,
        auto_select_best_match: bool = False,
        confidence_threshold: float = 0.8,
    ) -> MangaDxEnrichmentResponse:
        """
        Search MangaDx for potential matches to a local series.
        
        Args:
            db_session: Database session
            series_id: Local series ID to find matches for
            search_query: Override search query (uses series title if not provided)
            auto_select_best_match: Whether to auto-select best match
            confidence_threshold: Minimum confidence for auto-selection
            
        Returns:
            MangaDxEnrichmentResponse with potential matches
            
        Raises:
            MangaDxImportError: If series not found or search fails
        """
        # Get local series
        result = await db_session.execute(select(Series).where(Series.id == series_id))
        local_series = result.scalar_one_or_none()
        
        if not local_series:
            raise MangaDxImportError(f"Series not found: {series_id}")
        
        # Determine search query
        query = search_query or local_series.title_primary
        
        logger.info(f"Searching MangaDx for matches to series '{local_series.title_primary}' using query: '{query}'")
        
        try:
            # Search MangaDx
            search_request = MangaDxSearchRequest(title=query, limit=50)  # Get more results for better matching
            search_response = await self.mangadx_client.search_manga(
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
            
            # Convert and calculate confidence for each result
            candidates = []
            for mangadx_manga in search_response.data:
                mangadx_info = await self._convert_mangadx_to_manga_info(mangadx_manga)
                confidence, reasons = self._calculate_match_confidence(local_series, mangadx_info)
                
                # Only include candidates above minimum threshold
                if confidence >= self.max_title_similarity_threshold:
                    candidate = MangaDxEnrichmentCandidate(
                        mangadx_info=mangadx_info,
                        confidence_score=confidence,
                        match_reasons=reasons,
                        is_recommended=confidence >= self.auto_confidence_threshold,
                    )
                    candidates.append(candidate)
            
            # Sort by confidence (highest first)
            candidates.sort(key=lambda c: c.confidence_score, reverse=True)
            
            # Auto-select best match if requested and confidence is high enough
            auto_selected = None
            if auto_select_best_match and candidates:
                best_candidate = candidates[0]
                if best_candidate.confidence_score >= confidence_threshold:
                    auto_selected = best_candidate
                    logger.info(f"Auto-selected MangaDx match: {best_candidate.mangadx_info.title} (confidence: {best_candidate.confidence_score:.2f})")
            
            return MangaDxEnrichmentResponse(
                series_id=series_id,
                series_title=local_series.title_primary,
                candidates=candidates,
                auto_selected=auto_selected,
                search_query_used=query,
                total_candidates=len(candidates),
            )
        
        except Exception as e:
            logger.error(f"Failed to search MangaDx for series {series_id}: {e}")
            raise MangaDxImportError(f"Search failed: {e}")
    
    async def import_series_metadata(
        self,
        db_session: AsyncSession,
        import_request: MangaDxImportRequest,
    ) -> MangaDxImportResult:
        """
        Import or enrich series metadata from MangaDx.
        
        Args:
            db_session: Database session
            import_request: Import request parameters
            
        Returns:
            MangaDxImportResult with import details
            
        Raises:
            MangaDxImportError: If import fails
        """
        start_time = time.time()
        
        try:
            # Get MangaDx manga details
            logger.info(f"Importing MangaDx metadata for manga: {import_request.mangadx_id}")
            mangadx_manga = await self.mangadx_client.get_manga(import_request.mangadx_id)
            mangadx_info = await self._convert_mangadx_to_manga_info(mangadx_manga)
            
            # Determine operation mode
            operation = "created"
            metadata_fields_updated = []
            warnings = []
            errors = []
            
            if import_request.target_series_id:
                # Enrich existing series
                result = await db_session.execute(select(Series).where(Series.id == import_request.target_series_id))
                series = result.scalar_one_or_none()
                
                if not series:
                    raise MangaDxImportError(f"Target series not found: {import_request.target_series_id}")
                
                operation = "enriched"
                logger.info(f"Enriching existing series: {series.title_primary}")
                
            else:
                # Create new series
                series = Series(
                    id=uuid4(),
                    title_primary=import_request.custom_title or mangadx_info.title,
                    language="en",  # Default language
                )
                operation = "created"
                logger.info(f"Creating new series: {series.title_primary}")
            
            # Update metadata fields
            if not series.description or import_request.overwrite_existing:
                if mangadx_info.description:
                    series.description = mangadx_info.description
                    metadata_fields_updated.append("description")
            
            if not series.author or import_request.overwrite_existing:
                if mangadx_info.author:
                    series.author = mangadx_info.author
                    metadata_fields_updated.append("author")
            
            if not series.artist or import_request.overwrite_existing:
                if mangadx_info.artist:
                    series.artist = mangadx_info.artist
                    metadata_fields_updated.append("artist")
            
            if not series.genres or import_request.overwrite_existing:
                if mangadx_info.genres:
                    series.genres = mangadx_info.genres
                    metadata_fields_updated.append("genres")
            
            if not series.tags or import_request.overwrite_existing:
                if mangadx_info.tags:
                    series.tags = mangadx_info.tags
                    metadata_fields_updated.append("tags")
            
            if not series.publication_status or import_request.overwrite_existing:
                if mangadx_info.status:
                    series.publication_status = mangadx_info.status
                    metadata_fields_updated.append("publication_status")
            
            if not series.content_rating or import_request.overwrite_existing:
                if mangadx_info.content_rating:
                    series.content_rating = mangadx_info.content_rating
                    metadata_fields_updated.append("content_rating")
            
            # Set MangaDx ID and source metadata
            series.mangadx_id = import_request.mangadx_id
            series.source_metadata = {
                "mangadx": {
                    "id": mangadx_info.id,
                    "original_language": mangadx_info.original_language,
                    "publication_year": mangadx_info.publication_year,
                    "last_volume": mangadx_info.last_volume,
                    "last_chapter": mangadx_info.last_chapter,
                    "alternative_titles": mangadx_info.alternative_titles,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                    "mangadx_created_at": mangadx_info.mangadx_created_at.isoformat() if mangadx_info.mangadx_created_at else None,
                    "mangadx_updated_at": mangadx_info.mangadx_updated_at.isoformat() if mangadx_info.mangadx_updated_at else None,
                }
            }
            metadata_fields_updated.extend(["mangadx_id", "source_metadata"])
            
            # Download cover art if requested
            cover_art_downloaded = False
            if import_request.import_cover_art and mangadx_info.cover_art_url:
                cover_path = await self._download_cover_art(mangadx_info.cover_art_url, mangadx_info.id)
                if cover_path:
                    series.cover_image_path = cover_path
                    cover_art_downloaded = True
                    metadata_fields_updated.append("cover_image_path")
                else:
                    warnings.append("Failed to download cover art")
            
            # Save to database
            if operation == "created":
                db_session.add(series)
            
            await db_session.commit()
            
            # Calculate import duration
            import_duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Successfully {operation} series {series.id} with MangaDx metadata (duration: {import_duration_ms}ms)")
            
            return MangaDxImportResult(
                success=True,
                series_id=series.id,
                mangadx_id=import_request.mangadx_id,
                operation=operation,
                metadata_fields_updated=metadata_fields_updated,
                cover_art_downloaded=cover_art_downloaded,
                chapters_imported=0,  # Chapter import not implemented yet
                warnings=warnings,
                errors=errors,
                import_duration_ms=import_duration_ms,
            )
        
        except Exception as e:
            await db_session.rollback()
            import_duration_ms = int((time.time() - start_time) * 1000)
            
            logger.error(f"Failed to import MangaDx metadata for {import_request.mangadx_id}: {e}")
            
            return MangaDxImportResult(
                success=False,
                series_id=import_request.target_series_id,
                mangadx_id=import_request.mangadx_id,
                operation="failed",
                metadata_fields_updated=[],
                cover_art_downloaded=False,
                chapters_imported=0,
                warnings=[],
                errors=[str(e)],
                import_duration_ms=import_duration_ms,
            )