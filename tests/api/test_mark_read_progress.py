"""Tests for mark-read functionality and progress tracking API endpoints."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Series


class TestMarkReadAPI:
    """Test cases for mark-read API endpoints."""

    @pytest.fixture
    async def test_series_with_chapters(self, db_session: AsyncSession):
        """Create a test series with multiple chapters."""
        series = Series(
            id=uuid4(),
            title_primary="Test Series",
            language="en",
            file_path="/test/series",
            total_chapters=5,
            read_chapters=0,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        # Create 5 chapters
        chapters = []
        for i in range(1, 6):
            chapter = Chapter(
                id=uuid4(),
                series_id=series.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Chapter {i}",
                file_path=f"/test/chapter_{i}.cbz",
                file_size=1024 * i,
                page_count=20,
                is_read=False,
                last_read_page=0,
            )
            chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()
        for chapter in chapters:
            await db_session.refresh(chapter)

        return {"series": series, "chapters": chapters}

    @pytest.mark.asyncio
    async def test_mark_chapter_read_success(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test successfully marking a chapter as read."""
        chapter = test_series_with_chapters["chapters"][0]
        series = test_series_with_chapters["series"]

        # Mark chapter as read
        response = await client.put(f"/api/chapters/{chapter.id}/mark-read")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["id"] == str(chapter.id)
        assert data["is_read"] is True
        assert data["read_at"] is not None

        # Verify database was updated
        result = await db_session.execute(select(Chapter).where(Chapter.id == chapter.id))
        updated_chapter = result.scalar_one()

        assert updated_chapter.is_read is True
        assert updated_chapter.read_at is not None
        assert updated_chapter.last_read_page == updated_chapter.page_count - 1

        # Verify series read_chapters counter was updated
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        updated_series = result.scalar_one()
        assert updated_series.read_chapters == 1

    @pytest.mark.asyncio
    async def test_mark_chapter_unread_success(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test successfully marking a read chapter as unread."""
        chapter = test_series_with_chapters["chapters"][0]
        series = test_series_with_chapters["series"]

        # First mark chapter as read
        chapter.is_read = True
        chapter.read_at = datetime.utcnow()
        chapter.last_read_page = chapter.page_count - 1

        # Update series counter
        series.read_chapters = 1

        await db_session.commit()

        # Now mark as unread
        response = await client.put(f"/api/chapters/{chapter.id}/mark-read")

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["id"] == str(chapter.id)
        assert data["is_read"] is False
        assert data["read_at"] is None

        # Verify database was updated
        result = await db_session.execute(select(Chapter).where(Chapter.id == chapter.id))
        updated_chapter = result.scalar_one()

        assert updated_chapter.is_read is False
        assert updated_chapter.read_at is None
        assert updated_chapter.last_read_page == 0

        # Verify series read_chapters counter was decremented
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        updated_series = result.scalar_one()
        assert updated_series.read_chapters == 0

    @pytest.mark.asyncio
    async def test_mark_read_chapter_not_found(self, client: AsyncClient):
        """Test mark-read for non-existent chapter."""
        fake_id = uuid4()
        response = await client.put(f"/api/chapters/{fake_id}/mark-read")

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_mark_read_invalid_chapter_id(self, client: AsyncClient):
        """Test mark-read with invalid chapter ID format."""
        response = await client.put("/api/chapters/invalid-uuid/mark-read")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_bulk_mark_read_series_progress_update(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test that marking multiple chapters updates series progress correctly."""
        chapters = test_series_with_chapters["chapters"]
        series = test_series_with_chapters["series"]

        # Mark first 3 chapters as read
        for i in range(3):
            response = await client.put(f"/api/chapters/{chapters[i].id}/mark-read")
            assert response.status_code == 200

        # Verify series progress
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        updated_series = result.scalar_one()
        assert updated_series.read_chapters == 3

    @pytest.mark.asyncio
    async def test_mark_read_preserves_existing_progress(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test that marking as read preserves existing reading progress."""
        chapter = test_series_with_chapters["chapters"][0]

        # Set some initial progress
        chapter.last_read_page = 10
        await db_session.commit()

        # Mark as read
        response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
        assert response.status_code == 200

        # Verify progress was updated to completion but preserved if higher
        result = await db_session.execute(select(Chapter).where(Chapter.id == chapter.id))
        updated_chapter = result.scalar_one()

        assert updated_chapter.is_read is True
        assert updated_chapter.last_read_page == updated_chapter.page_count - 1


class TestSeriesProgressAPI:
    """Test cases for series progress API endpoints."""

    @pytest.fixture
    async def test_series_with_mixed_progress(self, db_session: AsyncSession):
        """Create a series with chapters in various read states."""
        series = Series(
            id=uuid4(),
            title_primary="Mixed Progress Series",
            language="en",
            file_path="/test/mixed_series",
            total_chapters=4,
            read_chapters=2,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        # Create chapters with different read states
        chapters = []

        # Chapter 1: Fully read
        chapter1 = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Chapter 1",
            file_path="/test/chapter_1.cbz",
            file_size=1024,
            page_count=20,
            is_read=True,
            last_read_page=19,
            read_at=datetime.utcnow() - timedelta(days=2),
        )
        chapters.append(chapter1)

        # Chapter 2: Partially read
        chapter2 = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=2.0,
            volume_number=1,
            title="Chapter 2",
            file_path="/test/chapter_2.cbz",
            file_size=1024,
            page_count=20,
            is_read=False,
            last_read_page=10,
        )
        chapters.append(chapter2)

        # Chapter 3: Fully read
        chapter3 = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=3.0,
            volume_number=1,
            title="Chapter 3",
            file_path="/test/chapter_3.cbz",
            file_size=1024,
            page_count=20,
            is_read=True,
            last_read_page=19,
            read_at=datetime.utcnow() - timedelta(days=1),
        )
        chapters.append(chapter3)

        # Chapter 4: Unread
        chapter4 = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=4.0,
            volume_number=1,
            title="Chapter 4",
            file_path="/test/chapter_4.cbz",
            file_size=1024,
            page_count=20,
            is_read=False,
            last_read_page=0,
        )
        chapters.append(chapter4)

        for chapter in chapters:
            db_session.add(chapter)

        await db_session.commit()
        for chapter in chapters:
            await db_session.refresh(chapter)

        return {"series": series, "chapters": chapters}

    @pytest.mark.asyncio
    async def test_get_series_progress_success(
        self, client: AsyncClient, test_series_with_mixed_progress: dict
    ):
        """Test successful series progress retrieval."""
        series = test_series_with_mixed_progress["series"]
        test_series_with_mixed_progress["chapters"]

        response = await client.get(f"/api/series/{series.id}/progress")

        assert response.status_code == 200
        data = response.json()

        # Verify series information
        assert data["series"]["id"] == str(series.id)
        assert data["series"]["title"] == series.title_primary
        assert data["series"]["total_chapters"] == 4
        assert data["series"]["read_chapters"] == 2

        # Verify progress calculation
        assert data["progress_percentage"] == 50.0  # 2/4 chapters read

        # Verify chapter details
        assert len(data["chapters"]) == 4

        # Check specific chapter states
        chapter_data = {ch["chapter_number"]: ch for ch in data["chapters"]}

        # Chapter 1: fully read
        assert chapter_data[1.0]["is_read"] is True
        assert chapter_data[1.0]["progress_percentage"] == 100.0

        # Chapter 2: partially read
        assert chapter_data[2.0]["is_read"] is False
        assert chapter_data[2.0]["progress_percentage"] == 55.0  # 11/20 pages (0-indexed)

        # Chapter 3: fully read
        assert chapter_data[3.0]["is_read"] is True
        assert chapter_data[3.0]["progress_percentage"] == 100.0

        # Chapter 4: unread
        assert chapter_data[4.0]["is_read"] is False
        assert chapter_data[4.0]["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_get_series_progress_not_found(self, client: AsyncClient):
        """Test series progress for non-existent series."""
        fake_id = uuid4()
        response = await client.get(f"/api/series/{fake_id}/progress")

        assert response.status_code == 404
        assert "Series not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_series_progress_no_chapters(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test series progress for series with no chapters."""
        series = Series(
            id=uuid4(),
            title_primary="Empty Series",
            language="en",
            file_path="/test/empty_series",
            total_chapters=0,
            read_chapters=0,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        response = await client.get(f"/api/series/{series.id}/progress")

        assert response.status_code == 200
        data = response.json()

        assert data["series"]["total_chapters"] == 0
        assert data["series"]["read_chapters"] == 0
        assert data["progress_percentage"] == 0.0
        assert len(data["chapters"]) == 0


class TestDashboardStatsAPI:
    """Test cases for dashboard statistics API endpoints."""

    @pytest.fixture
    async def test_library_with_stats(self, db_session: AsyncSession):
        """Create a test library with various series and reading progress."""

        # Series 1: Fully read
        series1 = Series(
            id=uuid4(),
            title_primary="Completed Series",
            language="en",
            file_path="/test/completed",
            total_chapters=3,
            read_chapters=3,
        )
        db_session.add(series1)

        # Series 2: Partially read
        series2 = Series(
            id=uuid4(),
            title_primary="In Progress Series",
            language="en",
            file_path="/test/in_progress",
            total_chapters=5,
            read_chapters=2,
        )
        db_session.add(series2)

        # Series 3: Unread
        series3 = Series(
            id=uuid4(),
            title_primary="Unread Series",
            language="en",
            file_path="/test/unread",
            total_chapters=4,
            read_chapters=0,
        )
        db_session.add(series3)

        await db_session.commit()

        series_list = [series1, series2, series3]
        for series in series_list:
            await db_session.refresh(series)

        # Create chapters for each series
        all_chapters = []

        # Chapters for series 1 (all read)
        for i in range(1, 4):
            chapter = Chapter(
                id=uuid4(),
                series_id=series1.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Chapter {i}",
                file_path=f"/test/completed/chapter_{i}.cbz",
                file_size=1024,
                page_count=20,
                is_read=True,
                last_read_page=19,
                read_at=datetime.utcnow() - timedelta(days=i),
            )
            all_chapters.append(chapter)
            db_session.add(chapter)

        # Chapters for series 2 (2 read, 3 unread)
        for i in range(1, 6):
            chapter = Chapter(
                id=uuid4(),
                series_id=series2.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Chapter {i}",
                file_path=f"/test/in_progress/chapter_{i}.cbz",
                file_size=1024,
                page_count=20,
                is_read=(i <= 2),  # First 2 chapters read
                last_read_page=19 if i <= 2 else 0,
                read_at=datetime.utcnow() - timedelta(days=i) if i <= 2 else None,
            )
            all_chapters.append(chapter)
            db_session.add(chapter)

        # Chapters for series 3 (all unread)
        for i in range(1, 5):
            chapter = Chapter(
                id=uuid4(),
                series_id=series3.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Chapter {i}",
                file_path=f"/test/unread/chapter_{i}.cbz",
                file_size=1024,
                page_count=20,
                is_read=False,
                last_read_page=0,
            )
            all_chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()

        return {
            "series": series_list,
            "chapters": all_chapters,
            "expected_stats": {
                "total_series": 3,
                "total_chapters": 12,
                "read_chapters": 5,
                "completed_series": 1,
                "in_progress_series": 1,
                "unread_series": 1,
            },
        }

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_success(
        self, client: AsyncClient, test_library_with_stats: dict
    ):
        """Test successful dashboard statistics retrieval."""
        expected = test_library_with_stats["expected_stats"]

        response = await client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify overall statistics
        assert data["total_series"] == expected["total_series"]
        assert data["total_chapters"] == expected["total_chapters"]
        assert data["read_chapters"] == expected["read_chapters"]

        # Verify progress percentages
        assert data["overall_progress_percentage"] == (5 / 12) * 100  # 41.67%

        # Verify series breakdown
        assert data["series_stats"]["completed"] == expected["completed_series"]
        assert data["series_stats"]["in_progress"] == expected["in_progress_series"]
        assert data["series_stats"]["unread"] == expected["unread_series"]

        # Verify recent activity exists
        assert "recent_reads" in data
        assert len(data["recent_reads"]) > 0

        # Verify reading streak calculation
        assert "reading_streak_days" in data
        assert isinstance(data["reading_streak_days"], int)

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_empty_library(self, client: AsyncClient):
        """Test dashboard statistics for empty library."""
        response = await client.get("/api/dashboard/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify empty library statistics
        assert data["total_series"] == 0
        assert data["total_chapters"] == 0
        assert data["read_chapters"] == 0
        assert data["overall_progress_percentage"] == 0.0

        # Verify series breakdown
        assert data["series_stats"]["completed"] == 0
        assert data["series_stats"]["in_progress"] == 0
        assert data["series_stats"]["unread"] == 0

        # Verify empty recent activity
        assert data["recent_reads"] == []
        assert data["reading_streak_days"] == 0

    @pytest.mark.asyncio
    async def test_dashboard_stats_performance_large_library(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test dashboard statistics performance with a larger library."""
        # Create a larger test dataset
        series_count = 50
        chapters_per_series = 20

        for s in range(series_count):
            series = Series(
                id=uuid4(),
                title_primary=f"Series {s + 1}",
                language="en",
                file_path=f"/test/series_{s + 1}",
                total_chapters=chapters_per_series,
                read_chapters=s % 10,  # Vary read chapters
            )
            db_session.add(series)

            # Add chapters for each series
            for c in range(chapters_per_series):
                chapter = Chapter(
                    id=uuid4(),
                    series_id=series.id,
                    chapter_number=float(c + 1),
                    volume_number=1,
                    title=f"Chapter {c + 1}",
                    file_path=f"/test/series_{s + 1}/chapter_{c + 1}.cbz",
                    file_size=1024,
                    page_count=20,
                    is_read=(c < (s % 10)),  # Mark some chapters as read
                    last_read_page=19 if (c < (s % 10)) else 0,
                    read_at=datetime.utcnow() - timedelta(days=c) if (c < (s % 10)) else None,
                )
                db_session.add(chapter)

        await db_session.commit()

        # Time the API call (should complete quickly)
        import time

        start_time = time.time()

        response = await client.get("/api/dashboard/stats")

        end_time = time.time()
        execution_time = end_time - start_time

        assert response.status_code == 200
        assert execution_time < 2.0  # Should complete within 2 seconds

        data = response.json()
        assert data["total_series"] == series_count
        assert data["total_chapters"] == series_count * chapters_per_series


class TestProgressAggregationValidation:
    """Test cases for validating progress aggregation and database consistency."""

    @pytest.mark.asyncio
    async def test_series_read_chapters_consistency(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that series.read_chapters stays consistent with actual chapter read states."""
        # Create series with chapters
        series = Series(
            id=uuid4(),
            title_primary="Consistency Test Series",
            language="en",
            file_path="/test/consistency",
            total_chapters=3,
            read_chapters=0,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        chapters = []
        for i in range(1, 4):
            chapter = Chapter(
                id=uuid4(),
                series_id=series.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Chapter {i}",
                file_path=f"/test/consistency/chapter_{i}.cbz",
                file_size=1024,
                page_count=20,
                is_read=False,
                last_read_page=0,
            )
            chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()

        # Mark chapters as read one by one and verify consistency
        for i, chapter in enumerate(chapters):
            await client.put(f"/api/chapters/{chapter.id}/mark-read")

            # Verify database consistency
            result = await db_session.execute(select(Series).where(Series.id == series.id))
            updated_series = result.scalar_one()

            # Count actual read chapters
            result = await db_session.execute(
                select(func.count(Chapter.id)).where(
                    Chapter.series_id == series.id, Chapter.is_read
                )
            )
            actual_read_count = result.scalar()

            assert updated_series.read_chapters == actual_read_count == i + 1

    @pytest.mark.asyncio
    async def test_mark_read_idempotency(self, client: AsyncClient, db_session: AsyncSession):
        """Test that marking the same chapter as read multiple times is idempotent."""
        # Create test data
        series = Series(
            id=uuid4(),
            title_primary="Idempotency Test Series",
            language="en",
            file_path="/test/idempotency",
            total_chapters=1,
            read_chapters=0,
        )
        db_session.add(series)

        chapter = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Test Chapter",
            file_path="/test/idempotency/chapter_1.cbz",
            file_size=1024,
            page_count=20,
            is_read=False,
            last_read_page=0,
        )
        db_session.add(chapter)
        await db_session.commit()

        # Mark as read multiple times
        for _ in range(3):
            response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
            assert response.status_code == 200

        # Verify series counter is still correct
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        updated_series = result.scalar_one()
        assert updated_series.read_chapters == 1

    @pytest.mark.asyncio
    async def test_concurrent_mark_read_operations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test concurrent mark-read operations maintain data consistency."""
        import asyncio

        # Create test data
        series = Series(
            id=uuid4(),
            title_primary="Concurrent Test Series",
            language="en",
            file_path="/test/concurrent",
            total_chapters=5,
            read_chapters=0,
        )
        db_session.add(series)

        chapters = []
        for i in range(1, 6):
            chapter = Chapter(
                id=uuid4(),
                series_id=series.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Chapter {i}",
                file_path=f"/test/concurrent/chapter_{i}.cbz",
                file_size=1024,
                page_count=20,
                is_read=False,
                last_read_page=0,
            )
            chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()

        # Concurrently mark all chapters as read
        tasks = [client.put(f"/api/chapters/{chapter.id}/mark-read") for chapter in chapters]

        responses = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200

        # Verify final consistency
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        updated_series = result.scalar_one()
        assert updated_series.read_chapters == 5

        # Verify all chapters are marked as read
        result = await db_session.execute(
            select(func.count(Chapter.id)).where(
                Chapter.series_id == series.id, Chapter.is_read
            )
        )
        actual_read_count = result.scalar()
        assert actual_read_count == 5
