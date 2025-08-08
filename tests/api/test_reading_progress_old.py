"""
Tests for reading progress API endpoints.

This module tests the R-2 reading progress API functionality including:
- Chapter progress updates and mark-read toggles  
- Series progress statistics and bulk operations
- User reading statistics and analytics
- Error handling and validation
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from uuid import uuid4

from kiremisu.database.models import Chapter, Series


@pytest.fixture
async def sample_series(db_session):
    """Create a sample series for testing."""
    series = Series(
        id=uuid4(),
        title_primary="Test Manga Series",
        author="Test Author",
        genres=["Action", "Adventure"],
        total_chapters=3,
        read_chapters=0,
    )
    db_session.add(series)
    await db_session.commit()
    return series


@pytest.fixture
async def sample_chapters(db_session, sample_series):
    """Create sample chapters for testing."""
    chapters = []
    for i in range(3):
        chapter = Chapter(
            id=uuid4(),
            series_id=sample_series.id,
            chapter_number=float(i + 1),
            file_path=f"/test/chapter_{i+1}.cbz",
            page_count=20,
            file_size=1024000,
        )
        chapters.append(chapter)
        db_session.add(chapter)
    
    await db_session.commit()
    return chapters


class TestReadingProgressAPI:
    """Test cases for reading progress API endpoints."""

    async def test_update_chapter_progress_success(self, client: AsyncClient, sample_chapters):
        """Test successful chapter progress update."""
        chapter = sample_chapters[0]
        
        response = await client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 5, "is_complete": None}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chapter_id"] == str(chapter.id)
        assert data["current_page"] == 5
        assert data["progress_percentage"] == 30.0  # (5+1)/20 * 100
        assert not data["is_read"]

    def test_update_chapter_progress_completion(self, client: TestClient, sample_chapters):
        """Test chapter progress update with auto-completion."""
        chapter = sample_chapters[0]
        
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 19, "is_complete": None}  # Last page
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"]
        assert data["progress_percentage"] == 100.0
        assert data["read_at"] is not None

    def test_update_chapter_progress_explicit_completion(self, client: TestClient, sample_chapters):
        """Test explicit chapter completion."""
        chapter = sample_chapters[0]
        
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 10, "is_complete": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"]
        assert data["current_page"] == 10
        assert data["read_at"] is not None

    def test_update_chapter_progress_invalid_chapter(self, client: TestClient):
        """Test progress update with invalid chapter ID."""
        invalid_id = uuid4()
        
        response = client.put(
            f"/reading-progress/chapters/{invalid_id}/progress",
            json={"current_page": 5, "is_complete": None}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_chapter_progress_invalid_page(self, client: TestClient, sample_chapters):
        """Test progress update with invalid page number."""
        chapter = sample_chapters[0]
        
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": -1, "is_complete": None}  # Negative page
        )
        
        assert response.status_code == 422  # Validation error

    def test_toggle_chapter_read_status(self, client: TestClient, sample_chapters):
        """Test toggling chapter read status."""
        chapter = sample_chapters[0]
        
        # Mark as read
        response = client.post(f"/reading-progress/chapters/{chapter.id}/mark-read")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"]
        assert data["read_at"] is not None
        
        # Toggle back to unread
        response = client.post(f"/reading-progress/chapters/{chapter.id}/mark-read")
        
        assert response.status_code == 200
        data = response.json()
        assert not data["is_read"]

    def test_mark_chapter_unread(self, client: TestClient, sample_chapters):
        """Test marking chapter as unread."""
        chapter = sample_chapters[0]
        
        # First mark as read
        client.post(f"/reading-progress/chapters/{chapter.id}/mark-read")
        
        # Then specifically mark as unread
        response = client.post(f"/reading-progress/chapters/{chapter.id}/mark-unread")
        
        assert response.status_code == 200
        data = response.json()
        assert not data["is_read"]
        assert data["read_at"] is None

    def test_mark_chapter_unread_already_unread(self, client: TestClient, sample_chapters):
        """Test marking already unread chapter as unread."""
        chapter = sample_chapters[0]
        
        response = client.post(f"/reading-progress/chapters/{chapter.id}/mark-unread")
        
        assert response.status_code == 200
        data = response.json()
        assert not data["is_read"]

    def test_get_chapter_progress(self, client: TestClient, sample_chapters):
        """Test getting current chapter progress."""
        chapter = sample_chapters[0]
        
        # First update progress
        client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 8, "is_complete": None}
        )
        
        # Then get progress
        response = client.get(f"/reading-progress/chapters/{chapter.id}/progress")
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_page"] == 8
        assert data["progress_percentage"] == 45.0  # (8+1)/20 * 100

    def test_get_chapter_progress_not_found(self, client: TestClient):
        """Test getting progress for non-existent chapter."""
        invalid_id = uuid4()
        
        response = client.get(f"/reading-progress/chapters/{invalid_id}/progress")
        
        assert response.status_code == 404

    def test_get_series_progress(self, client: TestClient, sample_series, sample_chapters):
        """Test getting series reading progress."""
        # Mark first chapter as read
        client.post(f"/reading-progress/chapters/{sample_chapters[0].id}/mark-read")
        
        response = client.get(f"/reading-progress/series/{sample_series.id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["series_id"] == str(sample_series.id)
        assert data["total_chapters"] == 3
        assert data["read_chapters"] == 1
        assert data["progress_percentage"] == pytest.approx(33.33, abs=0.1)
        assert len(data["recent_chapters"]) == 1

    def test_get_series_progress_not_found(self, client: TestClient):
        """Test getting progress for non-existent series."""
        invalid_id = uuid4()
        
        response = client.get(f"/reading-progress/series/{invalid_id}/stats")
        
        assert response.status_code == 404

    def test_mark_series_read(self, client: TestClient, sample_series):
        """Test marking entire series as read."""
        response = client.post(f"/reading-progress/series/{sample_series.id}/mark-read")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["chapters_updated"] == 3
        
        # Verify series progress
        progress_response = client.get(f"/reading-progress/series/{sample_series.id}/stats")
        progress_data = progress_response.json()
        assert progress_data["read_chapters"] == 3
        assert progress_data["progress_percentage"] == 100.0

    def test_mark_series_unread(self, client: TestClient, sample_series):
        """Test marking entire series as unread."""
        # First mark as read
        client.post(f"/reading-progress/series/{sample_series.id}/mark-read")
        
        # Then mark as unread
        response = client.post(f"/reading-progress/series/{sample_series.id}/mark-unread")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["chapters_updated"] == 3
        
        # Verify series progress
        progress_response = client.get(f"/reading-progress/series/{sample_series.id}/stats")
        progress_data = progress_response.json()
        assert progress_data["read_chapters"] == 0
        assert progress_data["progress_percentage"] == 0.0

    def test_mark_series_not_found(self, client: TestClient):
        """Test marking non-existent series."""
        invalid_id = uuid4()
        
        response = client.post(f"/reading-progress/series/{invalid_id}/mark-read")
        assert response.status_code == 404
        
        response = client.post(f"/reading-progress/series/{invalid_id}/mark-unread")
        assert response.status_code == 404

    def test_get_user_reading_stats(self, client: TestClient, sample_chapters):
        """Test getting comprehensive user reading statistics."""
        # Create some reading activity
        client.post(f"/reading-progress/chapters/{sample_chapters[0].id}/mark-read")
        client.put(
            f"/reading-progress/chapters/{sample_chapters[1].id}/progress",
            json={"current_page": 5, "is_complete": None}
        )
        
        response = client.get("/reading-progress/user/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_series"] >= 1
        assert data["total_chapters"] >= 3
        assert data["read_chapters"] >= 1
        assert data["in_progress_chapters"] >= 1
        assert data["overall_progress_percentage"] >= 0
        assert data["reading_streak_days"] >= 0
        assert isinstance(data["favorite_genres"], list)
        assert isinstance(data["recent_activity"], list)

    def test_api_validation_errors(self, client: TestClient, sample_chapters):
        """Test API validation for invalid requests."""
        chapter = sample_chapters[0]
        
        # Invalid current_page (string instead of int)
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": "invalid", "is_complete": None}
        )
        assert response.status_code == 422
        
        # Missing required field
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"is_complete": None}
        )
        assert response.status_code == 422
        
        # Invalid UUID format
        response = client.put(
            "/reading-progress/chapters/invalid-uuid/progress",
            json={"current_page": 5, "is_complete": None}
        )
        assert response.status_code == 422

    def test_progress_tracking_integration(self, client: TestClient, sample_chapters):
        """Test integration between different progress tracking endpoints."""
        chapter = sample_chapters[0]
        
        # 1. Start reading - update progress
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 5, "is_complete": None}
        )
        assert response.status_code == 200
        first_update = response.json()
        assert first_update["started_at"] is not None
        
        # 2. Continue reading - update progress again
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 10, "is_complete": None}
        )
        assert response.status_code == 200
        second_update = response.json()
        assert second_update["current_page"] == 10
        assert second_update["started_at"] == first_update["started_at"]  # Should not change
        
        # 3. Finish reading - auto-complete
        response = client.put(
            f"/reading-progress/chapters/{chapter.id}/progress",
            json={"current_page": 19, "is_complete": None}
        )
        assert response.status_code == 200
        completion = response.json()
        assert completion["is_read"]
        assert completion["read_at"] is not None
        
        # 4. Verify with get endpoint
        response = client.get(f"/reading-progress/chapters/{chapter.id}/progress")
        assert response.status_code == 200
        current_progress = response.json()
        assert current_progress["is_read"]
        assert current_progress["current_page"] == 19

    def test_series_statistics_updates(self, client: TestClient, sample_series, sample_chapters):
        """Test that series statistics are properly updated when chapters change."""
        # Initially no read chapters
        response = client.get(f"/reading-progress/series/{sample_series.id}/stats")
        initial_stats = response.json()
        assert initial_stats["read_chapters"] == 0
        
        # Mark first chapter as read
        client.post(f"/reading-progress/chapters/{sample_chapters[0].id}/mark-read")
        
        response = client.get(f"/reading-progress/series/{sample_series.id}/stats")
        updated_stats = response.json()
        assert updated_stats["read_chapters"] == 1
        assert len(updated_stats["recent_chapters"]) == 1
        
        # Mark second chapter as read
        client.post(f"/reading-progress/chapters/{sample_chapters[1].id}/mark-read")
        
        response = client.get(f"/reading-progress/series/{sample_series.id}/stats")
        final_stats = response.json()
        assert final_stats["read_chapters"] == 2
        assert len(final_stats["recent_chapters"]) == 2