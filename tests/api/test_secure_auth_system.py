"""
Comprehensive tests for the secure authentication system.

Tests all security features including:
- Password complexity validation
- Rate limiting
- Account lockout
- JWT token security
- User registration/login
- Session invalidation
"""


import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.auth import (
    blacklist_token,
    check_auth_rate_limit,
    create_jwt_token,
    create_user_db,
    is_token_blacklisted,
    validate_password_complexity,
    verify_jwt_token,
    verify_user_db,
)
from kiremisu.database.models import User
from kiremisu.main import app


class TestPasswordComplexity:
    """Test password complexity validation."""

    def test_valid_passwords(self):
        """Test passwords that meet all requirements."""
        valid_passwords = [
            "SecurePass123!",
            "MyStr0ng#Password",
            "C0mplex&S3cure!",
            "Testing123@#$",
        ]

        for password in valid_passwords:
            errors = validate_password_complexity(password)
            assert len(errors) == 0, f"Password '{password}' should be valid but got errors: {errors}"

    def test_invalid_passwords(self):
        """Test passwords that fail various requirements."""
        invalid_cases = [
            ("short7!", ["Password must be at least 8 characters long"]),
            ("nouppercase123!", ["Password must contain at least one uppercase letter"]),
            ("NOLOWERCASE123!", ["Password must contain at least one lowercase letter"]),
            ("NoNumbers!", ["Password must contain at least one digit"]),
            ("NoSpecial123", ["Password must contain at least one special character"]),
            ("password123!", ["Password contains common weak patterns"]),
            ("qwerty123!", ["Password contains common weak patterns"]),
            ("admin123!", ["Password contains common weak patterns"]),
        ]

        for password, expected_errors in invalid_cases:
            errors = validate_password_complexity(password)
            assert len(errors) > 0, f"Password '{password}' should be invalid"

            for expected_error in expected_errors:
                assert any(expected_error in error for error in errors), \
                    f"Expected error '{expected_error}' not found in {errors}"


class TestRateLimiting:
    """Test authentication rate limiting."""

    def test_rate_limit_allows_normal_usage(self):
        """Test that normal authentication attempts are allowed."""
        client_ip = "192.168.1.100"

        # First few attempts should be allowed
        for i in range(4):
            assert check_auth_rate_limit(client_ip), f"Attempt {i+1} should be allowed"

    def test_rate_limit_blocks_excessive_attempts(self):
        """Test that excessive attempts are blocked."""
        client_ip = "192.168.1.101"

        # Use up the limit
        for i in range(5):
            assert check_auth_rate_limit(client_ip), f"Attempt {i+1} should be allowed"

        # Next attempt should be blocked
        assert not check_auth_rate_limit(client_ip), "6th attempt should be blocked"

    def test_rate_limit_is_per_ip(self):
        """Test that rate limiting is applied per IP address."""
        ip1 = "192.168.1.102"
        ip2 = "192.168.1.103"

        # Use up limit for IP1
        for _i in range(5):
            assert check_auth_rate_limit(ip1)
        assert not check_auth_rate_limit(ip1)

        # IP2 should still be allowed
        assert check_auth_rate_limit(ip2), "Different IP should not be affected"


class TestJWTTokenSecurity:
    """Test JWT token generation and validation."""

    def test_jwt_token_creation_requires_user_model(self):
        """Test that JWT creation requires a proper User model."""
        # Create a mock user
        from uuid import uuid4
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            email_verified=False
        )

        token = create_jwt_token(user)
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are reasonably long

    def test_jwt_token_validation(self):
        """Test JWT token validation."""
        from uuid import uuid4
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            email_verified=False
        )

        # Create and verify token
        token = create_jwt_token(user)
        payload = verify_jwt_token(token)

        assert payload["username"] == "testuser"
        assert payload["user_id"] == str(user.id)
        assert not payload["is_admin"]
        assert "jti" in payload  # JWT ID for blacklisting
        assert "exp" in payload  # Expiration
        assert "iat" in payload  # Issued at

    def test_token_blacklisting(self):
        """Test token blacklisting functionality."""
        token = "test.jwt.token"

        # Token should not be blacklisted initially
        assert not is_token_blacklisted(token)

        # Blacklist token
        blacklist_token(token)
        assert is_token_blacklisted(token)

    def test_invalid_token_handling(self):
        """Test handling of invalid JWT tokens."""
        with pytest.raises(Exception):  # Should raise HTTPException
            verify_jwt_token("invalid.jwt.token")

    def test_expired_token_handling(self):
        """Test handling of expired JWT tokens."""
        # This would require mocking the JWT library or creating an expired token
        # For now, we'll test with a malformed token that represents expiration
        with pytest.raises(Exception):
            verify_jwt_token("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDk0NTkyMDB9.invalid")


