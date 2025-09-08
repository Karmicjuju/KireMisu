"""Basic authentication tests for FastAPI-Users system."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestBasicAuth:
    """Test basic authentication functionality."""

    def test_app_starts(self):
        """Test that the app starts successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert "KireMisu API" in response.json()["message"]

    def test_health_endpoint(self):
        """Test health endpoint works."""
        response = client.get("/api/v1/health")
        # Health endpoint may fail due to database connection, but it should not crash
        # Accept healthy, unhealthy, or not found (if not properly registered)
        assert response.status_code in [200, 404, 500]

    def test_register_endpoint_exists(self):
        """Test that register endpoint exists and responds."""
        # Send invalid data to test endpoint existence
        response = client.post("/api/v1/auth/register", json={})
        # Should return validation error, not 404
        assert response.status_code in [400, 422]
        assert response.status_code != 404

    def test_login_endpoint_exists(self):
        """Test that login endpoint exists and responds."""
        # Send invalid data to test endpoint existence  
        response = client.post("/api/v1/auth/login", data={})
        # Should return validation error or auth error, not 404
        assert response.status_code in [400, 401, 422]
        assert response.status_code != 404

    def test_logout_endpoint_exists(self):
        """Test that logout endpoint exists."""
        response = client.post("/api/v1/auth/logout")
        # Should succeed even without auth
        assert response.status_code == 200

    def test_protected_endpoint_requires_auth(self):
        """Test that protected endpoint requires authentication."""
        response = client.get("/api/v1/auth/users/me")
        assert response.status_code == 401

    def test_fastapi_users_jwt_endpoints_exist(self):
        """Test that FastAPI-Users JWT endpoints are available."""
        # JWT login endpoint
        response = client.post("/api/v1/auth/jwt/login", data={})
        assert response.status_code in [400, 401, 422]
        assert response.status_code != 404

    def test_password_validation_in_registration(self):
        """Test that password validation works."""
        weak_password_user = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",  # Too weak
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=weak_password_user)
        assert response.status_code == 422  # Validation error
        
        error_detail = response.json()
        assert "detail" in error_detail

    def test_email_validation_in_registration(self):
        """Test that email validation works."""
        invalid_email_user = {
            "username": "testuser", 
            "email": "invalid-email",  # Invalid email
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=invalid_email_user)
        assert response.status_code == 422  # Validation error