"""Integration tests for FastAPI-Users authentication system."""

import pytest
from httpx import AsyncClient


class TestAuthenticationIntegration:
    """Test complete authentication workflows."""

    async def test_complete_auth_workflow(self, client: AsyncClient):
        """Test complete registration -> login -> access protected route -> logout workflow."""
        
        # Step 1: Register a new user
        user_data = {
            "username": "integrationuser",
            "email": "integration@example.com",
            "password": "IntegrationPass123!",
            "full_name": "Integration Test User"
        }
        
        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        
        registered_user = register_response.json()
        assert registered_user["username"] == user_data["username"]
        assert registered_user["email"] == user_data["email"]
        assert registered_user["is_active"] is True
        
        # Step 2: Login with the registered user
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        # Step 3: Access protected route with token
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        me_response = await client.get("/api/v1/auth/users/me", headers=headers)
        assert me_response.status_code == 200
        
        user_info = me_response.json()
        assert user_info["username"] == user_data["username"]
        assert user_info["email"] == user_data["email"]
        assert user_info["full_name"] == user_data["full_name"]
        
        # Step 4: Logout
        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "Successfully logged out"
        
        # Step 5: Verify that accessing protected route without token fails
        no_auth_response = await client.get("/api/v1/auth/users/me")
        assert no_auth_response.status_code == 401

    async def test_fastapi_users_endpoints_work(self, client: AsyncClient):
        """Test that FastAPI-Users generated endpoints work correctly."""
        
        # Test JWT login endpoint
        user_data = {
            "username": "jwtuser",
            "email": "jwt@example.com",
            "password": "JwtTestPass123!",
            "full_name": "JWT Test User"
        }
        
        # Register user
        await client.post("/api/v1/auth/register", json=user_data)
        
        # Test JWT login endpoint
        jwt_login_response = await client.post("/api/v1/auth/jwt/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        assert jwt_login_response.status_code == 200
        jwt_token = jwt_login_response.json()
        assert "access_token" in jwt_token
        assert jwt_token["token_type"] == "bearer"
        
        # Test JWT logout endpoint
        headers = {"Authorization": f"Bearer {jwt_token['access_token']}"}
        jwt_logout_response = await client.post("/api/v1/auth/jwt/logout", headers=headers)
        assert jwt_logout_response.status_code == 200

    async def test_cookie_authentication_workflow(self, client: AsyncClient):
        """Test authentication using cookies instead of headers."""
        
        user_data = {
            "username": "cookieuser",
            "email": "cookie@example.com",
            "password": "CookiePass123!",
            "full_name": "Cookie Test User"
        }
        
        # Register and login user
        await client.post("/api/v1/auth/register", json=user_data)
        login_response = await client.post("/api/v1/auth/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        
        # Verify cookie is set
        assert "auth-token" in login_response.cookies
        
        # Access protected route (cookie should be automatically included)
        me_response = await client.get("/api/v1/auth/users/me")
        assert me_response.status_code == 200
        
        user_info = me_response.json()
        assert user_info["username"] == user_data["username"]

    async def test_single_user_limitation_enforced(self, client: AsyncClient):
        """Test that single user limitation is properly enforced."""
        
        # Register first user
        first_user = {
            "username": "firstuser",
            "email": "first@example.com",
            "password": "FirstPass123!",
            "full_name": "First User"
        }
        
        first_response = await client.post("/api/v1/auth/register", json=first_user)
        assert first_response.status_code == 201
        
        # Try to register second user - should fail
        second_user = {
            "username": "seconduser", 
            "email": "second@example.com",
            "password": "SecondPass123!",
            "full_name": "Second User"
        }
        
        second_response = await client.post("/api/v1/auth/register", json=second_user)
        assert second_response.status_code == 400
        
        error_detail = second_response.json()["detail"]
        assert "single user" in error_detail.lower()

    async def test_password_validation_comprehensive(self, client: AsyncClient):
        """Test comprehensive password validation scenarios."""
        
        base_user = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User"
        }
        
        # Test various invalid passwords
        invalid_passwords = [
            ("short", "too short"),
            ("nouppercase123!", "no uppercase"),
            ("NOLOWERCASE123!", "no lowercase"),
            ("NoNumbers!", "no numbers"), 
            ("NoSpecial123", "no special characters"),
            ("", "empty password"),
        ]
        
        for password, description in invalid_passwords:
            user_data = base_user.copy()
            user_data["password"] = password
            
            response = await client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 422, f"Password validation failed for {description}: {password}"

    async def test_email_validation(self, client: AsyncClient):
        """Test email validation in registration."""
        
        base_user = {
            "username": "testuser",
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        # Test invalid emails
        invalid_emails = [
            "invalid-email",
            "missing@domain",
            "@missinglocal.com",
            "spaces in@email.com",
            "double@@domain.com",
        ]
        
        for invalid_email in invalid_emails:
            user_data = base_user.copy()
            user_data["email"] = invalid_email
            
            response = await client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 422, f"Email validation failed for: {invalid_email}"