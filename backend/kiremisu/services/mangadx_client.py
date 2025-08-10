"""MangaDx API client with rate limiting and comprehensive error handling."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MangaDxError(Exception):
    """Base exception for MangaDx API errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class MangaDxRateLimitError(MangaDxError):
    """Raised when MangaDx API rate limit is exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(f"MangaDx API rate limit exceeded. Retry after: {retry_after} seconds")
        self.retry_after = retry_after


class MangaDxNotFoundError(MangaDxError):
    """Raised when requested manga is not found."""

    pass


class MangaDxServerError(MangaDxError):
    """Raised when MangaDx API returns server error."""

    pass


class MangaDxRateLimiter:
    """Rate limiter specifically for MangaDx API calls."""

    def __init__(self, requests_per_second: float = 5.0):
        """
        Initialize MangaDx rate limiter.

        Args:
            requests_per_second: Maximum requests per second (MangaDx allows 5 req/s)
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request, blocking if necessary."""
        async with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)

            self.last_request_time = time.time()


class MangaDxTitle(BaseModel):
    """MangaDx title information."""

    en: Optional[str] = None
    ja: Optional[str] = None
    ja_ro: Optional[str] = None

    def get_primary_title(self) -> str:
        """Get the primary title, preferring English."""
        return self.en or self.ja_ro or self.ja or "Unknown Title"

    def get_alternative_titles(self) -> List[str]:
        """Get alternative titles as a list."""
        titles = []
        if self.en and self.ja_ro and self.en != self.ja_ro:
            titles.append(self.ja_ro)
        if self.ja and self.ja != self.en and self.ja != self.ja_ro:
            titles.append(self.ja)
        return titles


class MangaDxMangaResponse(BaseModel):
    """MangaDx manga response model."""

    id: str = Field(..., description="MangaDx manga UUID")
    type: str = Field(default="manga")

    # Attributes
    title: Dict[str, str] = Field(default_factory=dict)
    alt_titles: List[Dict[str, str]] = Field(default_factory=list, alias="altTitles")
    description: Dict[str, str] = Field(default_factory=dict)
    is_locked: bool = Field(default=False, alias="isLocked")
    original_language: str = Field(default="ja", alias="originalLanguage")
    last_volume: Optional[str] = Field(None, alias="lastVolume")
    last_chapter: Optional[str] = Field(None, alias="lastChapter")
    publication_demographic: Optional[str] = Field(None, alias="publicationDemographic")
    status: str = Field(default="ongoing")
    year: Optional[int] = None
    content_rating: str = Field(default="safe", alias="contentRating")
    tags: List[Dict[str, Any]] = Field(default_factory=list)
    state: str = Field(default="published")
    chapter_numbers_reset_on_new_volume: bool = Field(
        default=False, alias="chapterNumbersResetOnNewVolume"
    )
    created_at: str = Field(default="", alias="createdAt")
    updated_at: str = Field(default="", alias="updatedAt")
    version: int = Field(default=1)

    # Relationships
    relationships: List[Dict[str, Any]] = Field(default_factory=list)

    def get_title_info(self) -> MangaDxTitle:
        """Extract title information."""
        return MangaDxTitle(
            en=self.title.get("en"), ja=self.title.get("ja"), ja_ro=self.title.get("ja-ro")
        )

    def get_description(self) -> Optional[str]:
        """Get description, preferring English."""
        return self.description.get("en") or self.description.get("ja") or None

    def get_genres_and_tags(self) -> Tuple[List[str], List[str]]:
        """Extract genres and tags from MangaDx tags."""
        genres = []
        tags = []

        for tag in self.tags:
            if isinstance(tag, dict) and "attributes" in tag:
                tag_name = tag["attributes"].get("name", {}).get("en", "")
                tag_group = tag["attributes"].get("group", "")

                if tag_group == "genre":
                    genres.append(tag_name)
                else:
                    tags.append(tag_name)

        return genres, tags

    def get_author_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract author and artist information from relationships."""
        author = None
        artist = None

        for rel in self.relationships:
            if rel.get("type") == "author":
                author = rel.get("attributes", {}).get("name")
            elif rel.get("type") == "artist":
                artist = rel.get("attributes", {}).get("name")

        return author, artist


