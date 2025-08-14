"""Tests for tag API endpoints."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestTagCRUD:
    """Test tag CRUD operations."""

    async def test_create_tag(self, client: AsyncClient):
        """Test creating a new tag."""
        tag_data = {
            "name": "action",
            "description": "Action manga series",
            "color": "#FF0000"
        }

        response = await client.post("/api/tags/", json=tag_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "action"
        assert data["description"] == "Action manga series"
        assert data["color"] == "#FF0000"
        assert data["usage_count"] == 0
        assert "id" in data
        assert "created_at" in data

    async def test_create_duplicate_tag_fails(self, client: AsyncClient):
        """Test that creating a duplicate tag fails."""
        tag_data = {"name": "duplicate"}

        # Create first tag
        response1 = await client.post("/api/tags/", json=tag_data)
        assert response1.status_code == 200

        # Try to create duplicate
        response2 = await client.post("/api/tags/", json=tag_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]

    async def test_get_tags_list(self, client: AsyncClient):
        """Test getting list of tags."""
        # Create some test tags
        for i in range(3):
            tag_data = {"name": f"test-tag-{i}"}
            await client.post("/api/tags/", json=tag_data)

        response = await client.get("/api/tags/")
        assert response.status_code == 200

        data = response.json()
        assert "tags" in data
        assert "total" in data
        assert len(data["tags"]) >= 3

    async def test_get_tags_with_search(self, client: AsyncClient):
        """Test searching tags."""
        # Create test tags
        await client.post("/api/tags/", json={"name": "action-adventure"})
        await client.post("/api/tags/", json={"name": "romance"})

        response = await client.get("/api/tags/?search=action")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "action-adventure"

    async def test_get_tags_with_sorting(self, client: AsyncClient):
        """Test tag sorting options."""
        # Create tags with different names
        await client.post("/api/tags/", json={"name": "zzz-last"})
        await client.post("/api/tags/", json={"name": "aaa-first"})

        # Test name sorting
        response = await client.get("/api/tags/?sort_by=name")
        assert response.status_code == 200

        data = response.json()
        tag_names = [tag["name"] for tag in data["tags"]]
        assert tag_names == sorted(tag_names)

    async def test_get_single_tag(self, client: AsyncClient):
        """Test getting a single tag by ID."""
        # Create a tag
        create_response = await client.post("/api/tags/", json={"name": "single-tag"})
        tag_id = create_response.json()["id"]

        # Get the tag
        response = await client.get(f"/api/tags/{tag_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == "single-tag"

    async def test_get_nonexistent_tag_fails(self, client: AsyncClient):
        """Test that getting a nonexistent tag returns 404."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/tags/{fake_id}")
        assert response.status_code == 404

    async def test_update_tag(self, client: AsyncClient):
        """Test updating a tag."""
        # Create a tag
        create_response = await client.post("/api/tags/", json={
            "name": "original-name",
            "description": "Original description"
        })
        tag_id = create_response.json()["id"]

        # Update the tag
        update_data = {
            "name": "updated-name",
            "description": "Updated description",
            "color": "#00FF00"
        }

        response = await client.put(f"/api/tags/{tag_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "updated-name"
        assert data["description"] == "Updated description"
        assert data["color"] == "#00FF00"

    async def test_update_tag_name_conflict_fails(self, client: AsyncClient):
        """Test that updating a tag name to an existing name fails."""
        # Create two tags
        await client.post("/api/tags/", json={"name": "existing-tag"})
        create_response = await client.post("/api/tags/", json={"name": "another-tag"})
        tag_id = create_response.json()["id"]

        # Try to update second tag to have the same name as first
        response = await client.put(f"/api/tags/{tag_id}", json={"name": "existing-tag"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_delete_tag(self, client: AsyncClient):
        """Test deleting a tag."""
        # Create a tag
        create_response = await client.post("/api/tags/", json={"name": "to-delete"})
        tag_id = create_response.json()["id"]

        # Delete the tag
        response = await client.delete(f"/api/tags/{tag_id}")
        assert response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/api/tags/{tag_id}")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_tag_fails(self, client: AsyncClient):
        """Test that deleting a nonexistent tag returns 404."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/tags/{fake_id}")
        assert response.status_code == 404


class TestSeriesTagAssignment:
    """Test series tag assignment operations."""

    async def test_assign_tags_to_series(self, client: AsyncClient, test_series):
        """Test assigning tags to a series."""
        # Create test tags
        tag1_response = await client.post("/api/tags/", json={"name": "tag1"})
        tag2_response = await client.post("/api/tags/", json={"name": "tag2"})

        tag1_id = tag1_response.json()["id"]
        tag2_id = tag2_response.json()["id"]

        # Assign tags to series
        assignment_data = {"tag_ids": [tag1_id, tag2_id]}
        response = await client.put(f"/api/tags/series/{test_series.id}", json=assignment_data)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        tag_names = {tag["name"] for tag in data}
        assert tag_names == {"tag1", "tag2"}

    async def test_get_series_tags(self, client: AsyncClient, test_series):
        """Test getting tags assigned to a series."""
        # Create and assign a tag
        tag_response = await client.post("/api/tags/", json={"name": "series-tag"})
        tag_id = tag_response.json()["id"]

        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag_id]})

        # Get series tags
        response = await client.get(f"/api/tags/series/{test_series.id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "series-tag"

    async def test_add_tags_to_series(self, client: AsyncClient, test_series):
        """Test adding tags to a series (keeping existing)."""
        # Create initial tags and assign one
        tag1_response = await client.post("/api/tags/", json={"name": "existing-tag"})
        tag2_response = await client.post("/api/tags/", json={"name": "new-tag"})

        tag1_id = tag1_response.json()["id"]
        tag2_id = tag2_response.json()["id"]

        # Assign first tag
        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag1_id]})

        # Add second tag (should keep first)
        response = await client.post(f"/api/tags/series/{test_series.id}/add", json={"tag_ids": [tag2_id]})
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        tag_names = {tag["name"] for tag in data}
        assert tag_names == {"existing-tag", "new-tag"}

    async def test_remove_tags_from_series(self, client: AsyncClient, test_series):
        """Test removing specific tags from a series."""
        # Create and assign tags
        tag1_response = await client.post("/api/tags/", json={"name": "keep-tag"})
        tag2_response = await client.post("/api/tags/", json={"name": "remove-tag"})

        tag1_id = tag1_response.json()["id"]
        tag2_id = tag2_response.json()["id"]

        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag1_id, tag2_id]})

        # Remove one tag
        response = await client.delete(f"/api/tags/series/{test_series.id}/remove", json={"tag_ids": [tag2_id]})
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "keep-tag"

    async def test_assign_nonexistent_tags_fails(self, client: AsyncClient, test_series):
        """Test that assigning nonexistent tags fails."""
        fake_id = str(uuid4())
        assignment_data = {"tag_ids": [fake_id]}

        response = await client.put(f"/api/tags/series/{test_series.id}", json=assignment_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    async def test_assign_tags_to_nonexistent_series_fails(self, client: AsyncClient):
        """Test that assigning tags to nonexistent series fails."""
        fake_series_id = str(uuid4())

        # Create a tag
        tag_response = await client.post("/api/tags/", json={"name": "test-tag"})
        tag_id = tag_response.json()["id"]

        assignment_data = {"tag_ids": [tag_id]}
        response = await client.put(f"/api/tags/series/{fake_series_id}", json=assignment_data)
        assert response.status_code == 404

    async def test_tag_usage_count_updates(self, client: AsyncClient, test_series, db: AsyncSession):
        """Test that tag usage counts update correctly."""
        # Create a tag
        tag_response = await client.post("/api/tags/", json={"name": "usage-test"})
        tag_data = tag_response.json()
        tag_id = tag_data["id"]

        # Initial usage should be 0
        assert tag_data["usage_count"] == 0

        # Assign to series
        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag_id]})

        # Check usage count increased
        get_response = await client.get(f"/api/tags/{tag_id}")
        updated_tag = get_response.json()
        assert updated_tag["usage_count"] == 1

        # Remove from series
        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": []})

        # Check usage count decreased
        final_response = await client.get(f"/api/tags/{tag_id}")
        final_tag = final_response.json()
        assert final_tag["usage_count"] == 0


class TestTagValidation:
    """Test tag data validation."""

    async def test_empty_tag_name_fails(self, client: AsyncClient):
        """Test that empty tag names are rejected."""
        response = await client.post("/api/tags/", json={"name": ""})
        assert response.status_code == 422

    async def test_invalid_color_format_fails(self, client: AsyncClient):
        """Test that invalid color formats are rejected."""
        invalid_colors = ["red", "FF0000", "#GG0000", "#FF00"]

        for color in invalid_colors:
            response = await client.post("/api/tags/", json={
                "name": f"test-{color}",
                "color": color
            })
            assert response.status_code == 422

    async def test_valid_color_format_succeeds(self, client: AsyncClient):
        """Test that valid color formats are accepted."""
        valid_colors = ["#FF0000", "#00ff00", "#0000FF"]

        for i, color in enumerate(valid_colors):
            response = await client.post("/api/tags/", json={
                "name": f"color-test-{i}",
                "color": color
            })
            assert response.status_code == 200
            data = response.json()
            assert data["color"] == color.upper()

    async def test_tag_name_case_insensitive(self, client: AsyncClient):
        """Test that tag names are case insensitive for uniqueness."""
        # Create tag with lowercase
        response1 = await client.post("/api/tags/", json={"name": "testcase"})
        assert response1.status_code == 200

        # Try to create with different case
        response2 = await client.post("/api/tags/", json={"name": "TestCase"})
        assert response2.status_code == 400

        response3 = await client.post("/api/tags/", json={"name": "TESTCASE"})
        assert response3.status_code == 400


class TestSeriesTagFiltering:
    """Test series filtering by tags."""

    async def test_filter_series_by_tag_ids(self, client: AsyncClient, test_series):
        """Test filtering series by tag IDs."""
        # Create tags and assign to series
        tag_response = await client.post("/api/tags/", json={"name": "filter-tag"})
        tag_id = tag_response.json()["id"]

        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag_id]})

        # Filter series by tag
        response = await client.get(f"/api/series/?tag_ids={tag_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1

        # Verify returned series has the tag
        found_series = next((s for s in data if s["id"] == str(test_series.id)), None)
        assert found_series is not None
        assert any(tag["id"] == tag_id for tag in found_series["user_tags"])

    async def test_filter_series_by_tag_names(self, client: AsyncClient, test_series):
        """Test filtering series by tag names."""
        # Create tag and assign to series
        await client.post("/api/tags/", json={"name": "name-filter"})
        tag_response = await client.get("/api/tags/?search=name-filter")
        tag_id = tag_response.json()["tags"][0]["id"]

        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag_id]})

        # Filter series by tag name
        response = await client.get("/api/series/?tag_names=name-filter")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1

        # Verify returned series has the tag
        found_series = next((s for s in data if s["id"] == str(test_series.id)), None)
        assert found_series is not None

    async def test_filter_series_by_multiple_tags_and_logic(self, client: AsyncClient, test_series):
        """Test filtering series by multiple tags (AND logic)."""
        # Create two tags
        tag1_response = await client.post("/api/tags/", json={"name": "multi-tag-1"})
        tag2_response = await client.post("/api/tags/", json={"name": "multi-tag-2"})

        tag1_id = tag1_response.json()["id"]
        tag2_id = tag2_response.json()["id"]

        # Assign both tags to series
        await client.put(f"/api/tags/series/{test_series.id}", json={"tag_ids": [tag1_id, tag2_id]})

        # Filter by both tags (should find the series)
        response = await client.get(f"/api/series/?tag_ids={tag1_id}&tag_ids={tag2_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1

        # Filter by one tag that doesn't exist (should not find the series)
        fake_tag_id = str(uuid4())
        response2 = await client.get(f"/api/series/?tag_ids={tag1_id}&tag_ids={fake_tag_id}")
        data2 = response2.json()

        # Should not include our test series since it doesn't have the fake tag
        found_series = next((s for s in data2 if s["id"] == str(test_series.id)), None)
        assert found_series is None
