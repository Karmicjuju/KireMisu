import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.chapter import Chapter
from app.services.chapter import ChapterService
from app.schemas.chapter import ChapterResponse, ChapterListResponse


@pytest.fixture
def test_client():
    """Test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_chapter_service():
    """Mock ChapterService."""
    return AsyncMock(spec=ChapterService)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = "user123"
    user.email = "test@example.com"
    user.username = "testuser"
    return user


@pytest.fixture
def sample_chapter():
    """Sample chapter for testing."""
    return Chapter(
        id=1,
        series_id=1,
        number=Decimal("1.0"),
        title="Chapter 1: The Beginning",
        file_path="series1/chapter1.zip",
        volume=Decimal("1.0"),
        description="The first chapter",
        page_count=20,
        file_size=1024000,
        read_status=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def chapter_list_response(sample_chapter):
    """Sample chapter list response."""
    return ChapterListResponse(
        items=[ChapterResponse.model_validate(sample_chapter)],
        total=1,
        page=1,
        size=20,
        pages=1,
    )


class TestChapterEndpoints:
    """Test chapter API endpoints."""

    def test_get_chapters_success(
        self,
        test_client,
        mock_chapter_service,
        chapter_list_response,
        mock_user,
    ):
        """Test successful chapters retrieval."""
        # Mock dependencies
        with (
            app.dependency_overrides.copy() as overrides,
        ):
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user  # Mock auth
            
            mock_chapter_service.get_chapters_paginated.return_value = chapter_list_response
            
            response = test_client.get("/api/v1/chapters/")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == 1
            assert data["items"][0]["title"] == "Chapter 1: The Beginning"

    def test_get_chapters_with_filters(
        self,
        test_client,
        mock_chapter_service,
        chapter_list_response,
        mock_user,
    ):
        """Test chapters retrieval with filters."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.get_chapters_paginated.return_value = chapter_list_response
            
            response = test_client.get(
                "/api/v1/chapters/?series_id=1&volume=1.0&read_status=false&page=1&size=10"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            # Verify service was called with correct parameters
            mock_chapter_service.get_chapters_paginated.assert_called_once_with(
                page=1,
                size=10,
                series_id=1,
                volume=Decimal("1.0"),
                read_status=False,
            )

    def test_create_chapter_success(
        self,
        test_client,
        mock_chapter_service,
        sample_chapter,
        mock_user,
    ):
        """Test successful chapter creation."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.create_chapter.return_value = sample_chapter
            
            chapter_data = {
                "series_id": 1,
                "number": 1.0,
                "title": "Chapter 1: The Beginning",
                "file_path": "series1/chapter1.zip",
                "volume": 1.0,
                "description": "The first chapter",
                "page_count": 20,
                "file_size": 1024000,
            }
            
            response = test_client.post("/api/v1/chapters/", json=chapter_data)
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == 1
            assert data["title"] == "Chapter 1: The Beginning"
            
            # Verify service was called with user ID
            mock_chapter_service.create_chapter.assert_called_once()
            call_args = mock_chapter_service.create_chapter.call_args
            assert call_args[1]["user_id"] == "user123"

    def test_create_chapter_validation_error(self, test_client, mock_user):
        """Test chapter creation with validation error."""
        with app.dependency_overrides.copy() as overrides:
            overrides[lambda: None] = lambda: mock_user
            
            # Invalid data - missing required fields
            chapter_data = {
                "title": "Chapter 1",
                # Missing series_id, number, file_path
            }
            
            response = test_client.post("/api/v1/chapters/", json=chapter_data)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_chapter_by_id_success(
        self,
        test_client,
        mock_chapter_service,
        sample_chapter,
        mock_user,
    ):
        """Test successful chapter retrieval by ID."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.get_chapter_by_id.return_value = sample_chapter
            
            response = test_client.get("/api/v1/chapters/1")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1
            assert data["title"] == "Chapter 1: The Beginning"

    def test_get_chapter_by_id_not_found(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test chapter retrieval when chapter not found."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.get_chapter_by_id.return_value = None
            
            response = test_client.get("/api/v1/chapters/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_chapter_success(
        self,
        test_client,
        mock_chapter_service,
        sample_chapter,
        mock_user,
    ):
        """Test successful chapter update."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            updated_chapter = Chapter(**sample_chapter.__dict__)
            updated_chapter.title = "Updated Chapter Title"
            mock_chapter_service.update_chapter.return_value = updated_chapter
            
            update_data = {
                "title": "Updated Chapter Title",
                "description": "Updated description"
            }
            
            response = test_client.patch("/api/v1/chapters/1", json=update_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["title"] == "Updated Chapter Title"
            
            # Verify service was called with correct parameters
            mock_chapter_service.update_chapter.assert_called_once()
            call_args = mock_chapter_service.update_chapter.call_args
            assert call_args[1]["chapter_id"] == 1
            assert call_args[1]["user_id"] == "user123"
            assert call_args[1]["preview_mode"] is False

    def test_update_chapter_preview_mode(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test chapter update in preview mode."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            preview_result = {
                "preview": {
                    "changes": {
                        "title": {
                            "old": "Chapter 1: The Beginning",
                            "new": "Updated Title"
                        }
                    },
                    "additions": {},
                    "removals": {}
                },
                "current": sample_chapter
            }
            mock_chapter_service.update_chapter.return_value = preview_result
            
            update_data = {"title": "Updated Title"}
            
            response = test_client.patch(
                "/api/v1/chapters/1?preview=true",
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "preview" in data
            assert "changes" in data["preview"]
            
            # Verify preview mode was enabled
            call_args = mock_chapter_service.update_chapter.call_args
            assert call_args[1]["preview_mode"] is True

    def test_update_chapter_not_found(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test updating non-existent chapter."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.update_chapter.return_value = None
            
            update_data = {"title": "Updated Title"}
            
            response = test_client.patch("/api/v1/chapters/999", json=update_data)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_update_chapters_success(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test successful bulk chapter update."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            # Mock successful bulk update
            updated_chapters = [
                Chapter(id=1, series_id=1, number=Decimal("1"), title="Ch1", file_path="ch1.zip", read_status=True),
                Chapter(id=2, series_id=1, number=Decimal("2"), title="Ch2", file_path="ch2.zip", read_status=True),
            ]
            mock_chapter_service.bulk_update_chapters.return_value = updated_chapters
            
            bulk_data = {
                "chapter_ids": [1, 2],
                "updates": {"read_status": True}
            }
            
            response = test_client.patch("/api/v1/chapters/bulk", json=bulk_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert all(chapter["read_status"] is True for chapter in data)

    def test_delete_chapter_success(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test successful chapter deletion."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.delete_chapter.return_value = True
            
            response = test_client.delete("/api/v1/chapters/1")
            
            assert response.status_code == status.HTTP_204_NO_CONTENT
            
            # Verify service was called with correct parameters
            mock_chapter_service.delete_chapter.assert_called_once_with(
                chapter_id=1,
                user_id="user123",
            )

    def test_delete_chapter_not_found(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test deleting non-existent chapter."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.delete_chapter.return_value = False
            
            response = test_client.delete("/api/v1/chapters/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_chapter_history(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test getting chapter history."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_history = [
                MagicMock(id=1, action="create", created_at=datetime.now()),
                MagicMock(id=2, action="update", created_at=datetime.now()),
            ]
            mock_chapter_service.get_chapter_history.return_value = mock_history
            
            response = test_client.get("/api/v1/chapters/1/history")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2

    def test_restore_chapter_from_history(
        self,
        test_client,
        mock_chapter_service,
        sample_chapter,
        mock_user,
    ):
        """Test restoring chapter from history."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.restore_chapter_from_history.return_value = sample_chapter
            
            response = test_client.post("/api/v1/chapters/1/restore/10")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1
            
            # Verify service was called with correct parameters
            mock_chapter_service.restore_chapter_from_history.assert_called_once_with(
                chapter_id=1,
                history_id=10,
                user_id="user123",
            )

    def test_restore_chapter_not_found(
        self,
        test_client,
        mock_chapter_service,
        mock_user,
    ):
        """Test restoring from non-existent chapter or history."""
        with app.dependency_overrides.copy() as overrides:
            overrides[ChapterService] = lambda: mock_chapter_service
            overrides[lambda: None] = lambda: mock_user
            
            mock_chapter_service.restore_chapter_from_history.return_value = None
            
            response = test_client.post("/api/v1/chapters/999/restore/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND