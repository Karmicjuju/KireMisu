"""Tests for FastAPI-Users authentication system."""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_async_session, create_db_and_tables
from app.models.user import User
from app.users import get_user_db
from app.schemas.user import UserCreate


# Fixtures are now defined in conftest.py


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_user_success(self, client: TestClient, test_user_data: dict):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"] 
        assert data["full_name"] == test_user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "id" in data

    def test_register_duplicate_email(self, client: TestClient, test_user_data: dict):
        """Test registration with duplicate email fails."""
        # Register first user
        client.post("/api/v1/auth/register", json=test_user_data)
        
        # Try to register second user with same email
        duplicate_user = test_user_data.copy()
        duplicate_user["username"] = "different_username"
        response = client.post("/api/v1/auth/register", json=duplicate_user)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, client: TestClient, test_user_data: dict):
        """Test registration with duplicate username fails."""
        # Register first user
        client.post("/api/v1/auth/register", json=test_user_data)
        
        # Try to register second user with same username
        duplicate_user = test_user_data.copy()
        duplicate_user["email"] = "different@example.com"
        response = client.post("/api/v1/auth/register", json=duplicate_user)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_single_user_limit(self, client: TestClient, test_user_data: dict):
        """Test single user limitation is enforced."""
        # Register first user successfully
        response1 = client.post("/api/v1/auth/register", json=test_user_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to register second user
        second_user = {
            "username": "seconduser",
            "email": "second@example.com",
            "password": "SecondPass123!",
            "full_name": "Second User"
        }
        response2 = client.post("/api/v1/auth/register", json=second_user)
        
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "single user" in response2.json()["detail"].lower()

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password fails."""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase  
            "NoNumbers!",  # No numbers
            "NoSpecial123",  # No special characters
        ]
        
        for weak_password in weak_passwords:
            user_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": weak_password,
                "full_name": "Test User"
            }
            response = client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email fails."""
        user_data = {
            "username": "testuser", 
            "email": "invalid-email",
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login functionality."""

    def test_login_success(self, client: TestClient, test_user_data: dict):
        """Test successful user login."""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)
        
        # Login with username
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Check that auth cookie is set
        assert "auth-token" in response.cookies

    def test_login_with_email(self, client: TestClient, test_user_data: dict):
        """Test login with email instead of username."""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)
        
        # Login with email
        login_data = {
            "username": test_user_data["email"], 
            "password": test_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_200_OK

    def test_login_wrong_password(self, client: TestClient, test_user_data: dict):
        """Test login with wrong password fails."""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)
        
        # Try to login with wrong password
        login_data = {
            "username": test_user_data["username"],
            "password": "WrongPassword123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user fails."""
        login_data = {
            "username": "nonexistent",
            "password": "TestPass123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthentication:
    """Test authentication and protected routes."""

    def test_protected_route_without_auth(self, client: TestClient):
        """Test accessing protected route without authentication fails."""
        response = client.get("/api/v1/auth/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_route_with_token(self, client: TestClient, test_user_data: dict):
        """Test accessing protected route with valid token succeeds."""
        # Register and login
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Access protected route with token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]

    def test_protected_route_with_cookie(self, client: TestClient, test_user_data: dict):
        """Test accessing protected route with auth cookie succeeds."""
        # Register and login
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        # The cookie should be automatically included in subsequent requests
        response = client.get("/api/v1/auth/users/me")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == test_user_data["username"]

    def test_invalid_token(self, client: TestClient):
        """Test accessing protected route with invalid token fails."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/users/me", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Test logout functionality."""

    def test_logout_success(self, client: TestClient, test_user_data: dict):
        """Test successful logout."""
        # Register and login
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"] 
        })
        
        # Logout
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Successfully logged out"
        
        # Check that auth cookie is cleared
        assert "auth-token" in response.cookies
        # The cookie should be expired/cleared

    def test_logout_without_auth(self, client: TestClient):
        """Test logout without authentication still succeeds."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == status.HTTP_200_OK


class TestDatabaseIntegration:
    """Test database integration with FastAPI-Users."""

    def test_user_stored_in_database(self, client: TestClient, test_user_data: dict, async_session: AsyncSession):
        """Test that registered user is properly stored in database."""
        # Register user
        response = client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check user in database
        from sqlalchemy import select
        result = await async_session.execute(select(User).where(User.username == test_user_data["username"]))
        user = result.scalar_one_or_none()
        
        assert user is not None
        assert user.username == test_user_data["username"]
        assert user.email == test_user_data["email"]
        assert user.full_name == test_user_data["full_name"]
        assert user.is_active is True
        assert user.is_verified is False
        assert user.hashed_password != test_user_data["password"]  # Password should be hashed

    def test_password_is_hashed(self, client: TestClient, test_user_data: dict, async_session: AsyncSession):
        """Test that passwords are properly hashed in database."""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)
        
        # Check user in database
        from sqlalchemy import select
        result = await async_session.execute(select(User).where(User.username == test_user_data["username"]))
        user = result.scalar_one_or_none()
        
        # Password should be hashed, not plain text
        assert user.hashed_password != test_user_data["password"]
        assert len(user.hashed_password) > 20  # Hashed passwords are longer
        assert "$" in user.hashed_password  # bcrypt hashes contain "$"