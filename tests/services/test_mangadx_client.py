"""Unit tests for MangaDx API client."""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx

from kiremisu.services.mangadx_client import (
    MangaDxClient,
    MangaDxError,
    MangaDxNotFoundError,
    MangaDxRateLimitError,
    MangaDxRateLimiter,
    MangaDxServerError,
    MangaDxTitle,
    MangaDxMangaResponse,
    MangaDxSearchResponse,
)


class TestMangaDxTitle:
    """Test MangaDx title handling."""
    
    def test_get_primary_title_english_preferred(self):
        """Test that English title is preferred."""
        title = MangaDxTitle(en="English Title", ja="Japanese Title", ja_ro="Romanized Title")
        assert title.get_primary_title() == "English Title"
    
    def test_get_primary_title_fallback_to_romanized(self):
        """Test fallback to romanized Japanese."""
        title = MangaDxTitle(ja="Japanese Title", ja_ro="Romanized Title")
        assert title.get_primary_title() == "Romanized Title"
    
    def test_get_primary_title_fallback_to_japanese(self):
        """Test fallback to Japanese."""
        title = MangaDxTitle(ja="Japanese Title")
        assert title.get_primary_title() == "Japanese Title"
    
    def test_get_primary_title_default(self):
        """Test default when no titles available."""
        title = MangaDxTitle()
        assert title.get_primary_title() == "Unknown Title"
    
    def test_get_alternative_titles(self):
        """Test alternative titles extraction."""
        title = MangaDxTitle(en="English Title", ja="Japanese Title", ja_ro="Romanized Title")
        alternatives = title.get_alternative_titles()
        assert "Romanized Title" in alternatives
        assert "Japanese Title" in alternatives
        assert "English Title" not in alternatives


class TestMangaDxRateLimiter:
    """Test MangaDx rate limiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_delays_requests(self):
        """Test that rate limiter adds delays between requests."""
        limiter = MangaDxRateLimiter(requests_per_second=10.0)  # 0.1s between requests
        
        start_time = time.time()
        
        # First request should be immediate
        await limiter.acquire()
        first_request_time = time.time() - start_time
        assert first_request_time < 0.01  # Should be nearly instant
        
        # Second request should be delayed
        await limiter.acquire()
        second_request_time = time.time() - start_time
        assert second_request_time >= 0.1  # Should be at least 0.1s
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test that rate limiter works correctly with concurrent requests."""
        limiter = MangaDxRateLimiter(requests_per_second=5.0)  # 0.2s between requests
        
        start_time = time.time()
        
        # Make 3 concurrent requests
        tasks = [limiter.acquire() for _ in range(3)]
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        # Should take at least 0.4s (2 * 0.2s delays)
        assert total_time >= 0.4


