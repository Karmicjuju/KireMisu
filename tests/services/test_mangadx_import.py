"""Unit tests for MangaDx import service."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Series
from kiremisu.database.schemas import (
    MangaDxEnrichmentResponse,
    MangaDxImportRequest,
    MangaDxImportResult,
    MangaDxMangaInfo,
)
from kiremisu.services.mangadx_client import MangaDxClient, MangaDxMangaResponse
from kiremisu.services.mangadx_import import MangaDxImportError, MangaDxImportService


class TestMangaDxImportService:
    """Test MangaDx import service."""

    @pytest.fixture
    def mock_mangadx_client(self):
        """Mock MangaDx client."""
        return Mock(spec=MangaDxClient)

    @pytest.fixture
    def import_service(self, mock_mangadx_client, tmp_path):
        """Create import service with mocked dependencies."""
        return MangaDxImportService(
            mangadx_client=mock_mangadx_client,
            cover_storage_path=str(tmp_path / "covers"),
            max_title_similarity_threshold=0.6,
            auto_confidence_threshold=0.85,
        )

    @pytest.fixture
    def sample_mangadx_manga(self):
        """Sample MangaDx manga response."""
        return MangaDxMangaResponse(
            id="test-manga-id",
            title={"en": "Test Manga", "ja": "テストマンガ"},
            altTitles=[{"ja-ro": "Tesuto Manga"}],
            description={"en": "A test manga description"},
            status="ongoing",
            contentRating="safe",
            originalLanguage="ja",
            year=2020,
            tags=[
                {
                    "id": "tag-1",
                    "attributes": {
                        "name": {"en": "Action"},
                        "group": "genre"
                    }
                }
            ],
            relationships=[
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
            ],
            createdAt="2020-01-01T00:00:00+00:00",
            updatedAt="2023-01-01T00:00:00+00:00",
        )

    @pytest.fixture
    def sample_local_series(self):
        """Sample local series for testing."""
        return Series(
            id=uuid4(),
            title_primary="Test Manga",
            author="Test Author",
            description="Local description",
            genres=["Action"],
            language="en",
        )

    def test_initialization(self, import_service, tmp_path):
        """Test service initialization."""
        assert import_service.cover_storage_path == tmp_path / "covers"
        assert import_service.max_title_similarity_threshold == 0.6
        assert import_service.auto_confidence_threshold == 0.85

        # Check that cover directory was created
        assert (tmp_path / "covers").exists()

    def test_convert_mangadx_to_manga_info(self, import_service, sample_mangadx_manga):
        """Test conversion from MangaDx response to MangaDxMangaInfo."""
        with patch.object(import_service.mangadx_client, 'get_cover_art_url') as mock_cover_url:
            mock_cover_url.return_value = "https://example.com/cover.jpg"

            manga_info = import_service._convert_mangadx_to_manga_info(sample_mangadx_manga)

            assert isinstance(manga_info, MangaDxMangaInfo)
            assert manga_info.id == "test-manga-id"
            assert manga_info.title == "Test Manga"
            assert "Tesuto Manga" in manga_info.alternative_titles
            assert manga_info.description == "A test manga description"
            assert manga_info.author == "Test Author"
            assert "Action" in manga_info.genres
            assert manga_info.status == "ongoing"
            assert manga_info.cover_art_url == "https://example.com/cover.jpg"

    def test_calculate_title_similarity(self, import_service):
        """Test title similarity calculation."""
        # Exact match
        assert import_service._calculate_title_similarity("Test Manga", "Test Manga") == 1.0

        # Similar titles
        similarity = import_service._calculate_title_similarity("Test Manga", "Test Manga Series")
        assert 0.7 < similarity < 1.0

        # Different titles
        similarity = import_service._calculate_title_similarity("Test Manga", "Completely Different")
        assert similarity < 0.3

        # Case insensitive
        similarity = import_service._calculate_title_similarity("Test Manga", "test manga")
        assert similarity == 1.0

        # Empty strings
        assert import_service._calculate_title_similarity("", "Test") == 0.0
        assert import_service._calculate_title_similarity("Test", "") == 0.0

    def test_calculate_match_confidence_high_confidence(self, import_service, sample_local_series):
        """Test confidence calculation for high-confidence match."""
        mangadx_info = MangaDxMangaInfo(
            id="test-id",
            title="Test Manga",  # Exact title match
            author="Test Author",  # Exact author match
            genres=["Action"],  # Genre overlap
            status="ongoing",
            content_rating="safe",
            original_language="ja",
        )

        confidence, reasons = import_service._calculate_match_confidence(sample_local_series, mangadx_info)

        assert confidence > 0.8  # Should be high confidence
        assert "Primary title match" in str(reasons)
        assert "Author match" in str(reasons)
        assert "Genre overlap" in str(reasons)

    def test_calculate_match_confidence_low_confidence(self, import_service, sample_local_series):
        """Test confidence calculation for low-confidence match."""
        mangadx_info = MangaDxMangaInfo(
            id="test-id",
            title="Completely Different Title",
            author="Different Author",
            genres=["Romance"],  # No genre overlap
            status="ongoing",
            content_rating="safe",
            original_language="ja",
        )

        confidence, reasons = import_service._calculate_match_confidence(sample_local_series, mangadx_info)

        assert confidence < 0.5  # Should be low confidence
        assert len(reasons) == 0  # No good matches

    def test_calculate_match_confidence_alternative_title_match(self, import_service, sample_local_series):
        """Test confidence calculation with alternative title match."""
        mangadx_info = MangaDxMangaInfo(
            id="test-id",
            title="Different Primary Title",
            alternative_titles=["Test Manga"],  # Matches local title
            status="ongoing",
            content_rating="safe",
            original_language="ja",
        )

        confidence, reasons = import_service._calculate_match_confidence(sample_local_series, mangadx_info)

        assert confidence > 0.3  # Should have some confidence from alt title
        assert "Alternative title match" in str(reasons)

    @pytest.mark.asyncio
    async def test_download_cover_art_success(self, import_service, tmp_path):
        """Test successful cover art download."""
        cover_url = "https://example.com/cover.jpg"
        manga_id = "test-manga-id"

        mock_response = Mock()
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.content = b"fake image data"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await import_service._download_cover_art(cover_url, manga_id)

            assert result is not None
            assert Path(result).exists()
            assert Path(result).name.startswith(manga_id)

            # Verify file content
            with open(result, 'rb') as f:
                assert f.read() == b"fake image data"

    @pytest.mark.asyncio
    async def test_download_cover_art_invalid_content_type(self, import_service):
        """Test cover art download with invalid content type."""
        cover_url = "https://example.com/cover.txt"
        manga_id = "test-manga-id"

        mock_response = Mock()
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = b"not an image"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await import_service._download_cover_art(cover_url, manga_id)

            assert result is None

    @pytest.mark.asyncio
    async def test_download_cover_art_already_exists(self, import_service, tmp_path):
        """Test cover art download when file already exists."""
        cover_url = "https://example.com/cover.jpg"
        manga_id = "test-manga-id"

        # Create existing file
        import hashlib
        url_hash = hashlib.md5(cover_url.encode()).hexdigest()[:8]
        existing_file = tmp_path / "covers" / f"{manga_id}_{url_hash}.jpg"
        existing_file.write_bytes(b"existing data")

        result = await import_service._download_cover_art(cover_url, manga_id)

        assert result == str(existing_file)
        # Should not make HTTP request since file exists

    @pytest.mark.asyncio
    async def test_import_series_metadata_create_new(self, import_service, sample_mangadx_manga):
        """Test importing metadata to create new series."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        import_request = MangaDxImportRequest(
            mangadx_id="test-manga-id",
            import_cover_art=False,  # Skip cover art for this test
        )

        # Mock MangaDx client response
        import_service.mangadx_client.get_manga.return_value = sample_mangadx_manga

        result = await import_service.import_series_metadata(mock_db_session, import_request)

        assert isinstance(result, MangaDxImportResult)
        assert result.success is True
        assert result.operation == "created"
        assert result.mangadx_id == "test-manga-id"
        assert "description" in result.metadata_fields_updated
        assert "author" in result.metadata_fields_updated
        assert "mangadx_id" in result.metadata_fields_updated

        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_series_metadata_enrich_existing(self, import_service, sample_mangadx_manga, sample_local_series):
        """Test enriching existing series with metadata."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        # Mock database query to return existing series
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_local_series
        mock_db_session.execute.return_value = mock_result

        import_request = MangaDxImportRequest(
            mangadx_id="test-manga-id",
            target_series_id=sample_local_series.id,
            import_cover_art=False,
            overwrite_existing=True,
        )

        # Mock MangaDx client response
        import_service.mangadx_client.get_manga.return_value = sample_mangadx_manga

        result = await import_service.import_series_metadata(mock_db_session, import_request)

        assert result.success is True
        assert result.operation == "enriched"
        assert result.series_id == sample_local_series.id

        # Verify database operations (no add for existing series)
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_series_metadata_with_cover_art(self, import_service, sample_mangadx_manga):
        """Test importing metadata with cover art download."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        import_request = MangaDxImportRequest(
            mangadx_id="test-manga-id",
            import_cover_art=True,
        )

        # Mock MangaDx client and cover download
        import_service.mangadx_client.get_manga.return_value = sample_mangadx_manga

        with patch.object(import_service, '_download_cover_art') as mock_download:
            mock_download.return_value = "/path/to/cover.jpg"

            result = await import_service.import_series_metadata(mock_db_session, import_request)

            assert result.success is True
            assert result.cover_art_downloaded is True
            assert "cover_image_path" in result.metadata_fields_updated

            mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_series_metadata_error_handling(self, import_service):
        """Test error handling during import."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        import_request = MangaDxImportRequest(mangadx_id="invalid-id")

        # Mock MangaDx client to raise error
        import_service.mangadx_client.get_manga.side_effect = Exception("API error")

        result = await import_service.import_series_metadata(mock_db_session, import_request)

        assert result.success is False
        assert result.operation == "failed"
        assert "API error" in result.errors

        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_and_match_series_success(self, import_service, sample_local_series):
        """Test successful series matching."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        # Mock database query to return local series
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_local_series
        mock_db_session.execute.return_value = mock_result

        # Mock MangaDx search response
        mock_search_response = Mock()
        mock_search_response.data = [sample_mangadx_manga]
        import_service.mangadx_client.search_manga.return_value = mock_search_response

        result = await import_service.search_and_match_series(
            db_session=mock_db_session,
            series_id=sample_local_series.id,
            auto_select_best_match=True,
            confidence_threshold=0.5,
        )

        assert isinstance(result, MangaDxEnrichmentResponse)
        assert result.series_id == sample_local_series.id
        assert result.series_title == sample_local_series.title_primary
        assert len(result.candidates) > 0
        assert result.total_candidates > 0

        # Should have high confidence match
        if result.candidates:
            assert result.candidates[0].confidence_score > 0.5

    @pytest.mark.asyncio
    async def test_search_and_match_series_not_found(self, import_service):
        """Test series matching when local series not found."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        # Mock database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(MangaDxImportError, match="Series not found"):
            await import_service.search_and_match_series(
                db_session=mock_db_session,
                series_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_search_and_match_series_auto_select(self, import_service, sample_local_series, sample_mangadx_manga):
        """Test auto-selection of best match."""
        mock_db_session = AsyncMock(spec=AsyncSession)

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_local_series
        mock_db_session.execute.return_value = mock_result

        # Mock high-confidence search result
        mock_search_response = Mock()
        mock_search_response.data = [sample_mangadx_manga]  # Same title = high confidence
        import_service.mangadx_client.search_manga.return_value = mock_search_response

        result = await import_service.search_and_match_series(
            db_session=mock_db_session,
            series_id=sample_local_series.id,
            auto_select_best_match=True,
            confidence_threshold=0.8,
        )

        assert result.auto_selected is not None
        assert result.auto_selected.confidence_score >= 0.8
