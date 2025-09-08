"""Pytest configuration and fixtures for FastAPI-Users tests."""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_async_session, Base
from app.models.user import User

# Test database URL (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(test_engine):
    """Create async database session for testing."""
    TestingSessionLocal = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine):
    """Create test client with test database."""
    TestingSessionLocal = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async def override_get_async_session():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user data with strong password."""
    return {
        "username": "testuser",
        "email": "test@example.com", 
        "password": "TestPass123!",
        "full_name": "Test User"
    }


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, test_user_data: dict):
    """Create a registered user for tests."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def authenticated_user(client: AsyncClient, test_user_data: dict, registered_user):
    """Create an authenticated user session."""
    login_response = await client.post("/api/v1/auth/login", data={
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"user": registered_user, "token": token}