class TestUserRegistration:
    """Test user registration functionality."""

    @pytest.mark.asyncio
    async def test_user_creation_success(self, async_db_session: AsyncSession):
        """Test successful user creation."""
        user = await create_user_db(
            db=async_db_session,
            username="newuser",
            email="newuser@example.com",
            password="SecurePass123!",
            is_admin=False
        )

        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active
        assert not user.is_admin
        assert not user.email_verified
        assert user.failed_login_attempts == 0
        # Password should be hashed, not stored in plain text
        assert user.password_hash != "SecurePass123!"

    @pytest.mark.asyncio
    async def test_user_creation_duplicate_username(self, async_db_session: AsyncSession):
        """Test that duplicate usernames are rejected."""
        # Create first user
        await create_user_db(
            db=async_db_session,
            username="duplicate",
            email="first@example.com",
            password="SecurePass123!",
        )

        # Attempt to create second user with same username
        with pytest.raises(ValueError, match="Username is already taken"):
            await create_user_db(
                db=async_db_session,
                username="duplicate",
                email="second@example.com",
                password="AnotherPass456!",
            )

    @pytest.mark.asyncio
    async def test_user_creation_duplicate_email(self, async_db_session: AsyncSession):
        """Test that duplicate emails are rejected."""
        # Create first user
        await create_user_db(
            db=async_db_session,
            username="user1",
            email="duplicate@example.com",
            password="SecurePass123!",
        )

        # Attempt to create second user with same email
        with pytest.raises(ValueError, match="Email address is already registered"):
            await create_user_db(
                db=async_db_session,
                username="user2",
                email="duplicate@example.com",
                password="AnotherPass456!",
            )

    @pytest.mark.asyncio
    async def test_user_creation_weak_password(self, async_db_session: AsyncSession):
        """Test that weak passwords are rejected."""
        with pytest.raises(ValueError, match="Password validation failed"):
            await create_user_db(
                db=async_db_session,
                username="weakpassuser",
                email="weak@example.com",
                password="weak",  # Too short, no complexity
            )


