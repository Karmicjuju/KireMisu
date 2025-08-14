"""Integration tests for MangaDx API endpoints."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from kiremisu.services.mangadx_client import (
    MangaDxClient,
    MangaDxMangaResponse,
    MangaDxNotFoundError,
    MangaDxRateLimitError,
    MangaDxSearchResponse,
)
from kiremisu.services.mangadx_import import MangaDxImportError, MangaDxImportService


@pytest.mark.api
class TestMangaDxAPI:
    """Integration tests for MangaDx API endpoints."""

    @pytest.fixture
    def mock_mangadx_client(self):
        """Mock MangaDx client for testing."""
        return AsyncMock(spec=MangaDxClient)

    @pytest.fixture
    def mock_import_service(self):
        """Mock import service for testing."""
        return AsyncMock(spec=MangaDxImportService)

    @pytest.fixture
    def sample_manga_data(self):
        """Sample manga data for testing."""
        return {
            "id": "test-manga-id",
            "type": "manga",
            "title": {"en": "Test Manga"},
            "altTitles": [{"ja": "テストマンガ"}],
            "description": {"en": "Test description"},
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
                }
            ],
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

    @pytest.mark.asyncio
    async def test_health_check_success(self, async_test_client, mock_mangadx_client):
        """Test successful health check."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            mock_mangadx_client.health_check.return_value = True

            response = await async_test_client.get("/api/mangadx/health")

            assert response.status_code == 200
            data = response.json()
            assert data["api_accessible"] is True
            assert "response_time_ms" in data
            assert "last_check" in data
            assert data["error_message"] is None

    @pytest.mark.asyncio
    async def test_health_check_failure(self, async_test_client, mock_mangadx_client):
        """Test failed health check."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            mock_mangadx_client.health_check.return_value = False

            response = await async_test_client.get("/api/mangadx/health")

            assert response.status_code == 200
            data = response.json()
            assert data["api_accessible"] is False
            assert data["error_message"] == "API health check failed"

    @pytest.mark.asyncio
    async def test_search_manga_success(self, async_test_client, mock_mangadx_client, sample_manga_data):
        """Test successful manga search."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            # Mock search response
            mock_search_response = MangaDxSearchResponse(
                result="ok",
                response="collection",
                data=[MangaDxMangaResponse(**sample_manga_data)],
                limit=20,
                offset=0,
                total=1
            )
            mock_mangadx_client.search_manga.return_value = mock_search_response
            mock_mangadx_client.get_cover_art_url.return_value = "https://example.com/cover.jpg"

            search_data = {
                "title": "Test Manga",
                "limit": 10
            }

            response = await async_test_client.post("/api/mangadx/search", json=search_data)

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["title"] == "Test Manga"
            assert data["results"][0]["id"] == "test-manga-id"
            assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_search_manga_validation_error(self, async_test_client):
        """Test search with invalid parameters."""
        search_data = {
            "title": "Test Manga",
            "limit": 150,  # Exceeds maximum
            "status": ["invalid_status"]  # Invalid status
        }

        response = await async_test_client.post("/api/mangadx/search", json=search_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_manga_rate_limit_error(self, async_test_client, mock_mangadx_client):
        """Test search with rate limit error."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            mock_mangadx_client.search_manga.side_effect = MangaDxRateLimitError(retry_after=60)

            search_data = {"title": "Test Manga"}

            response = await async_test_client.post("/api/mangadx/search", json=search_data)

            assert response.status_code == 429
            data = response.json()
            assert data["detail"]["error"] == "rate_limit_exceeded"
            assert data["detail"]["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_get_manga_details_success(self, async_test_client, mock_mangadx_client, sample_manga_data):
        """Test successful manga details retrieval."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            mock_mangadx_client.get_manga.return_value = MangaDxMangaResponse(**sample_manga_data)
            mock_mangadx_client.get_cover_art_url.return_value = "https://example.com/cover.jpg"

            response = await async_test_client.get("/api/mangadx/manga/test-manga-id")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-manga-id"
            assert data["title"] == "Test Manga"
            assert data["author"] == "Test Author"
            assert "Action" in data["genres"]

    @pytest.mark.asyncio
    async def test_get_manga_details_not_found(self, async_test_client, mock_mangadx_client):
        """Test manga details with not found error."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            mock_mangadx_client.get_manga.side_effect = MangaDxNotFoundError("Manga not found")

            response = await async_test_client.get("/api/mangadx/manga/invalid-id")

            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_import_manga_metadata_success(self, async_test_client, mock_import_service):
        """Test successful metadata import."""
        with patch('kiremisu.api.mangadx.get_import_service', return_value=mock_import_service):
            # Mock successful import result
            from kiremisu.database.schemas import MangaDxImportResult
            mock_result = MangaDxImportResult(
                success=True,
                series_id=uuid4(),
                mangadx_id="test-manga-id",
                operation="created",
                metadata_fields_updated=["title", "description", "author"],
                cover_art_downloaded=True,
                chapters_imported=0,
                warnings=[],
                errors=[],
                import_duration_ms=500,
            )
            mock_import_service.import_series_metadata.return_value = mock_result

            import_data = {
                "mangadx_id": "test-manga-id",
                "import_cover_art": True
            }

            response = await async_test_client.post("/api/mangadx/import", json=import_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["success"] is True
            assert data["result"]["operation"] == "created"

    @pytest.mark.asyncio
    async def test_import_manga_metadata_validation_error(self, async_test_client):
        """Test import with invalid data."""
        import_data = {
            "mangadx_id": "",  # Empty ID
        }

        response = await async_test_client.post("/api/mangadx/import", json=import_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_import_manga_metadata_import_error(self, async_test_client, mock_import_service):
        """Test import with service error."""
        with patch('kiremisu.api.mangadx.get_import_service', return_value=mock_import_service):
            mock_import_service.import_series_metadata.side_effect = MangaDxImportError("Import failed")

            import_data = {"mangadx_id": "test-manga-id"}

            response = await async_test_client.post("/api/mangadx/import", json=import_data)

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "import_error"

    @pytest.mark.asyncio
    async def test_find_enrichment_candidates_success(self, async_test_client, mock_import_service):
        """Test successful enrichment candidate search."""
        with patch('kiremisu.api.mangadx.get_import_service', return_value=mock_import_service):
            # Mock enrichment response
            from kiremisu.database.schemas import (
                MangaDxEnrichmentCandidate,
                MangaDxEnrichmentResponse,
                MangaDxMangaInfo,
            )

            manga_info = MangaDxMangaInfo(
                id="test-manga-id",
                title="Test Manga",
                status="ongoing",
                content_rating="safe",
                original_language="ja",
            )

            candidate = MangaDxEnrichmentCandidate(
                mangadx_info=manga_info,
                confidence_score=0.9,
                match_reasons=["Primary title match (0.95)"],
                is_recommended=True,
            )

            mock_response = MangaDxEnrichmentResponse(
                series_id=uuid4(),
                series_title="Test Manga",
                candidates=[candidate],
                auto_selected=candidate,
                search_query_used="Test Manga",
                total_candidates=1,
            )

            mock_import_service.search_and_match_series.return_value = mock_response

            series_id = str(uuid4())
            enrichment_data = {
                "series_id": series_id,
                "auto_select_best_match": True,
                "confidence_threshold": 0.8
            }

            response = await async_test_client.post(f"/api/mangadx/enrich/{series_id}", json=enrichment_data)

            assert response.status_code == 200
            data = response.json()
            assert data["series_title"] == "Test Manga"
            assert len(data["candidates"]) == 1
            assert data["candidates"][0]["confidence_score"] == 0.9
            assert data["auto_selected"] is not None

    @pytest.mark.asyncio
    async def test_find_enrichment_candidates_series_not_found(self, async_test_client, mock_import_service):
        """Test enrichment with non-existent series."""
        with patch('kiremisu.api.mangadx.get_import_service', return_value=mock_import_service):
            mock_import_service.search_and_match_series.side_effect = MangaDxImportError("Series not found")

            series_id = str(uuid4())
            enrichment_data = {"series_id": series_id}

            response = await async_test_client.post(f"/api/mangadx/enrich/{series_id}", json=enrichment_data)

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "import_error"

    @pytest.mark.asyncio
    async def test_bulk_import_not_implemented(self, async_test_client):
        """Test bulk import endpoint (not yet implemented)."""
        bulk_data = {
            "import_requests": [
                {"mangadx_id": "test-id-1"},
                {"mangadx_id": "test-id-2"}
            ]
        }

        response = await async_test_client.post("/api/mangadx/bulk-import", json=bulk_data)

        assert response.status_code == 501
        data = response.json()
        assert data["detail"]["error"] == "not_implemented"

    @pytest.mark.asyncio
    async def test_error_handling_generic_exception(self, async_test_client, mock_mangadx_client):
        """Test generic exception handling."""
        with patch('kiremisu.api.mangadx.get_mangadx_client', return_value=mock_mangadx_client):
            mock_mangadx_client.search_manga.side_effect = Exception("Unexpected error")

            search_data = {"title": "Test Manga"}

            response = await async_test_client.post("/api/mangadx/search", json=search_data)

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "internal_error"

    def test_search_manga_comprehensive_parameters(self, test_client):
        """Test search with all possible parameters."""
        with patch('kiremisu.api.mangadx.get_mangadx_client') as mock_get_client:
            mock_client = AsyncMock(spec=MangaDxClient)
            mock_get_client.return_value = mock_client

            # Mock empty search response
            mock_search_response = MangaDxSearchResponse(
                result="ok",
                response="collection",
                data=[],
                limit=10,
                offset=0,
                total=0
            )
            mock_client.search_manga.return_value = mock_search_response

            search_data = {
                "title": "Test Manga",
                "author": "Test Author",
                "artist": "Test Artist",
                "year": 2020,
                "status": ["ongoing", "completed"],
                "content_rating": ["safe", "suggestive"],
                "original_language": ["ja", "en"],
                "limit": 10,
                "offset": 20
            }

            response = test_client.post("/api/mangadx/search", json=search_data)

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["limit"] == 10
            assert data["offset"] == 0

            # Verify all parameters were passed to client
            mock_client.search_manga.assert_called_once()
            call_kwargs = mock_client.search_manga.call_args.kwargs
            assert call_kwargs["title"] == "Test Manga"
            assert call_kwargs["author"] == "Test Author"
            assert call_kwargs["artist"] == "Test Artist"
            assert call_kwargs["year"] == 2020
            assert call_kwargs["status"] == ["ongoing", "completed"]

    def test_import_metadata_with_all_options(self, test_client):
        """Test import with all available options."""
        with patch('kiremisu.api.mangadx.get_import_service') as mock_get_service:
            mock_service = AsyncMock(spec=MangaDxImportService)
            mock_get_service.return_value = mock_service

            # Mock successful import
            from kiremisu.database.schemas import MangaDxImportResult
            mock_result = MangaDxImportResult(
                success=True,
                series_id=uuid4(),
                mangadx_id="test-manga-id",
                operation="enriched",
                metadata_fields_updated=["description", "genres", "cover_image_path"],
                cover_art_downloaded=True,
                chapters_imported=0,
                warnings=["Minor warning"],
                errors=[],
                import_duration_ms=750,
            )
            mock_service.import_series_metadata.return_value = mock_result

            import_data = {
                "mangadx_id": "test-manga-id",
                "target_series_id": str(uuid4()),
                "import_cover_art": True,
                "import_chapters": False,
                "overwrite_existing": True,
                "custom_title": "Custom Title Override"
            }

            response = test_client.post("/api/mangadx/import", json=import_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["operation"] == "enriched"
            assert data["result"]["cover_art_downloaded"] is True
            assert len(data["result"]["warnings"]) == 1