class TestMangaDxClient:
    """Test MangaDx API client."""
    
    @pytest.fixture
    def mock_manga_response(self):
        """Mock MangaDx manga API response."""
        return {
            "data": {
                "id": "test-manga-id",
                "type": "manga",
                "attributes": {
                    "title": {"en": "Test Manga"},
                    "altTitles": [{"ja": "テストマンガ"}],
                    "description": {"en": "Test description"},
                    "isLocked": False,
                    "originalLanguage": "ja",
                    "status": "ongoing",
                    "contentRating": "safe",
                    "tags": [
                        {
                            "id": "tag-1",
                            "type": "tag",
                            "attributes": {
                                "name": {"en": "Action"},
                                "group": "genre"
                            }
                        }
                    ],
                    "year": 2020,
                    "createdAt": "2020-01-01T00:00:00+00:00",
                    "updatedAt": "2023-01-01T00:00:00+00:00",
                },
                "relationships": [
                    {
                        "id": "author-id",
                        "type": "author",
                        "attributes": {"name": "Test Author"}
                    },
                    {
                        "id": "cover-id",
                        "type": "cover_art",
                        "attributes": {"fileName": "test-cover.jpg"}
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_search_response(self, mock_manga_response):
        """Mock MangaDx search API response."""
        return {
            "result": "ok",
            "response": "collection",
            "data": [mock_manga_response["data"]],
            "limit": 20,
            "offset": 0,
            "total": 1
        }
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        client = MangaDxClient(timeout=10.0, requests_per_second=2.0)
        
        assert client.timeout == 10.0
        assert client.rate_limiter.requests_per_second == 2.0
        assert client.BASE_URL == "https://api.mangadx.org"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with MangaDxClient() as client:
            assert client is not None
        # Client should be closed automatically
    
    @pytest.mark.asyncio
    async def test_successful_request(self, mock_search_response):
        """Test successful API request."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            mock_request.return_value = mock_response
            
            client = MangaDxClient()
            result = await client._make_request("GET", "/manga")
            
            assert result == mock_search_response
            mock_request.assert_called_once()
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_404_error_handling(self):
        """Test 404 error handling."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"error": "Not found"}
            mock_response.content = b'{"error": "Not found"}'
            mock_request.return_value = mock_response
            
            client = MangaDxClient()
            
            with pytest.raises(MangaDxNotFoundError):
                await client._make_request("GET", "/manga/invalid-id")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test rate limit error handling."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            # First request returns 429, second succeeds
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {"Retry-After": "1"}
            
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {"result": "ok"}
            
            mock_request.side_effect = [rate_limit_response, success_response]
            
            client = MangaDxClient(max_retries=1)
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await client._make_request("GET", "/manga")
                
                assert result == {"result": "ok"}
                mock_sleep.assert_called_once_with(1)  # Should sleep for Retry-After duration
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeded after all retries."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_request.return_value = mock_response
            
            client = MangaDxClient(max_retries=1)
            
            with pytest.raises(MangaDxRateLimitError) as exc_info:
                await client._make_request("GET", "/manga")
            
            assert exc_info.value.retry_after == 60
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_server_error_retry(self):
        """Test server error retry logic."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            # First request returns 500, second succeeds
            server_error_response = Mock()
            server_error_response.status_code = 500
            server_error_response.json.return_value = {"error": "Server error"}
            server_error_response.content = b'{"error": "Server error"}'
            
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {"result": "ok"}
            
            mock_request.side_effect = [server_error_response, success_response]
            
            client = MangaDxClient(max_retries=1, retry_delay=0.1)
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await client._make_request("GET", "/manga")
                
                assert result == {"result": "ok"}
                mock_sleep.assert_called_once_with(0.1)  # Should use retry_delay
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_server_error_exceeded_retries(self):
        """Test server error after all retries exhausted."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": "Server error"}
            mock_response.content = b'{"error": "Server error"}'
            mock_request.return_value = mock_response
            
            client = MangaDxClient(max_retries=1)
            
            with pytest.raises(MangaDxServerError):
                await client._make_request("GET", "/manga")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout error handling."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timeout")
            
            client = MangaDxClient(max_retries=1)
            
            with pytest.raises(MangaDxError, match="Request timeout after all retries"):
                await client._make_request("GET", "/manga")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test network error handling."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_request.side_effect = httpx.NetworkError("Network error")
            
            client = MangaDxClient(max_retries=1)
            
            with pytest.raises(MangaDxError, match="Network error after all retries"):
                await client._make_request("GET", "/manga")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_search_manga(self, mock_search_response):
        """Test manga search functionality."""
        with patch.object(MangaDxClient, '_make_request') as mock_request:
            mock_request.return_value = mock_search_response
            
            client = MangaDxClient()
            result = await client.search_manga(title="Test Manga", limit=10)
            
            assert isinstance(result, MangaDxSearchResponse)
            assert len(result.data) == 1
            assert result.total == 1
            assert result.limit == 20
            
            # Verify request parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("GET", "/manga")
            params = call_args[1]["params"]
            assert params["title"] == "Test Manga"
            assert params["limit"] == 10
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_get_manga(self, mock_manga_response):
        """Test get manga by ID functionality."""
        with patch.object(MangaDxClient, '_make_request') as mock_request:
            mock_request.return_value = mock_manga_response
            
            client = MangaDxClient()
            result = await client.get_manga("test-manga-id")
            
            assert isinstance(result, MangaDxMangaResponse)
            assert result.id == "test-manga-id"
            
            # Verify request parameters
            mock_request.assert_called_once_with(
                "GET", "/manga/test-manga-id", params={"includes[]": ["author", "artist", "cover_art"]}
            )
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_get_cover_art_url(self):
        """Test cover art URL generation."""
        client = MangaDxClient()
        
        # Test with specific size
        url = client.get_cover_art_url("manga-id", "cover.jpg", size="512")
        expected = "https://uploads.mangadx.org/covers/manga-id/cover.jpg.512.jpg"
        assert url == expected
        
        # Test with original size
        url = client.get_cover_art_url("manga-id", "cover.jpg", size="original")
        expected = "https://uploads.mangadx.org/covers/manga-id/cover.jpg"
        assert url == expected
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with patch.object(MangaDxClient, '_make_request') as mock_request:
            mock_request.return_value = {"status": "ok"}
            
            client = MangaDxClient()
            result = await client.health_check()
            
            assert result is True
            mock_request.assert_called_once_with("GET", "/ping")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        with patch.object(MangaDxClient, '_make_request') as mock_request:
            mock_request.side_effect = MangaDxError("API error")
            
            client = MangaDxClient()
            result = await client.health_check()
            
            assert result is False
            
            await client.close()


class TestMangaDxMangaResponse:
    """Test MangaDx manga response parsing."""
    
    @pytest.fixture
    def sample_manga_data(self):
        """Sample manga data for testing."""
        return {
            "id": "test-id",
            "type": "manga",
            "title": {"en": "English Title", "ja": "日本語タイトル", "ja-ro": "Nihongo Title"},
            "altTitles": [{"es": "Título Español"}],
            "description": {"en": "English description", "ja": "日本語の説明"},
            "status": "ongoing",
            "contentRating": "safe",
            "originalLanguage": "ja",
            "year": 2020,
            "tags": [
                {
                    "id": "tag-1",
                    "attributes": {
                        "name": {"en": "Action"},
                        "group": "genre"
                    }
                },
                {
                    "id": "tag-2", 
                    "attributes": {
                        "name": {"en": "School Life"},
                        "group": "theme"
                    }
                }
            ],
            "relationships": [
                {
                    "id": "author-id",
                    "type": "author",
                    "attributes": {"name": "Test Author"}
                },
                {
                    "id": "artist-id",
                    "type": "artist", 
                    "attributes": {"name": "Test Artist"}
                }
            ]
        }
    
    def test_title_extraction(self, sample_manga_data):
        """Test title extraction from manga data."""
        manga = MangaDxMangaResponse(**sample_manga_data)
        title_info = manga.get_title_info()
        
        assert title_info.en == "English Title"
        assert title_info.ja == "日本語タイトル"
        assert title_info.ja_ro == "Nihongo Title"
        assert title_info.get_primary_title() == "English Title"
    
    def test_description_extraction(self, sample_manga_data):
        """Test description extraction."""
        manga = MangaDxMangaResponse(**sample_manga_data)
        description = manga.get_description()
        
        assert description == "English description"
    
    def test_genres_and_tags_extraction(self, sample_manga_data):
        """Test genres and tags extraction."""
        manga = MangaDxMangaResponse(**sample_manga_data)
        genres, tags = manga.get_genres_and_tags()
        
        assert "Action" in genres
        assert "School Life" in tags
    
    def test_author_info_extraction(self, sample_manga_data):
        """Test author and artist extraction."""
        manga = MangaDxMangaResponse(**sample_manga_data)
        author, artist = manga.get_author_info()
        
        assert author == "Test Author"
        assert artist == "Test Artist"