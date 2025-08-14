"""Tests for annotation API endpoints."""

from uuid import UUID

from httpx import AsyncClient


class TestAnnotationAPI:
    """Test annotation CRUD operations."""

    async def test_create_annotation(self, client: AsyncClient, sample_series_with_chapters):
        """Test creating a new annotation."""
        series, chapters = sample_series_with_chapters
        chapter = chapters[0]

        annotation_data = {
            "chapter_id": str(chapter.id),
            "content": "This is a test annotation",
            "page_number": 1,
            "annotation_type": "note",
            "position_x": 0.5,
            "position_y": 0.3,
            "color": "#ff0000"
        }

        response = await client.post("/api/annotations/", json=annotation_data)
        assert response.status_code == 201

        data = response.json()
        assert data["content"] == annotation_data["content"]
        assert data["page_number"] == annotation_data["page_number"]
        assert data["annotation_type"] == annotation_data["annotation_type"]
        assert data["position_x"] == annotation_data["position_x"]
        assert data["position_y"] == annotation_data["position_y"]
        assert data["color"] == annotation_data["color"]
        assert data["chapter_id"] == annotation_data["chapter_id"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_annotation_invalid_chapter(self, db_session):
        """Test creating annotation with invalid chapter ID."""
        annotation_data = {
            "chapter_id": str(UUID('00000000-0000-0000-0000-000000000000')),
            "content": "This is a test annotation",
            "annotation_type": "note"
        }

        response = client.post("/api/annotations/", json=annotation_data)
        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    def test_create_annotation_invalid_page_number(self, db_session, sample_series_with_chapters):
        """Test creating annotation with invalid page number."""
        series, chapters = sample_series_with_chapters
        chapter = chapters[0]

        annotation_data = {
            "chapter_id": str(chapter.id),
            "content": "This is a test annotation",
            "page_number": chapter.page_count + 1,  # Invalid page
            "annotation_type": "note"
        }

        response = client.post("/api/annotations/", json=annotation_data)
        assert response.status_code == 400
        assert "Page number must be between" in response.json()["detail"]

    def test_get_annotation(self, db_session, sample_annotation):
        """Test retrieving an annotation."""
        annotation = sample_annotation

        response = client.get(f"/api/annotations/{annotation.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(annotation.id)
        assert data["content"] == annotation.content
        assert data["annotation_type"] == annotation.annotation_type

    def test_get_annotation_with_chapter(self, db_session, sample_annotation):
        """Test retrieving an annotation with chapter information."""
        annotation = sample_annotation

        response = client.get(f"/api/annotations/{annotation.id}?include_chapter=true")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(annotation.id)
        assert "chapter" in data
        assert data["chapter"]["id"] == str(annotation.chapter_id)

    def test_get_annotation_not_found(self, db_session):
        """Test retrieving non-existent annotation."""
        response = client.get(f"/api/annotations/{UUID('00000000-0000-0000-0000-000000000000')}")
        assert response.status_code == 404

    def test_update_annotation(self, db_session, sample_annotation):
        """Test updating an annotation."""
        annotation = sample_annotation

        update_data = {
            "content": "Updated annotation content",
            "annotation_type": "bookmark",
            "color": "#00ff00"
        }

        response = client.put(f"/api/annotations/{annotation.id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["content"] == update_data["content"]
        assert data["annotation_type"] == update_data["annotation_type"]
        assert data["color"] == update_data["color"]

    def test_delete_annotation(self, db_session, sample_annotation):
        """Test deleting an annotation."""
        annotation = sample_annotation

        response = client.delete(f"/api/annotations/{annotation.id}")
        assert response.status_code == 204

        # Verify annotation is deleted
        response = client.get(f"/api/annotations/{annotation.id}")
        assert response.status_code == 404

    def test_list_annotations(self, db_session, sample_annotations):
        """Test listing annotations."""
        annotations = sample_annotations

        response = client.get("/api/annotations/")
        assert response.status_code == 200

        data = response.json()
        assert "annotations" in data
        assert "total" in data
        assert len(data["annotations"]) == len(annotations)

    def test_list_annotations_filtered_by_chapter(self, db_session, sample_annotations):
        """Test listing annotations filtered by chapter."""
        annotations = sample_annotations
        chapter_id = annotations[0].chapter_id

        response = client.get(f"/api/annotations/?chapter_id={chapter_id}")
        assert response.status_code == 200

        data = response.json()
        chapter_annotations = [a for a in annotations if a.chapter_id == chapter_id]
        assert len(data["annotations"]) == len(chapter_annotations)
        assert data["chapter_id"] == str(chapter_id)

    def test_list_annotations_filtered_by_type(self, db_session, sample_annotations):
        """Test listing annotations filtered by type."""
        annotations = sample_annotations

        response = client.get("/api/annotations/?annotation_type=note")
        assert response.status_code == 200

        data = response.json()
        note_annotations = [a for a in annotations if a.annotation_type == "note"]
        assert len(data["annotations"]) == len(note_annotations)
        assert data["annotation_type"] == "note"

    def test_get_chapter_annotations(self, db_session, sample_annotations):
        """Test getting all annotations for a chapter."""
        annotations = sample_annotations
        chapter_id = annotations[0].chapter_id

        response = client.get(f"/api/annotations/chapters/{chapter_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["chapter_id"] == str(chapter_id)
        assert "chapter_title" in data
        assert "total_pages" in data
        assert "annotations" in data
        assert "annotations_by_page" in data

        chapter_annotations = [a for a in annotations if a.chapter_id == chapter_id]
        assert len(data["annotations"]) == len(chapter_annotations)

    def test_get_page_annotations(self, db_session, sample_annotations):
        """Test getting annotations for a specific page."""
        annotations = sample_annotations
        chapter_id = annotations[0].chapter_id
        page_number = 1

        response = client.get(f"/api/annotations/chapters/{chapter_id}/pages/{page_number}")
        assert response.status_code == 200

        data = response.json()
        page_annotations = [
            a for a in annotations
            if a.chapter_id == chapter_id and a.page_number == page_number
        ]
        assert len(data) == len(page_annotations)

    def test_create_page_annotation(self, db_session, sample_series_with_chapters):
        """Test creating annotation for specific page."""
        series, chapters = sample_series_with_chapters
        chapter = chapters[0]
        page_number = 1

        annotation_data = {
            "chapter_id": str(chapter.id),
            "content": "Page-specific annotation",
            "annotation_type": "highlight"
        }

        response = client.post(
            f"/api/annotations/chapters/{chapter.id}/pages/{page_number}",
            json=annotation_data
        )
        assert response.status_code == 201

        data = response.json()
        assert data["content"] == annotation_data["content"]
        assert data["page_number"] == page_number
        assert data["chapter_id"] == str(chapter.id)

    def test_delete_chapter_annotations(self, db_session, sample_annotations):
        """Test deleting all annotations for a chapter."""
        annotations = sample_annotations
        chapter_id = annotations[0].chapter_id

        response = client.delete(f"/api/annotations/chapters/{chapter_id}")
        assert response.status_code == 204

        # Verify annotations are deleted
        response = client.get(f"/api/annotations/chapters/{chapter_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["annotations"]) == 0
