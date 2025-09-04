import os
import sys
import secrets
from pathlib import Path

# Generate a secure random secret key for each test run
# This prevents using predictable test secrets in production
test_secret_key = secrets.token_urlsafe(64)
os.environ.setdefault("SECRET_KEY", test_secret_key)
os.environ.setdefault("POSTGRES_USER", "kiremisu")
os.environ.setdefault("POSTGRES_PASSWORD", "development")
os.environ.setdefault("POSTGRES_DB", "kiremisu")
# Use PostgreSQL database for tests (same as development)
# Note: In production, ensure test database is separate from production database
os.environ.setdefault("DATABASE_URL", "postgresql://kiremisu:development@localhost:5432/kiremisu")

# Additional security-related test environment variables
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("ENVIRONMENT", "test")

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    # Use the same PostgreSQL database as development
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(
        database_url,
        echo=True,  # Enable SQL logging for debugging
    )
    return engine


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables for testing."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up after all tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables):
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    # Rollback any changes after the test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a test client with dependency override."""
    def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client
    
    # Clean up dependency override
    app.dependency_overrides.clear()