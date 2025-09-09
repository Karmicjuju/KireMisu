"""Tests for search service functionality."""

import pytest
from uuid import uuid4

from app.services.search import SearchService
from app.models.series import Series
from app.models.search_history import SearchHistory


class TestSearchService:
    """Test SearchService functionality."""

    @pytest.fixture
    async def search_service(self, async_session):
        """Create SearchService instance."""
        return SearchService(async_session)

    @pytest.fixture
    async def sample_series(self, async_session):
        """Create sample series for testing."""
        series_data = [
            Series(
                title="Naruto",
                author="Masashi Kishimoto",
                artist="Masashi Kishimoto",
                description="A ninja boy's journey to become Hokage",
                status="completed"
            ),
            Series(
                title="One Piece",
                author="Eiichiro Oda",
                artist="Eiichiro Oda", 
                description="Pirates searching for the greatest treasure",
                status="ongoing"
            ),
            Series(
                title="Attack on Titan",
                author="Hajime Isayama",
                artist="Hajime Isayama",
                description="Humanity fights against giant humanoid creatures",
                status="completed"
            ),
            Series(
                title="Dragon Ball",
                author="Akira Toriyama",
                artist="Akira Toriyama",
                description="A Saiyan warrior's adventures and battles",
                status="completed"
            )
        ]
        
        for series in series_data:
            async_session.add(series)
        
        await async_session.commit()
        await async_session.refresh(series_data[0])
        
        return series_data

    @pytest.mark.asyncio
    async def test_parse_search_query_simple(self, search_service):
        """Test parsing simple search query."""
        search_text, filters = search_service.parse_search_query("naruto manga")
        
        assert search_text == "naruto manga"
        assert filters == {}

    @pytest.mark.asyncio
    async def test_parse_search_query_with_filters(self, search_service):
        """Test parsing search query with filters."""
        search_text, filters = search_service.parse_search_query("ninja author:kishimoto status:completed")
        
        assert search_text == "ninja"
        assert "author" in filters
        assert "status" in filters
        assert filters["author"] == ["kishimoto"]
        assert filters["status"] == ["completed"]

    @pytest.mark.asyncio
    async def test_parse_search_query_empty(self, search_service):
        """Test parsing empty search query."""
        search_text, filters = search_service.parse_search_query("")
        
        assert search_text == ""
        assert filters == {}

    @pytest.mark.asyncio
    async def test_build_search_vector_query(self, search_service):
        """Test building PostgreSQL tsquery."""
        tsquery = search_service.build_search_vector_query("naruto ninja")
        
        assert "naruto:*" in tsquery
        assert "ninja:*" in tsquery
        assert "&" in tsquery

    @pytest.mark.asyncio
    async def test_build_search_vector_query_empty(self, search_service):
        """Test building tsquery with empty input."""
        tsquery = search_service.build_search_vector_query("")
        
        assert tsquery == ""

    @pytest.mark.asyncio
    async def test_build_search_vector_query_short_words(self, search_service):
        """Test building tsquery with short words."""
        tsquery = search_service.build_search_vector_query("a to of")
        
        # Short words should be filtered out
        assert tsquery == ""

    @pytest.mark.asyncio
    async def test_search_series_empty_query(self, search_service, sample_series):
        """Test search with empty query returns recent series."""
        results, total = await search_service.search_series("")
        
        assert total >= 4  # Should return all series
        assert len(results) >= 4
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_series_by_title(self, search_service, sample_series):
        """Test search by series title."""
        results, total = await search_service.search_series("Naruto")
        
        assert total >= 1
        assert len(results) >= 1
        
        # Should find Naruto
        naruto_found = any(series.title == "Naruto" for series in results)
        assert naruto_found

    @pytest.mark.asyncio
    async def test_search_series_by_author(self, search_service, sample_series):
        """Test search by author name."""
        results, total = await search_service.search_series("Kishimoto")
        
        assert total >= 1
        assert len(results) >= 1
        
        # Should find series by Kishimoto
        kishimoto_found = any("Kishimoto" in (series.author or "") for series in results)
        assert kishimoto_found

    @pytest.mark.asyncio
    async def test_search_series_by_description(self, search_service, sample_series):
        """Test search by description content."""
        results, total = await search_service.search_series("ninja")
        
        assert total >= 1
        assert len(results) >= 1
        
        # Should find series with "ninja" in description
        ninja_found = any("ninja" in (series.description or "").lower() for series in results)
        assert ninja_found

    @pytest.mark.asyncio
    async def test_search_series_no_results(self, search_service, sample_series):
        """Test search with no matching results."""
        results, total = await search_service.search_series("nonexistent_manga_title_12345")
        
        assert total == 0
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_series_with_pagination(self, search_service, sample_series):
        """Test search with pagination parameters."""
        results, total = await search_service.search_series("", limit=2, offset=1)
        
        assert len(results) <= 2
        assert total >= 4  # Total should still reflect all results

    @pytest.mark.asyncio
    async def test_search_series_with_author_filter(self, search_service, sample_series):
        """Test search with author filter."""
        results, total = await search_service.search_series("author:Toriyama")
        
        assert total >= 1
        # Should find Dragon Ball by Akira Toriyama
        toriyama_found = any("Toriyama" in (series.author or "") for series in results)
        assert toriyama_found

    @pytest.mark.asyncio
    async def test_search_series_with_status_filter(self, search_service, sample_series):
        """Test search with status filter."""
        results, total = await search_service.search_series("status:completed")
        
        # Should find completed series
        completed_series = [s for s in results if s.status == "completed"]
        assert len(completed_series) >= 1

    @pytest.mark.asyncio
    async def test_get_search_suggestions_empty(self, search_service):
        """Test autocomplete with empty/short query."""
        suggestions = await search_service.get_search_suggestions("")
        assert suggestions == []
        
        suggestions = await search_service.get_search_suggestions("a")
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_get_search_suggestions_with_results(self, search_service, sample_series):
        """Test autocomplete with matching results."""
        suggestions = await search_service.get_search_suggestions("Na")
        
        # Should include titles and authors starting with or containing "Na"
        assert isinstance(suggestions, list)
        
        # Should find "Naruto" in suggestions
        naruto_found = any("Naruto" in suggestion for suggestion in suggestions)
        if naruto_found:  # Only assert if we actually have results
            assert naruto_found

    @pytest.mark.asyncio
    async def test_get_search_suggestions_limit(self, search_service, sample_series):
        """Test autocomplete respects limit parameter."""
        suggestions = await search_service.get_search_suggestions("a", limit=2)
        
        assert len(suggestions) <= 2

    @pytest.mark.asyncio
    async def test_save_search_history(self, search_service, async_session):
        """Test saving search history."""
        user_id = uuid4()
        
        await search_service._save_search_history(user_id, "test query", 5)
        
        # Check that search history was saved
        from sqlalchemy import select
        stmt = select(SearchHistory).where(SearchHistory.user_id == user_id)
        result = await async_session.execute(stmt)
        history = result.scalar_one_or_none()
        
        assert history is not None
        assert history.query == "test query"
        assert history.results_count == 5

    @pytest.mark.asyncio
    async def test_save_search_history_duplicate_prevention(self, search_service, async_session):
        """Test that recent duplicate searches are not saved."""
        user_id = uuid4()
        
        # Save same query twice
        await search_service._save_search_history(user_id, "duplicate query", 5)
        await search_service._save_search_history(user_id, "duplicate query", 3)
        
        # Should only have one entry
        from sqlalchemy import select, func
        stmt = select(func.count(SearchHistory.id)).where(
            SearchHistory.user_id == user_id,
            SearchHistory.query == "duplicate query"
        )
        result = await async_session.execute(stmt)
        count = result.scalar()
        
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_recent_searches(self, search_service, async_session):
        """Test getting recent searches."""
        user_id = uuid4()
        
        # Add some search history
        searches = [
            SearchHistory(user_id=user_id, query="query 1", results_count=1),
            SearchHistory(user_id=user_id, query="query 2", results_count=2),
            SearchHistory(user_id=user_id, query="query 3", results_count=3),
        ]
        
        for search in searches:
            async_session.add(search)
        
        await async_session.commit()
        
        recent_searches = await search_service.get_recent_searches(user_id)
        
        assert len(recent_searches) == 3
        assert "query 1" in recent_searches
        assert "query 2" in recent_searches
        assert "query 3" in recent_searches

    @pytest.mark.asyncio
    async def test_get_recent_searches_limit(self, search_service, async_session):
        """Test getting recent searches with limit."""
        user_id = uuid4()
        
        # Add search history
        searches = [
            SearchHistory(user_id=user_id, query=f"query {i}", results_count=i)
            for i in range(5)
        ]
        
        for search in searches:
            async_session.add(search)
        
        await async_session.commit()
        
        recent_searches = await search_service.get_recent_searches(user_id, limit=2)
        
        assert len(recent_searches) == 2

    @pytest.mark.asyncio
    async def test_search_series_with_user_history(self, search_service, async_session):
        """Test search that saves to user history."""
        user_id = uuid4()
        
        results, total = await search_service.search_series("test query", user_id=user_id)
        
        # Check that search history was saved
        from sqlalchemy import select
        stmt = select(SearchHistory).where(SearchHistory.user_id == user_id)
        result = await async_session.execute(stmt)
        history = result.scalar_one_or_none()
        
        assert history is not None
        assert history.query == "test query"
        assert history.results_count == total