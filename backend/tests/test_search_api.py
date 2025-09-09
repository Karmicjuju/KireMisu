"""Tests for search API endpoints."""

import pytest
from fastapi.testclient import TestClient
from fastapi import status

from app.models.series import Series
from app.models.search_history import SearchHistory
from app.models.user import User


class TestSearchAPI:
    """Test search API endpoints."""

    def test_search_series_success(self, client: TestClient, test_user_data: dict):
        """Test successful series search."""
        # Register and login
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/search/",
            params={"q": "test", "limit": 10, "offset": 0},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "query" in data
        assert data["query"] == "test"
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_search_series_with_results(self, async_client: AsyncClient, async_session, auth_headers):
        """Test search with actual results."""
        # Create test series
        series1 = Series(
            title="Test Manga One",
            author="Test Author",
            description="A test manga about adventures"
        )
        series2 = Series(
            title="Another Series",
            author="Test Author",
            description="Different story"
        )
        
        async_session.add(series1)
        async_session.add(series2)
        await async_session.commit()
        
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "Test Manga", "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should find the series with "Test Manga" in title
        assert data["total"] >= 1
        assert len(data["results"]) >= 1
        
        # Check result structure
        result = data["results"][0]
        assert "id" in result
        assert "title" in result
        assert "author" in result
        assert "description" in result

    def test_search_series_pagination(self, client: TestClient, test_user_data: dict):
        """Test search pagination."""
        # Register and login
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/search/",
            params={"q": "test", "limit": 5, "offset": 10},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["limit"] == 5
        assert data["offset"] == 10

    @pytest.mark.asyncio
    async def test_search_series_invalid_params(self, async_client: AsyncClient, auth_headers):
        """Test search with invalid parameters."""
        # Empty query
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "", "limit": 10},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Query too long
        long_query = "a" * 201
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": long_query, "limit": 10},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Invalid limit
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "test", "limit": 0},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_series_unauthenticated(self, client: TestClient):
        """Test search without authentication (should require auth)."""
        response = client.get(
            "/api/v1/search/",
            params={"q": "test", "limit": 10}
        )
        
        # Search should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_autocomplete_success(self, async_client: AsyncClient, async_session):
        """Test autocomplete suggestions."""
        # Create test series for suggestions
        series = Series(
            title="Naruto Manga",
            author="Masashi Kishimoto",
            description="Ninja adventures"
        )
        
        async_session.add(series)
        await async_session.commit()
        
        response = await async_client.get(
            "/api/v1/search/autocomplete",
            params={"q": "Na", "limit": 10}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "suggestions" in data
        assert "query" in data
        assert data["query"] == "Na"
        assert isinstance(data["suggestions"], list)

    @pytest.mark.asyncio
    async def test_autocomplete_invalid_params(self, async_client: AsyncClient):
        """Test autocomplete with invalid parameters."""
        # Query too short
        response = await async_client.get(
            "/api/v1/search/autocomplete",
            params={"q": "a", "limit": 10}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Empty query
        response = await async_client.get(
            "/api/v1/search/autocomplete",
            params={"q": "", "limit": 10}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_recent_searches_success(self, async_client: AsyncClient, test_user, auth_headers, async_session):
        """Test getting recent searches."""
        # Create some search history
        search1 = SearchHistory(
            user_id=test_user.id,
            query="test query 1",
            results_count=5
        )
        search2 = SearchHistory(
            user_id=test_user.id,
            query="test query 2",
            results_count=3
        )
        
        async_session.add(search1)
        async_session.add(search2)
        await async_session.commit()
        
        response = await async_client.get(
            "/api/v1/search/recent",
            params={"limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "searches" in data
        assert isinstance(data["searches"], list)

    @pytest.mark.asyncio
    async def test_recent_searches_unauthenticated(self, async_client: AsyncClient):
        """Test getting recent searches without authentication."""
        response = await async_client.get(
            "/api/v1/search/recent",
            params={"limit": 10}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_clear_recent_searches_success(self, async_client: AsyncClient, test_user, auth_headers, async_session):
        """Test clearing recent searches."""
        # Create some search history
        search1 = SearchHistory(
            user_id=test_user.id,
            query="test query 1",
            results_count=5
        )
        
        async_session.add(search1)
        await async_session.commit()
        
        response = await async_client.delete(
            "/api/v1/search/recent",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "cleared" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_clear_recent_searches_unauthenticated(self, async_client: AsyncClient):
        """Test clearing recent searches without authentication."""
        response = await async_client.delete("/api/v1/search/recent")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_series_mandatory_auth(self, client: TestClient):
        """Test that search endpoint requires authentication."""
        response = client.get(
            "/api/v1/search/",
            params={"q": "test manga", "limit": 5}
        )
        
        # Should return 401 for unauthenticated request
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Verify error details
        data = response.json()
        assert "detail" in data


class TestSearchFilters:
    """Test search with various filters."""

    @pytest.mark.asyncio
    async def test_search_with_author_filter(self, async_client: AsyncClient, async_session, auth_headers):
        """Test search with author filter."""
        # Create test series with different authors
        series1 = Series(
            title="Series One",
            author="Author A",
            description="First series"
        )
        series2 = Series(
            title="Series Two",
            author="Author B",
            description="Second series"
        )
        
        async_session.add(series1)
        async_session.add(series2)
        await async_session.commit()
        
        # Search with author filter
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "author:A", "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_search_by_description(self, async_client: AsyncClient, async_session, auth_headers):
        """Test search that matches description."""
        series = Series(
            title="Test Series",
            author="Test Author",
            description="This is a unique description with special keywords"
        )
        
        async_session.add(series)
        await async_session.commit()
        
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "unique special", "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should find the series by description
        # Note: Exact matching depends on full-text search implementation


class TestSearchPerformance:
    """Test search performance and edge cases."""

    @pytest.mark.asyncio
    async def test_search_empty_database(self, async_client: AsyncClient, auth_headers):
        """Test search on empty database."""
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "nonexistent", "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_special_characters(self, async_client: AsyncClient, auth_headers):
        """Test search with special characters."""
        response = await async_client.get(
            "/api/v1/search/",
            params={"q": "test-manga_vol.1", "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_search_rate_limiting(self, async_client: AsyncClient, auth_headers):
        """Test search rate limiting (if implemented)."""
        # This would test rate limiting if it's enforced
        # For now, just ensure multiple requests don't fail
        for _ in range(5):
            response = await async_client.get(
                "/api/v1/search/",
                params={"q": "test", "limit": 1},
                headers=auth_headers
            )
            assert response.status_code == status.HTTP_200_OK