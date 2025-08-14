"""Pytest configuration and fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import UTC
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from kiremisu.database.connection import get_db
from kiremisu.database.models import Annotation, Base, Chapter, Notification, Series
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

    # Drop all tables first to ensure clean state
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Clean up after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession]:
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
        await session.execute(text("TRUNCATE TABLE notifications CASCADE"))
        await session.commit()

        yield session

        # Clean up after test
        await session.execute(text("TRUNCATE TABLE chapters CASCADE"))
        await session.execute(text("TRUNCATE TABLE series CASCADE"))
        await session.execute(text("TRUNCATE TABLE library_paths CASCADE"))
        await session.execute(text("TRUNCATE TABLE job_queue CASCADE"))
        await session.execute(text("TRUNCATE TABLE annotations CASCADE"))
        await session.execute(text("TRUNCATE TABLE user_lists CASCADE"))
        await session.execute(text("TRUNCATE TABLE notifications CASCADE"))
        await session.commit()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Create test HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Use the correct AsyncClient initialization for httpx 0.28+
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Annotation test fixtures
@pytest.fixture
async def sample_series_with_chapters(db_session: AsyncSession):
    """Create a test series with chapters for annotation testing."""
    series = Series(
        id=uuid4(),
        title_primary="Test Manga Series",
        language="en",
        file_path="/test/manga/series",
        total_chapters=3,
        read_chapters=0,
    )
    db_session.add(series)
    await db_session.commit()
    await db_session.refresh(series)

    chapters = []
    for i in range(3):
        chapter = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=float(i + 1),
            title=f"Chapter {i + 1}",
            file_path=f"/test/manga/series/chapter_{i + 1}.cbz",
            file_size=1024 * 1024,  # 1MB
            page_count=20,
        )
        chapters.append(chapter)
        db_session.add(chapter)

    await db_session.commit()
    for chapter in chapters:
        await db_session.refresh(chapter)

    return series, chapters


@pytest.fixture
async def sample_annotation(db_session: AsyncSession, sample_series_with_chapters):
    """Create a single test annotation."""
    series, chapters = sample_series_with_chapters
    chapter = chapters[0]

    annotation = Annotation(
        id=uuid4(),
        chapter_id=chapter.id,
        content="This is a test note annotation",
        page_number=1,
        annotation_type="note",
        position_x=0.5,
        position_y=0.3,
        color="#3b82f6",
    )
    db_session.add(annotation)
    await db_session.commit()
    await db_session.refresh(annotation)

    return annotation


@pytest.fixture
async def sample_annotations(db_session: AsyncSession, sample_series_with_chapters):
    """Create multiple test annotations across different chapters and pages."""
    series, chapters = sample_series_with_chapters

    annotations = []

    # Chapter 1 annotations
    annotations.extend([
        Annotation(
            id=uuid4(),
            chapter_id=chapters[0].id,
            content="Note on page 1",
            page_number=1,
            annotation_type="note",
            position_x=0.2,
            position_y=0.3,
            color="#3b82f6",
        ),
        Annotation(
            id=uuid4(),
            chapter_id=chapters[0].id,
            content="Bookmark on page 1",
            page_number=1,
            annotation_type="bookmark",
            position_x=0.8,
            position_y=0.1,
            color="#f59e0b",
        ),
        Annotation(
            id=uuid4(),
            chapter_id=chapters[0].id,
            content="Highlight on page 2",
            page_number=2,
            annotation_type="highlight",
            position_x=0.5,
            position_y=0.7,
            color="#eab308",
        ),
    ])

    # Chapter 2 annotations
    annotations.extend([
        Annotation(
            id=uuid4(),
            chapter_id=chapters[1].id,
            content="Note on chapter 2",
            page_number=1,
            annotation_type="note",
            position_x=0.3,
            position_y=0.5,
            color="#3b82f6",
        ),
        Annotation(
            id=uuid4(),
            chapter_id=chapters[1].id,
            content="General chapter annotation",
            page_number=None,  # No specific page
            annotation_type="bookmark",
            color="#f59e0b",
        ),
    ])

    for annotation in annotations:
        db_session.add(annotation)

    await db_session.commit()
    for annotation in annotations:
        await db_session.refresh(annotation)

    return annotations


@pytest.fixture
async def sample_series(db_session: AsyncSession):
    """Create a single test series."""
    series = Series(
        id=uuid4(),
        title_primary="Test Series",
        file_path="/test/manga/test-series",
        watching_enabled=False,
    )
    db_session.add(series)
    await db_session.commit()
    await db_session.refresh(series)

    return series


@pytest.fixture
async def sample_notifications(
    db_session: AsyncSession, sample_series: Series
) -> list[Notification]:
    """Create sample notifications for testing."""
    from datetime import datetime

    notifications = []

    for i in range(5):
        notification = Notification(
            notification_type="new_chapter",
            title=f"New chapter available: {sample_series.title_primary}",
            message=f"Chapter {i+1} is now available for reading.",
            series_id=sample_series.id,
            is_read=i % 2 == 0,  # Alternate read/unread
        )

        if notification.is_read:
            notification.read_at = datetime.now(UTC).replace(tzinfo=None)

        db_session.add(notification)
        notifications.append(notification)

    await db_session.commit()
    return notifications