class MangaDxSearchResponse(BaseModel):
    """MangaDx search response model."""

    result: str = Field(default="ok")
    response: str = Field(default="collection")
    data: List[MangaDxMangaResponse] = Field(default_factory=list)
    limit: int = Field(default=10)
    offset: int = Field(default=0)
    total: int = Field(default=0)


class MangaDxClient:
    """
    Async MangaDx API client with rate limiting and comprehensive error handling.

    Implements the MangaDx API v5 specification with proper rate limiting,
    retry logic, and structured error handling.
    """

    BASE_URL = "https://api.mangadex.org"

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        requests_per_second: float = 5.0,
    ):
        """
        Initialize MangaDx client.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            requests_per_second: Rate limit for API calls
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={
                "User-Agent": "KireMisu/0.1.0 (Manga Library Manager)",
                "Accept": "application/json",
            },
        )

        # Initialize rate limiter
        self.rate_limiter = MangaDxRateLimiter(requests_per_second)

        logger.info(f"Initialized MangaDx client with {requests_per_second} req/s rate limit")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON request body

        Returns:
            Parsed JSON response

        Raises:
            MangaDxError: For various API errors
            MangaDxRateLimitError: When rate limited
            MangaDxNotFoundError: When resource not found
            MangaDxServerError: For server errors
        """
        url = urljoin(self.BASE_URL, endpoint)

        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire()

                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")

                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                # Handle different status codes
                if response.status_code == 200:
                    return response.json()

                elif response.status_code == 404:
                    raise MangaDxNotFoundError(
                        "Resource not found",
                        status_code=response.status_code,
                        response_data=response.json() if response.content else {},
                    )

                elif response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Rate limited by MangaDx API. Retry after: {retry_after} seconds"
                    )

                    if attempt < self.max_retries:
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise MangaDxRateLimitError(retry_after=retry_after)

                elif 500 <= response.status_code < 600:
                    # Server error - retry with exponential backoff
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2**attempt)
                        logger.warning(f"Server error {response.status_code}, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise MangaDxServerError(
                            f"MangaDx server error: {response.status_code}",
                            status_code=response.status_code,
                            response_data=response.json() if response.content else {},
                        )

                else:
                    # Other client errors
                    raise MangaDxError(
                        f"MangaDx API error: {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.json() if response.content else {},
                    )

            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(f"Request timeout, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise MangaDxError("Request timeout after all retries")

            except httpx.NetworkError as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(f"Network error: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise MangaDxError(f"Network error after all retries: {e}")

    async def search_manga(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        artist: Optional[str] = None,
        year: Optional[int] = None,
        included_tags: Optional[List[str]] = None,
        excluded_tags: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
        original_language: Optional[List[str]] = None,
        publication_demographic: Optional[List[str]] = None,
        content_rating: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> MangaDxSearchResponse:
        """
        Search for manga using MangaDx API.

        Args:
            title: Manga title to search for
            author: Author name to search for
            artist: Artist name to search for
            year: Publication year
            included_tags: List of tag UUIDs that must be included
            excluded_tags: List of tag UUIDs that must be excluded
            status: List of publication statuses (ongoing, completed, hiatus, cancelled)
            original_language: List of language codes (ja, en, etc.)
            publication_demographic: List of demographics (shounen, seinen, shoujo, josei)
            content_rating: List of content ratings (safe, suggestive, erotica, pornographic)
            limit: Number of results to return (max 100)
            offset: Offset for pagination

        Returns:
            MangaDxSearchResponse with search results

        Raises:
            MangaDxError: For API errors
        """
        params = {
            "limit": min(limit, 100),  # MangaDx max limit is 100
            "offset": offset,
            "includes[]": ["author", "artist", "cover_art"],  # Include relationships
            "contentRating[]": ["safe", "suggestive", "erotica"],  # Default content ratings
        }

        # Add search parameters
        if title:
            params["title"] = title

        if author:
            params["authors[]"] = author

        if artist:
            params["artists[]"] = artist

        if year:
            params["year"] = year

        if included_tags:
            params["includedTags[]"] = included_tags

        if excluded_tags:
            params["excludedTags[]"] = excluded_tags

        if status:
            params["status[]"] = status

        if original_language:
            params["originalLanguage[]"] = original_language

        if publication_demographic:
            params["publicationDemographic[]"] = publication_demographic

        if content_rating:
            params["contentRating[]"] = content_rating

        logger.info(
            f"Searching MangaDx for manga: title='{title}', author='{author}', limit={limit}"
        )

        try:
            response_data = await self._make_request("GET", "/manga", params=params)

            # Parse the raw MangaDx API response format
            manga_responses = []
            for item in response_data.get("data", []):
                # Extract the attributes and add ID to create flat structure
                attributes = item.get("attributes", {})
                manga_data = {
                    "id": item.get("id", ""),
                    "type": item.get("type", "manga"),
                    "relationships": item.get("relationships", []),
                    **attributes,  # Flatten attributes into the main object
                }
                manga_responses.append(MangaDxMangaResponse(**manga_data))

            return MangaDxSearchResponse(
                result=response_data.get("result", "ok"),
                response=response_data.get("response", "collection"),
                data=manga_responses,
                limit=response_data.get("limit", limit),
                offset=response_data.get("offset", offset),
                total=response_data.get("total", 0),
            )

        except Exception as e:
            logger.error(f"Error searching MangaDx: {e}")
            raise

    async def get_manga(self, manga_id: str) -> MangaDxMangaResponse:
        """
        Get detailed manga information by ID.

        Args:
            manga_id: MangaDx manga UUID

        Returns:
            MangaDxMangaResponse with detailed manga information

        Raises:
            MangaDxNotFoundError: If manga not found
            MangaDxError: For other API errors
        """
        params = {"includes[]": ["author", "artist", "cover_art"]}

        logger.info(f"Fetching MangaDx manga details: {manga_id}")

        try:
            response_data = await self._make_request("GET", f"/manga/{manga_id}", params=params)

            # Parse the raw MangaDx API response format
            item = response_data.get("data", {})
            attributes = item.get("attributes", {})
            manga_data = {
                "id": item.get("id", ""),
                "type": item.get("type", "manga"),
                "relationships": item.get("relationships", []),
                **attributes,  # Flatten attributes into the main object
            }
            return MangaDxMangaResponse(**manga_data)

        except Exception as e:
            logger.error(f"Error fetching MangaDx manga {manga_id}: {e}")
            raise

    async def get_cover_art_url(self, manga_id: str, cover_filename: str, size: str = "512") -> str:
        """
        Get cover art URL for a manga.

        Args:
            manga_id: MangaDx manga UUID
            cover_filename: Cover art filename from manga data
            size: Image size (256, 512, or original)

        Returns:
            Full URL to cover art image
        """
        base_url = "https://uploads.mangadex.org/covers"

        if size == "original":
            return f"{base_url}/{manga_id}/{cover_filename}"
        else:
            return f"{base_url}/{manga_id}/{cover_filename}.{size}.jpg"

    async def get_manga_chapters(
        self,
        manga_id: str,
        translated_language: List[str] = ["en"],
        limit: int = 100,
        offset: int = 0,
        order_by: str = "chapter",
        order_direction: str = "asc",
    ) -> "MangaDxChapterListResponse":
        """
        Get chapters for a manga from MangaDx API.

        Args:
            manga_id: MangaDx manga UUID
            translated_language: List of language codes to filter by
            limit: Number of results to return (max 500)
            offset: Offset for pagination
            order_by: Field to order by (chapter, volume, createdAt, updatedAt)
            order_direction: Order direction (asc, desc)

        Returns:
            MangaDxChapterListResponse with chapter data

        Raises:
            MangaDxError: For API errors
            MangaDxNotFoundError: If manga not found
        """
        params = {
            "manga": manga_id,
            "limit": min(limit, 100),  # Reduced limit to avoid 400 Bad Request errors
            "offset": offset,
            "translatedLanguage[]": translated_language,
            "contentRating[]": ["safe", "suggestive", "erotica"],  # Default content ratings
            f"order[{order_by}]": order_direction,
            "includes[]": ["scanlation_group", "user"],  # Include relationships
        }

        logger.info(
            f"Fetching chapters for manga {manga_id}: language={translated_language}, limit={limit}"
        )

        try:
            response_data = await self._make_request("GET", "/chapter", params=params)

            # Import here to avoid circular imports
            from kiremisu.database.schemas import MangaDxChapterListResponse

            return MangaDxChapterListResponse(**response_data)

        except Exception as e:
            logger.error(f"Error fetching chapters for manga {manga_id}: {e}")
            raise

    async def get_chapter_at_home_server(self, chapter_id: str) -> "MangaDxAtHomeResponse":
        """
        Get @Home server information for chapter page downloads.

        Args:
            chapter_id: MangaDx chapter UUID

        Returns:
            MangaDxAtHomeResponse with server URL and page data

        Raises:
            MangaDxError: For API errors
            MangaDxNotFoundError: If chapter not found
        """
        logger.info(f"Getting @Home server info for chapter {chapter_id}")

        try:
            response_data = await self._make_request("GET", f"/at-home/server/{chapter_id}")

            # Import here to avoid circular imports
            from kiremisu.database.schemas import MangaDxAtHomeResponse

            return MangaDxAtHomeResponse(**response_data)

        except Exception as e:
            logger.error(f"Error getting @Home server for chapter {chapter_id}: {e}")
            raise

    async def download_chapter_pages(
        self,
        chapter_id: str,
        base_url: str,
        chapter_hash: str,
        page_filenames: List[str],
        quality: str = "data",
        max_concurrent: int = 3,
        timeout_per_page: float = 30.0,
    ) -> List[bytes]:
        """
        Download all pages for a chapter from MangaDx @Home network.

        Args:
            chapter_id: MangaDx chapter UUID (for logging)
            base_url: @Home server base URL
            chapter_hash: Chapter hash for URL construction
            page_filenames: List of page filenames to download
            quality: Quality setting ("data" for full, "data-saver" for compressed)
            max_concurrent: Maximum concurrent downloads
            timeout_per_page: Timeout per page download in seconds

        Returns:
            List of downloaded page image data as bytes

        Raises:
            MangaDxError: For download errors
        """
        if not page_filenames:
            logger.warning(f"No pages to download for chapter {chapter_id}")
            return []

        logger.info(
            f"Downloading {len(page_filenames)} pages for chapter {chapter_id} at {quality} quality"
        )

        # Construct page URLs
        quality_path = "data-saver" if quality == "data-saver" else "data"
        page_urls = [
            f"{base_url}/{quality_path}/{chapter_hash}/{filename}" for filename in page_filenames
        ]

        downloaded_pages = []
        failed_downloads = []

        # Create a semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_single_page(url: str, page_index: int) -> tuple[int, bytes]:
            """Download a single page with rate limiting."""
            async with semaphore:
                # Apply rate limiting before each page download
                await self.rate_limiter.acquire()

                try:
                    logger.debug(f"Downloading page {page_index + 1}/{len(page_urls)}: {url}")

                    response = await self.client.get(
                        url,
                        timeout=httpx.Timeout(timeout_per_page),
                        follow_redirects=True,
                    )

                    if response.status_code == 200:
                        return page_index, response.content
                    else:
                        raise MangaDxError(
                            f"Failed to download page {page_index + 1}: HTTP {response.status_code}"
                        )

                except httpx.TimeoutException:
                    raise MangaDxError(f"Timeout downloading page {page_index + 1}")
                except httpx.NetworkError as e:
                    raise MangaDxError(f"Network error downloading page {page_index + 1}: {e}")

        # Download all pages concurrently
        try:
            download_tasks = [download_single_page(url, i) for i, url in enumerate(page_urls)]

            # Use asyncio.gather with return_exceptions to handle individual failures
            results = await asyncio.gather(*download_tasks, return_exceptions=True)

            # Process results and separate successful downloads from failures
            for result in results:
                if isinstance(result, Exception):
                    failed_downloads.append(str(result))
                    downloaded_pages.append(None)  # Placeholder for failed download
                else:
                    page_index, page_data = result
                    downloaded_pages.append((page_index, page_data))

            # Sort by page index to maintain order
            downloaded_pages = [
                data for _, data in sorted([p for p in downloaded_pages if p is not None])
            ]

            if failed_downloads:
                error_summary = f"{len(failed_downloads)} pages failed to download"
                logger.error(f"Chapter {chapter_id} download incomplete: {error_summary}")

                # If more than 20% of pages failed, raise an error
                failure_rate = len(failed_downloads) / len(page_urls)
                if failure_rate > 0.2:
                    raise MangaDxError(
                        f"Too many page download failures ({failure_rate:.1%}): {error_summary}"
                    )

            logger.info(
                f"Downloaded {len(downloaded_pages)}/{len(page_urls)} pages for chapter {chapter_id}"
            )
            return downloaded_pages

        except Exception as e:
            logger.error(f"Failed to download pages for chapter {chapter_id}: {e}")
            raise MangaDxError(f"Page download failed: {e}")

    async def download_full_chapter(
        self,
        chapter_id: str,
        quality: str = "data",
        max_concurrent: int = 3,
    ) -> "MangaDxDownloadedChapter":
        """
        Download a complete chapter including metadata and all pages.

        This is a convenience method that combines chapter metadata fetching,
        @Home server lookup, and page downloads into a single operation.

        Args:
            chapter_id: MangaDx chapter UUID
            quality: Quality setting ("data" for full, "data-saver" for compressed)
            max_concurrent: Maximum concurrent page downloads

        Returns:
            MangaDxDownloadedChapter with chapter info and downloaded data

        Raises:
            MangaDxError: For any step of the download process
        """
        start_time = time.time()

        logger.info(f"Starting full chapter download: {chapter_id} at {quality} quality")

        try:
            # Step 1: Get chapter metadata
            logger.debug(f"Fetching chapter metadata for {chapter_id}")
            chapter_response = await self._make_request("GET", f"/chapter/{chapter_id}")

            # Import here to avoid circular imports
            from kiremisu.database.schemas import MangaDxChapterResponse, MangaDxDownloadedChapter

            chapter_data = MangaDxChapterResponse(**chapter_response["data"])

            # Step 2: Get @Home server info
            logger.debug(f"Getting @Home server info for {chapter_id}")
            at_home_response = await self.get_chapter_at_home_server(chapter_id)

            # Step 3: Download all pages
            page_filenames = at_home_response.chapter.get_page_filenames(quality)
            page_data_list = await self.download_chapter_pages(
                chapter_id=chapter_id,
                base_url=at_home_response.base_url,
                chapter_hash=at_home_response.chapter.hash,
                page_filenames=page_filenames,
                quality=quality,
                max_concurrent=max_concurrent,
            )

            # Calculate download statistics
            download_duration = time.time() - start_time
            total_size = sum(len(page_data) for page_data in page_data_list)

            logger.info(
                f"Chapter {chapter_id} download completed: {len(page_data_list)} pages, "
                f"{total_size / 1024 / 1024:.1f}MB in {download_duration:.1f}s"
            )

            # Return download result (without actual page data to save memory)
            return MangaDxDownloadedChapter(
                chapter_id=chapter_id,
                title=chapter_data.attributes.title,
                chapter_number=chapter_data.get_chapter_number(),
                volume_number=chapter_data.get_volume_number(),
                file_path="",  # Will be set by the download service when CBZ is created
                file_size=total_size,
                page_count=len(page_data_list),
                download_quality=quality,
                download_duration_seconds=download_duration,
            ), page_data_list

        except Exception as e:
            logger.error(f"Full chapter download failed for {chapter_id}: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if MangaDx API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # The /ping endpoint returns text/plain "pong", not JSON
            # So we need to handle this differently
            url = urljoin(self.BASE_URL, "/ping")

            await self.rate_limiter.acquire()
            response = await self.client.get(url)

            # Check if response is successful and contains expected text
            if response.status_code == 200 and response.text.strip() == "pong":
                return True
            else:
                logger.warning(
                    f"MangaDx health check unexpected response: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.warning(f"MangaDx API health check failed: {e}")
            return False
