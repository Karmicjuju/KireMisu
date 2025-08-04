"""Integration tests for mark-read workflow end-to-end functionality."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from kiremisu.database.models import Chapter, Series


class TestMarkReadWorkflowIntegration:
    """Integration tests for complete mark-read workflow."""

    @pytest.fixture
    async def test_series_with_chapters(self, db_session: AsyncSession):
        """Create a test series with multiple chapters for workflow testing."""
        series = Series(
            id=uuid4(),
            title_primary="Workflow Test Series",
            language="en",
            file_path="/test/workflow_series",
            total_chapters=10,
            read_chapters=0,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        # Create 10 chapters
        chapters = []
        for i in range(1, 11):
            chapter = Chapter(
                id=uuid4(),
                series_id=series.id,
                chapter_number=float(i),
                volume_number=(i - 1) // 5 + 1,  # Volume 1: ch 1-5, Volume 2: ch 6-10
                title=f"Chapter {i}: Test Chapter",
                file_path=f"/test/workflow_series/chapter_{i:03d}.cbz",
                file_size=1024 * i,
                page_count=20 + (i % 3),  # Vary page counts: 20, 21, 22
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
    async def test_complete_series_reading_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test complete workflow of reading an entire series."""
        series = test_series_with_chapters["series"]
        chapters = test_series_with_chapters["chapters"]

        # Initial state: no chapters read
        response = await client.get(f"/api/series/{series.id}/progress")
        assert response.status_code == 200
        initial_progress = response.json()

        assert initial_progress["series"]["read_chapters"] == 0
        assert initial_progress["progress_percentage"] == 0.0
        assert all(not ch["is_read"] for ch in initial_progress["chapters"])

        # Mark chapters as read one by one and verify progress updates
        for i, chapter in enumerate(chapters):
            # Mark chapter as read
            mark_response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
            assert mark_response.status_code == 200

            mark_data = mark_response.json()
            assert mark_data["is_read"] is True
            assert mark_data["read_at"] is not None

            # Check series progress after each chapter
            progress_response = await client.get(f"/api/series/{series.id}/progress")
            assert progress_response.status_code == 200

            progress_data = progress_response.json()
            expected_read_count = i + 1
            expected_progress = (expected_read_count / 10) * 100

            assert progress_data["series"]["read_chapters"] == expected_read_count
            assert progress_data["progress_percentage"] == expected_progress

            # Verify individual chapter states
            chapter_states = {ch["id"]: ch for ch in progress_data["chapters"]}
            for j, ch in enumerate(chapters):
                expected_read = j <= i
                assert chapter_states[str(ch.id)]["is_read"] == expected_read

        # Final state: all chapters read
        final_response = await client.get(f"/api/series/{series.id}/progress")
        final_data = final_response.json()

        assert final_data["series"]["read_chapters"] == 10
        assert final_data["progress_percentage"] == 100.0
        assert all(ch["is_read"] for ch in final_data["chapters"])

    @pytest.mark.asyncio
    async def test_partial_reading_with_unreading_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test workflow of partially reading, then unreading some chapters."""
        series = test_series_with_chapters["series"]
        chapters = test_series_with_chapters["chapters"]

        # Read first 5 chapters
        for i in range(5):
            response = await client.put(f"/api/chapters/{chapters[i].id}/mark-read")
            assert response.status_code == 200

        # Verify intermediate progress
        response = await client.get(f"/api/series/{series.id}/progress")
        data = response.json()
        assert data["series"]["read_chapters"] == 5
        assert data["progress_percentage"] == 50.0

        # Unread chapters 2 and 4 (index 1 and 3)
        for i in [1, 3]:
            response = await client.put(f"/api/chapters/{chapters[i].id}/mark-read")
            assert response.status_code == 200

            unread_data = response.json()
            assert unread_data["is_read"] is False
            assert unread_data["read_at"] is None

        # Verify updated progress
        response = await client.get(f"/api/series/{series.id}/progress")
        data = response.json()
        assert data["series"]["read_chapters"] == 3  # Chapters 1, 3, 5 (0-indexed: 0, 2, 4)
        assert data["progress_percentage"] == 30.0

        # Verify specific chapter states
        chapter_states = {ch["id"]: ch for ch in data["chapters"]}
        expected_read_chapters = [0, 2, 4]  # 0-indexed

        for i, chapter in enumerate(chapters):
            expected_read = i in expected_read_chapters
            assert chapter_states[str(chapter.id)]["is_read"] == expected_read

    @pytest.mark.asyncio
    async def test_dashboard_stats_update_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test that dashboard stats update correctly during reading workflow."""
        series = test_series_with_chapters["series"]
        chapters = test_series_with_chapters["chapters"]

        # Create additional series for more comprehensive stats
        series2 = Series(
            id=uuid4(),
            title_primary="Completed Series",
            language="en",
            file_path="/test/completed_series",
            total_chapters=3,
            read_chapters=3,
        )
        db_session.add(series2)

        # Add completed chapters
        for i in range(1, 4):
            chapter = Chapter(
                id=uuid4(),
                series_id=series2.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Completed Chapter {i}",
                file_path=f"/test/completed_series/chapter_{i}.cbz",
                file_size=1024,
                page_count=20,
                is_read=True,
                last_read_page=19,
                read_at=datetime.utcnow() - timedelta(days=i),
            )
            db_session.add(chapter)

        await db_session.commit()

        # Initial dashboard stats
        stats_response = await client.get("/api/dashboard/stats")
        assert stats_response.status_code == 200
        initial_stats = stats_response.json()

        assert initial_stats["total_series"] == 2
        assert initial_stats["total_chapters"] == 13  # 10 + 3
        assert initial_stats["read_chapters"] == 3
        assert initial_stats["series_stats"]["completed"] == 1
        assert initial_stats["series_stats"]["in_progress"] == 0
        assert initial_stats["series_stats"]["unread"] == 1

        # Start reading the first series - read 5 chapters
        for i in range(5):
            await client.put(f"/api/chapters/{chapters[i].id}/mark-read")

        # Check updated dashboard stats
        stats_response = await client.get("/api/dashboard/stats")
        mid_stats = stats_response.json()

        assert mid_stats["total_chapters"] == 13
        assert mid_stats["read_chapters"] == 8  # 3 + 5
        assert mid_stats["overall_progress_percentage"] == (8 / 13) * 100
        assert mid_stats["series_stats"]["completed"] == 1
        assert mid_stats["series_stats"]["in_progress"] == 1  # First series now in progress
        assert mid_stats["series_stats"]["unread"] == 0

        # Complete the first series
        for i in range(5, 10):
            await client.put(f"/api/chapters/{chapters[i].id}/mark-read")

        # Check final dashboard stats
        stats_response = await client.get("/api/dashboard/stats")
        final_stats = stats_response.json()

        assert final_stats["read_chapters"] == 13
        assert final_stats["overall_progress_percentage"] == 100.0
        assert final_stats["series_stats"]["completed"] == 2
        assert final_stats["series_stats"]["in_progress"] == 0
        assert final_stats["series_stats"]["unread"] == 0

    @pytest.mark.asyncio
    async def test_reading_progress_persistence_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test that reading progress persists correctly through the workflow."""
        chapters = test_series_with_chapters["chapters"]
        first_chapter = chapters[0]

        # Mark chapter as read
        mark_response = await client.put(f"/api/chapters/{first_chapter.id}/mark-read")
        assert mark_response.status_code == 200

        read_time_str = mark_response.json()["read_at"]
        assert read_time_str is not None

        # Verify persistence by checking database directly
        result = await db_session.execute(select(Chapter).where(Chapter.id == first_chapter.id))
        db_chapter = result.scalar_one()

        assert db_chapter.is_read is True
        assert db_chapter.read_at is not None
        assert db_chapter.last_read_page == db_chapter.page_count - 1

        # Verify persistence through API calls
        chapter_response = await client.get(f"/api/chapters/{first_chapter.id}")
        chapter_data = chapter_response.json()

        assert chapter_data["is_read"] is True
        assert chapter_data["read_at"] == read_time_str
        assert chapter_data["last_read_page"] == chapter_data["page_count"] - 1

        # Mark as unread and verify persistence
        unmark_response = await client.put(f"/api/chapters/{first_chapter.id}/mark-read")
        assert unmark_response.status_code == 200

        unread_data = unmark_response.json()
        assert unread_data["is_read"] is False
        assert unread_data["read_at"] is None

        # Verify unread persistence
        result = await db_session.execute(select(Chapter).where(Chapter.id == first_chapter.id))
        db_chapter = result.scalar_one()

        assert db_chapter.is_read is False
        assert db_chapter.read_at is None
        assert db_chapter.last_read_page == 0

    @pytest.mark.asyncio
    async def test_concurrent_reading_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test workflow with concurrent reading of multiple chapters."""
        import asyncio

        series = test_series_with_chapters["series"]
        chapters = test_series_with_chapters["chapters"]

        # Concurrently mark first 5 chapters as read
        mark_tasks = [client.put(f"/api/chapters/{chapters[i].id}/mark-read") for i in range(5)]

        responses = await asyncio.gather(*mark_tasks)

        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["is_read"] is True

        # Verify final consistency
        progress_response = await client.get(f"/api/series/{series.id}/progress")
        progress_data = progress_response.json()

        assert progress_data["series"]["read_chapters"] == 5
        assert progress_data["progress_percentage"] == 50.0

        # Verify database consistency
        result = await db_session.execute(
            select(func.count(Chapter.id)).where(
                Chapter.series_id == series.id, Chapter.is_read == True
            )
        )
        actual_read_count = result.scalar()
        assert actual_read_count == 5

        # Verify series counter consistency
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        updated_series = result.scalar_one()
        assert updated_series.read_chapters == 5

    @pytest.mark.asyncio
    async def test_mixed_volume_reading_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test reading workflow across different volumes."""
        series = test_series_with_chapters["series"]
        chapters = test_series_with_chapters["chapters"]

        # Read all chapters from volume 1 (chapters 1-5, index 0-4)
        volume1_chapters = chapters[:5]
        for chapter in volume1_chapters:
            response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
            assert response.status_code == 200

        # Read only first 2 chapters from volume 2 (chapters 6-7, index 5-6)
        volume2_partial = chapters[5:7]
        for chapter in volume2_partial:
            response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
            assert response.status_code == 200

        # Verify progress
        progress_response = await client.get(f"/api/series/{series.id}/progress")
        progress_data = progress_response.json()

        assert progress_data["series"]["read_chapters"] == 7
        assert progress_data["progress_percentage"] == 70.0

        # Verify volume-specific progress
        chapters_by_volume = {}
        for ch in progress_data["chapters"]:
            vol = ch["volume_number"]
            if vol not in chapters_by_volume:
                chapters_by_volume[vol] = []
            chapters_by_volume[vol].append(ch)

        # Volume 1 should be complete
        vol1_chapters = chapters_by_volume[1]
        assert len(vol1_chapters) == 5
        assert all(ch["is_read"] for ch in vol1_chapters)

        # Volume 2 should be partial
        vol2_chapters = chapters_by_volume[2]
        assert len(vol2_chapters) == 5
        read_vol2 = sum(1 for ch in vol2_chapters if ch["is_read"])
        assert read_vol2 == 2

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test workflow recovery from errors."""
        chapters = test_series_with_chapters["chapters"]
        valid_chapter = chapters[0]

        # Test with invalid chapter ID
        invalid_response = await client.put(f"/api/chapters/{uuid4()}/mark-read")
        assert invalid_response.status_code == 404

        # Test that valid operations still work after error
        valid_response = await client.put(f"/api/chapters/{valid_chapter.id}/mark-read")
        assert valid_response.status_code == 200
        assert valid_response.json()["is_read"] is True

        # Test with malformed chapter ID
        malformed_response = await client.put("/api/chapters/invalid-uuid/mark-read")
        assert malformed_response.status_code == 422

        # Verify valid operations continue to work
        unread_response = await client.put(f"/api/chapters/{valid_chapter.id}/mark-read")
        assert unread_response.status_code == 200
        assert unread_response.json()["is_read"] is False

    @pytest.mark.asyncio
    async def test_progress_calculation_edge_cases_workflow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test workflow with edge cases in progress calculation."""
        # Create series with single chapter
        single_chapter_series = Series(
            id=uuid4(),
            title_primary="Single Chapter Series",
            language="en",
            file_path="/test/single",
            total_chapters=1,
            read_chapters=0,
        )
        db_session.add(single_chapter_series)

        single_chapter = Chapter(
            id=uuid4(),
            series_id=single_chapter_series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Only Chapter",
            file_path="/test/single/chapter_1.cbz",
            file_size=1024,
            page_count=1,  # Single page
            is_read=False,
            last_read_page=0,
        )
        db_session.add(single_chapter)
        await db_session.commit()

        # Test single chapter progress
        progress_response = await client.get(f"/api/series/{single_chapter_series.id}/progress")
        initial_data = progress_response.json()
        assert initial_data["progress_percentage"] == 0.0

        # Mark single chapter as read
        mark_response = await client.put(f"/api/chapters/{single_chapter.id}/mark-read")
        assert mark_response.status_code == 200

        # Verify 100% completion
        progress_response = await client.get(f"/api/series/{single_chapter_series.id}/progress")
        final_data = progress_response.json()
        assert final_data["progress_percentage"] == 100.0
        assert final_data["series"]["read_chapters"] == 1

        # Create series with zero chapters (edge case)
        empty_series = Series(
            id=uuid4(),
            title_primary="Empty Series",
            language="en",
            file_path="/test/empty",
            total_chapters=0,
            read_chapters=0,
        )
        db_session.add(empty_series)
        await db_session.commit()

        # Test empty series progress
        empty_response = await client.get(f"/api/series/{empty_series.id}/progress")
        assert empty_response.status_code == 200
        empty_data = empty_response.json()
        assert empty_data["progress_percentage"] == 0.0
        assert empty_data["series"]["read_chapters"] == 0
        assert len(empty_data["chapters"]) == 0
