"""Pytest configuration and fixtures."""

import asyncio
import os
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from kiremisu.database.models import Base
from kiremisu.database.connection import get_db
from kiremisu.main import app


# Test database URL - uses PostgreSQL test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://kiremisu:kiremisu@localhost:5432/kiremisu_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    await test_engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with proper isolation."""
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # Clear all tables before each test for complete isolation
        await session.execute(text("TRUNCATE TABLE chapters CASCADE"))
        await session.execute(text("TRUNCATE TABLE series CASCADE"))
        await session.execute(text("TRUNCATE TABLE library_paths CASCADE"))
        await session.execute(text("TRUNCATE TABLE job_queue CASCADE"))
        await session.execute(text("TRUNCATE TABLE annotations CASCADE"))
        await session.execute(text("TRUNCATE TABLE user_lists CASCADE"))
        await session.commit()

        yield session

        # Clean up after test
        await session.execute(text("TRUNCATE TABLE chapters CASCADE"))
        await session.execute(text("TRUNCATE TABLE series CASCADE"))
        await session.execute(text("TRUNCATE TABLE library_paths CASCADE"))
        await session.execute(text("TRUNCATE TABLE job_queue CASCADE"))
        await session.execute(text("TRUNCATE TABLE annotations CASCADE"))
        await session.execute(text("TRUNCATE TABLE user_lists CASCADE"))
        await session.commit()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Use the correct AsyncClient initialization for httpx 0.28+
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
