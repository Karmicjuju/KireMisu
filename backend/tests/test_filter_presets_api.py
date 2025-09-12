"""Tests for filter preset API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestFilterPresetAPI:
    """Test filter preset API endpoints."""
    
    def test_create_filter_preset_endpoint(self, client: TestClient):
        """Test creating a filter preset via API."""
        preset_data = {
            "name": "Action Series",
            "description": "All action series",
            "filters": {
                "genres": ["Action"],
                "filter_logic": "and"
            },
            "sorting": {
                "sort_by": [
                    {"field": "title", "direction": "asc"}
                ]
            },
            "is_public": False
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Action Series"
        assert data["description"] == "All action series"
        assert data["is_public"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_filter_presets_endpoint(self, client: TestClient):
        """Test getting filter presets list."""
        response = client.get("/api/v1/filter-presets/?page=1&size=20")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
    
    def test_get_filter_preset_by_id_endpoint(self, client: TestClient):
        """Test getting a specific filter preset."""
        # First create a preset
        preset_data = {
            "name": "Test Preset",
            "filters": {"search": "test"},
            "is_public": False
        }
        
        create_response = client.post("/api/v1/filter-presets/", json=preset_data)
        assert create_response.status_code == 201
        preset_id = create_response.json()["id"]
        
        # Then retrieve it
        response = client.get(f"/api/v1/filter-presets/{preset_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Preset"
        assert data["id"] == preset_id
    
    def test_update_filter_preset_endpoint(self, client: TestClient):
        """Test updating a filter preset."""
        # First create a preset
        preset_data = {
            "name": "Original Name",
            "filters": {"search": "original"},
            "is_public": False
        }
        
        create_response = client.post("/api/v1/filter-presets/", json=preset_data)
        assert create_response.status_code == 201
        preset_id = create_response.json()["id"]
        
        # Update the preset
        update_data = {
            "name": "Updated Name",
            "description": "Updated description"
        }
        
        response = client.patch(f"/api/v1/filter-presets/{preset_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
    
    def test_delete_filter_preset_endpoint(self, client: TestClient):
        """Test deleting a filter preset."""
        # First create a preset
        preset_data = {
            "name": "To Be Deleted",
            "filters": {"search": "delete"},
            "is_public": False
        }
        
        create_response = client.post("/api/v1/filter-presets/", json=preset_data)
        assert create_response.status_code == 201
        preset_id = create_response.json()["id"]
        
        # Delete the preset
        response = client.delete(f"/api/v1/filter-presets/{preset_id}")
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/api/v1/filter-presets/{preset_id}")
        assert get_response.status_code == 404
    
    def test_get_public_filter_presets_endpoint(self, client: TestClient):
        """Test getting public filter presets."""
        response = client.get("/api/v1/filter-presets/public/?page=1&size=20")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
    
    def test_search_filter_presets_endpoint(self, client: TestClient):
        """Test searching filter presets."""
        # First create a preset to search for
        preset_data = {
            "name": "Searchable Preset",
            "description": "A preset for testing search functionality",
            "filters": {"search": "searchable"},
            "is_public": False
        }
        
        create_response = client.post("/api/v1/filter-presets/", json=preset_data)
        assert create_response.status_code == 201
        
        # Search for the preset
        response = client.get("/api/v1/filter-presets/?search=Searchable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        
        # Check if our preset is in the results
        preset_names = [item["name"] for item in data["items"]]
        assert "Searchable Preset" in preset_names
    
    def test_invalid_filter_preset_data(self, client: TestClient):
        """Test creating preset with invalid data."""
        # Missing required fields
        invalid_data = {
            "description": "Missing name and filters"
        }
        
        response = client.post("/api/v1/filter-presets/", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_preset_name_uniqueness_api(self, client: TestClient):
        """Test that duplicate preset names are rejected."""
        preset_data = {
            "name": "Duplicate Name",
            "filters": {"search": "duplicate"}
        }
        
        # Create first preset
        response1 = client.post("/api/v1/filter-presets/", json=preset_data)
        assert response1.status_code == 201
        
        # Try to create second with same name
        response2 = client.post("/api/v1/filter-presets/", json=preset_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    def test_access_nonexistent_preset(self, client: TestClient):
        """Test accessing a preset that doesn't exist."""
        response = client.get("/api/v1/filter-presets/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_nonexistent_preset(self, client: TestClient):
        """Test updating a preset that doesn't exist."""
        update_data = {"name": "New Name"}
        
        response = client.patch("/api/v1/filter-presets/99999", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_delete_nonexistent_preset(self, client: TestClient):
        """Test deleting a preset that doesn't exist."""
        response = client.delete("/api/v1/filter-presets/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_complex_filter_preset(self, client: TestClient):
        """Test creating a preset with complex filters and sorting."""
        complex_preset = {
            "name": "Complex Filter",
            "description": "A preset with multiple filters and sorting options",
            "filters": {
                "search": "action",
                "status": ["completed", "ongoing"],
                "genres": ["Action", "Adventure"],
                "tags": ["Fantasy"],
                "rating_filter": {
                    "min_rating": 8.0,
                    "max_rating": 10.0
                },
                "read_status": ["completed", "reading"],
                "filter_logic": "and"
            },
            "sorting": {
                "sort_by": [
                    {"field": "rating", "direction": "desc"},
                    {"field": "title", "direction": "asc"}
                ]
            },
            "is_public": True
        }
        
        response = client.post("/api/v1/filter-presets/", json=complex_preset)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Complex Filter"
        assert data["is_public"] is True
        
        # Verify the complex filters are stored correctly
        assert "search" in data["filters"]
        assert "status" in data["filters"]
        assert "genres" in data["filters"]
        assert "rating_filter" in data["filters"]
        assert "sort_by" in data["sorting"]
    
    def test_use_preset_in_series_filter(self, client: TestClient):
        """Test using a preset in the series filter endpoint."""
        # First create a preset
        preset_data = {
            "name": "Test Filter Preset",
            "filters": {
                "status": ["completed"],
                "filter_logic": "and"
            },
            "sorting": {
                "sort_by": [{"field": "title", "direction": "asc"}]
            }
        }
        
        create_response = client.post("/api/v1/filter-presets/", json=preset_data)
        assert create_response.status_code == 201
        preset_id = create_response.json()["id"]
        
        # Use the preset in series filtering
        filter_request = {
            "page": 1,
            "size": 10,
            "preset_id": preset_id
        }
        
        response = client.post("/api/v1/series/filter", json=filter_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "applied_filters" in data
        assert "applied_sorting" in data
        
        # Check that preset filters were applied
        assert data["applied_filters"].get("status") == ["completed"]
        assert data["applied_sorting"].get("sort_by") is not None


class TestFilterPresetValidation:
    """Test filter preset validation."""
    
    def test_invalid_sort_field(self, client: TestClient):
        """Test validation of invalid sort field."""
        preset_data = {
            "name": "Invalid Sort",
            "filters": {"search": "test"},
            "sorting": {
                "sort_by": [{"field": "invalid_field", "direction": "asc"}]
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_sort_direction(self, client: TestClient):
        """Test validation of invalid sort direction."""
        preset_data = {
            "name": "Invalid Direction",
            "filters": {"search": "test"},
            "sorting": {
                "sort_by": [{"field": "title", "direction": "invalid"}]
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_status_value(self, client: TestClient):
        """Test validation of invalid status value."""
        preset_data = {
            "name": "Invalid Status",
            "filters": {
                "status": ["invalid_status"]
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_filter_logic(self, client: TestClient):
        """Test validation of invalid filter logic."""
        preset_data = {
            "name": "Invalid Logic",
            "filters": {
                "search": "test",
                "filter_logic": "invalid_logic"
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_empty_preset_name(self, client: TestClient):
        """Test validation of empty preset name."""
        preset_data = {
            "name": "",
            "filters": {"search": "test"}
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_preset_name_too_long(self, client: TestClient):
        """Test validation of preset name that's too long."""
        preset_data = {
            "name": "x" * 101,  # Exceeds 100 character limit
            "filters": {"search": "test"}
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_rating_filter_validation(self, client: TestClient):
        """Test validation of rating filter ranges."""
        # Invalid: min_rating > max_rating
        preset_data = {
            "name": "Invalid Rating Range",
            "filters": {
                "rating_filter": {
                    "min_rating": 9.0,
                    "max_rating": 8.0
                }
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_too_many_sort_criteria(self, client: TestClient):
        """Test validation of too many sort criteria."""
        preset_data = {
            "name": "Too Many Sorts",
            "filters": {"search": "test"},
            "sorting": {
                "sort_by": [
                    {"field": "title", "direction": "asc"},
                    {"field": "author", "direction": "asc"},
                    {"field": "status", "direction": "asc"},
                    {"field": "rating", "direction": "desc"}  # Should exceed limit of 3
                ]
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_duplicate_sort_fields(self, client: TestClient):
        """Test validation of duplicate sort fields."""
        preset_data = {
            "name": "Duplicate Sort Fields",
            "filters": {"search": "test"},
            "sorting": {
                "sort_by": [
                    {"field": "title", "direction": "asc"},
                    {"field": "title", "direction": "desc"}  # Duplicate field
                ]
            }
        }
        
        response = client.post("/api/v1/filter-presets/", json=preset_data)
        
        assert response.status_code == 422  # Validation error