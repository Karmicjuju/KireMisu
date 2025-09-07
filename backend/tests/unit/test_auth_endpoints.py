import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.schemas.user import UserCreate


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """Create test client with test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_user_data():
    """Sample valid user registration data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "TestPassword123!"
    }


class TestPasswordValidation:
    """Test password strength validation in UserCreate schema."""
    
    def test_valid_password(self, valid_user_data):
        """Test that valid password passes validation."""
        user_create = UserCreate(**valid_user_data)
        assert user_create.password == "TestPassword123!"
    
    def test_password_too_short(self, valid_user_data):
        """Test that password shorter than 8 characters fails."""
        valid_user_data["password"] = "Test1!"
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            UserCreate(**valid_user_data)
    
    def test_password_no_uppercase(self, valid_user_data):
        """Test that password without uppercase letter fails."""
        valid_user_data["password"] = "testpassword123!"
        with pytest.raises(ValueError, match="Password must contain at least one uppercase letter"):
            UserCreate(**valid_user_data)
    
    def test_password_no_lowercase(self, valid_user_data):
        """Test that password without lowercase letter fails."""
        valid_user_data["password"] = "TESTPASSWORD123!"
        with pytest.raises(ValueError, match="Password must contain at least one lowercase letter"):
            UserCreate(**valid_user_data)
    
    def test_password_no_number(self, valid_user_data):
        """Test that password without number fails."""
        valid_user_data["password"] = "TestPassword!"
        with pytest.raises(ValueError, match="Password must contain at least one number"):
            UserCreate(**valid_user_data)
    
    def test_password_no_special_char(self, valid_user_data):
        """Test that password without special character fails."""
        valid_user_data["password"] = "TestPassword123"
        with pytest.raises(ValueError, match="Password must contain at least one special character"):
            UserCreate(**valid_user_data)


class TestUserRegistration:
    """Test user registration endpoint."""
    
    def test_register_success(self, client, valid_user_data):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=valid_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        # Password should not be in response
        assert "password" not in data
        assert "hashed_password" not in data
    
    def test_register_invalid_password(self, client, valid_user_data):
        """Test registration with invalid password fails."""
        valid_user_data["password"] = "weak"
        response = client.post("/api/v1/auth/register", json=valid_user_data)
        
        assert response.status_code == 422
        assert "Password must be at least 8 characters long" in response.text
    
    def test_register_duplicate_username(self, client, valid_user_data):
        """Test registration with duplicate username fails."""
        # Register first user
        response1 = client.post("/api/v1/auth/register", json=valid_user_data)
        assert response1.status_code == 200
        
        # Try to register second user with same username but different email
        duplicate_user = valid_user_data.copy()
        duplicate_user["email"] = "different@example.com"
        response2 = client.post("/api/v1/auth/register", json=duplicate_user)
        
        assert response2.status_code == 400
        assert "Username already exists" in response2.json()["detail"]
    
    def test_register_duplicate_email(self, client, valid_user_data):
        """Test registration with duplicate email fails."""
        # Register first user
        response1 = client.post("/api/v1/auth/register", json=valid_user_data)
        assert response1.status_code == 200
        
        # Try to register second user with same email but different username
        duplicate_user = valid_user_data.copy()
        duplicate_user["username"] = "differentuser"
        response2 = client.post("/api/v1/auth/register", json=duplicate_user)
        
        assert response2.status_code == 400
        assert "Email already exists" in response2.json()["detail"]
    
    def test_register_single_user_limit(self, client, valid_user_data):
        """Test that only one user can register (single user limit)."""
        # Register first user
        response1 = client.post("/api/v1/auth/register", json=valid_user_data)
        assert response1.status_code == 200
        
        # Try to register second user with different credentials
        second_user = {
            "username": "seconduser",
            "email": "second@example.com", 
            "full_name": "Second User",
            "password": "SecondPassword123!"
        }
        response2 = client.post("/api/v1/auth/register", json=second_user)
        
        assert response2.status_code == 403
        assert "Registration is currently limited to a single user" in response2.json()["detail"]
    
    def test_register_invalid_email(self, client, valid_user_data):
        """Test registration with invalid email fails."""
        valid_user_data["email"] = "invalid-email"
        response = client.post("/api/v1/auth/register", json=valid_user_data)
        
        assert response.status_code == 422
        assert "value is not a valid email address" in response.text
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields fails."""
        incomplete_data = {
            "username": "testuser"
            # Missing email and password
        }
        response = client.post("/api/v1/auth/register", json=incomplete_data)
        
        assert response.status_code == 422
        assert "Field required" in response.text


class TestUserLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client, valid_user_data):
        """Test successful login after registration."""
        # First register a user
        register_response = client.post("/api/v1/auth/register", json=valid_user_data)
        assert register_response.status_code == 200
        
        # Then try to login
        login_data = {
            "username": valid_user_data["username"],
            "password": valid_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Check that auth cookie was set
        assert "auth-token" in response.cookies
    
    def test_login_invalid_credentials(self, client, valid_user_data):
        """Test login with invalid credentials fails."""
        # First register a user
        register_response = client.post("/api/v1/auth/register", json=valid_user_data)
        assert register_response.status_code == 200
        
        # Try to login with wrong password
        login_data = {
            "username": valid_user_data["username"],
            "password": "WrongPassword123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user fails."""
        login_data = {
            "username": "nonexistent",
            "password": "TestPassword123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]


class TestAuthenticatedEndpoints:
    """Test endpoints that require authentication."""
    
    def test_get_current_user(self, client, valid_user_data):
        """Test getting current user information."""
        # Register and login
        register_response = client.post("/api/v1/auth/register", json=valid_user_data)
        assert register_response.status_code == 200
        
        login_data = {
            "username": valid_user_data["username"],
            "password": valid_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        
        # Get current user info
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == valid_user_data["username"]
        assert data["email"] == valid_user_data["email"]
        assert data["is_active"] is True
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication fails."""
        response = client.get("/api/v1/auth/users/me")
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    def test_logout(self, client, valid_user_data):
        """Test logout functionality."""
        # Register and login
        register_response = client.post("/api/v1/auth/register", json=valid_user_data)
        assert register_response.status_code == 200
        
        login_data = {
            "username": valid_user_data["username"],
            "password": valid_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        # Logout
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
        # Check that auth cookie was cleared (it gets set to empty string)
        if "auth-token" in response.cookies:
            auth_cookie = response.cookies["auth-token"]
            assert auth_cookie == ""