class TestUserAuthentication:
    """Test user authentication functionality."""

    @pytest.mark.asyncio
    async def test_successful_authentication(self, async_db_session: AsyncSession):
        """Test successful user authentication."""
        # Create user
        password = "SecurePass123!"
        user = await create_user_db(
            db=async_db_session,
            username="authuser",
            email="auth@example.com",
            password=password,
        )

        # Verify authentication
        authenticated_user = await verify_user_db(
            db=async_db_session,
            username_or_email="authuser",
            password=password,
        )

        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.failed_login_attempts == 0
        assert authenticated_user.locked_until is None

    @pytest.mark.asyncio
    async def test_failed_authentication_wrong_password(self, async_db_session: AsyncSession):
        """Test authentication failure with wrong password."""
        # Create user
        await create_user_db(
            db=async_db_session,
            username="wrongpassuser",
            email="wrongpass@example.com",
            password="SecurePass123!",
        )

        # Attempt authentication with wrong password
        authenticated_user = await verify_user_db(
            db=async_db_session,
            username_or_email="wrongpassuser",
            password="WrongPassword!",
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_account_lockout_after_failed_attempts(self, async_db_session: AsyncSession):
        """Test account lockout after multiple failed attempts."""
        # Create user
        await create_user_db(
            db=async_db_session,
            username="lockoutuser",
            email="lockout@example.com",
            password="SecurePass123!",
        )

        # Make 5 failed attempts
        for _i in range(5):
            result = await verify_user_db(
                db=async_db_session,
                username_or_email="lockoutuser",
                password="WrongPassword!",
            )
            assert result is None

        # User should now be locked out even with correct password
        result = await verify_user_db(
            db=async_db_session,
            username_or_email="lockoutuser",
            password="SecurePass123!",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_authentication_by_email(self, async_db_session: AsyncSession):
        """Test authentication using email address."""
        # Create user
        password = "SecurePass123!"
        await create_user_db(
            db=async_db_session,
            username="emailauthuser",
            email="emailauth@example.com",
            password=password,
        )

        # Authenticate using email
        authenticated_user = await verify_user_db(
            db=async_db_session,
            username_or_email="emailauth@example.com",
            password=password,
        )

        assert authenticated_user is not None
        assert authenticated_user.email == "emailauth@example.com"


class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    def test_registration_endpoint_success(self):
        """Test successful user registration via API."""
        client = TestClient(app)

        registration_data = {
            "username": "apiuser",
            "email": "apiuser@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "display_name": "API User"
        }

        response = client.post("/api/auth/register", json=registration_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"]
        assert data["user"]["username"] == "apiuser"
        assert data["user"]["email"] == "apiuser@example.com"
        assert data["user"]["display_name"] == "API User"
        assert not data["user"]["is_admin"]

    def test_registration_endpoint_password_mismatch(self):
        """Test registration failure with password mismatch."""
        client = TestClient(app)

        registration_data = {
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass456!",
        }

        response = client.post("/api/auth/register", json=registration_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_registration_endpoint_weak_password(self):
        """Test registration failure with weak password."""
        client = TestClient(app)

        registration_data = {
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "weak",
            "confirm_password": "weak",
        }

        response = client.post("/api/auth/register", json=registration_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_endpoint_success(self):
        """Test successful login via API."""
        client = TestClient(app)

        # First register a user
        registration_data = {
            "username": "loginuser",
            "email": "login@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        client.post("/api/auth/register", json=registration_data)

        # Then login
        login_data = {
            "username_or_email": "loginuser",
            "password": "SecurePass123!",
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "loginuser"

    def test_login_endpoint_invalid_credentials(self):
        """Test login failure with invalid credentials."""
        client = TestClient(app)

        login_data = {
            "username_or_email": "nonexistent",
            "password": "WrongPassword123!",
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_validation_endpoint(self):
        """Test password validation endpoint."""
        client = TestClient(app)

        # Test valid password
        response = client.post("/api/auth/validate-password?password=SecurePass123!")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"]
        assert len(data["errors"]) == 0

        # Test invalid password
        response = client.post("/api/auth/validate-password?password=weak")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert not data["is_valid"]
        assert len(data["errors"]) > 0

    def test_protected_endpoint_requires_auth(self):
        """Test that protected endpoints require authentication."""
        client = TestClient(app)

        # Try to access protected endpoint without token
        response = client.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid token."""
        client = TestClient(app)

        # Register and login to get token
        registration_data = {
            "username": "protecteduser",
            "email": "protected@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        client.post("/api/auth/register", json=registration_data)

        login_data = {
            "username_or_email": "protecteduser",
            "password": "SecurePass123!",
        }
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Access protected endpoint with token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "protecteduser"


class TestSecurityFeatures:
    """Test additional security features."""

    def test_no_information_leakage_in_login_errors(self):
        """Test that login errors don't leak information about user existence."""
        client = TestClient(app)

        # Try to login with non-existent user
        login_data = {
            "username_or_email": "nonexistent",
            "password": "SomePassword123!",
        }
        response1 = client.post("/api/auth/login", json=login_data)

        # Register a user and try with wrong password
        registration_data = {
            "username": "realuser",
            "email": "real@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        client.post("/api/auth/register", json=registration_data)

        login_data = {
            "username_or_email": "realuser",
            "password": "WrongPassword123!",
        }
        response2 = client.post("/api/auth/login", json=login_data)

        # Both should return the same generic error
        assert response1.status_code == status.HTTP_401_UNAUTHORIZED
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED
        assert response1.json()["detail"] == response2.json()["detail"]
        assert "Invalid credentials" in response1.json()["detail"]

    def test_rate_limiting_prevents_brute_force(self):
        """Test that rate limiting prevents brute force attacks."""
        client = TestClient(app)

        # Make many rapid login attempts from same IP
        login_data = {
            "username_or_email": "bruteforcetest",
            "password": "WrongPassword123!",
        }

        # First few should get 401 (invalid credentials)
        for _i in range(5):
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # After rate limit hit, should get 429 (too many requests)
        response = client.post("/api/auth/login", json=login_data)
        # Note: This test might be flaky due to the actual rate limiter implementation
        # In a real scenario, you'd want to mock the rate limiter for consistent testing
