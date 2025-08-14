"""Extended reader API tests covering progress update flows and integration."""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Series


class TestReaderProgressIntegration:
    """Test reader API integration with progress tracking functionality."""

    @pytest.fixture
    async def test_series_with_chapters(self, db_session: AsyncSession):
        """Create a test series with chapters for reader progress testing."""
        series = Series(
            id=uuid4(),
            title_primary="Reader Progress Test Series",
            language="en",
            file_path="/test/reader_progress_series",
            total_chapters=5,
            read_chapters=0,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        chapters = []
        for i in range(1, 6):
            chapter = Chapter(
                id=uuid4(),
                series_id=series.id,
                chapter_number=float(i),
                volume_number=1,
                title=f"Reader Test Chapter {i}",
                file_path=f"/test/reader_progress_series/chapter_{i:03d}.cbz",
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
    async def test_reader_chapter_info_includes_progress(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test that reader chapter info endpoint includes progress information."""
        chapter = test_series_with_chapters["chapters"][0]
        series = test_series_with_chapters["series"]

        response = await client.get(f"/api/reader/chapter/{chapter.id}/info")

        assert response.status_code == 200
        data = response.json()

        # Verify chapter information includes progress fields
        assert data["id"] == str(chapter.id)
        assert data["series_id"] == str(series.id)
        assert data["series_title"] == series.title_primary
        assert data["page_count"] == chapter.page_count

        # Verify progress information
        assert "is_read" in data
        assert "last_read_page" in data
        assert "read_at" in data

        # Initial state should be unread
        assert data["is_read"] is False
        assert data["last_read_page"] == 0
        assert data["read_at"] is None

    @pytest.mark.asyncio
    async def test_reader_progress_update_integration(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test reader progress update integration with mark-read functionality."""
        chapter = test_series_with_chapters["chapters"][0]
        series = test_series_with_chapters["series"]

        # Update reading progress through reader API
        progress_update = {"last_read_page": 10, "is_read": False}

        progress_response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=progress_update
        )

        assert progress_response.status_code == 200
        progress_data = progress_response.json()

        assert progress_data["last_read_page"] == 10
        assert progress_data["is_read"] is False

        # Now mark as read using mark-read API
        mark_read_response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
        assert mark_read_response.status_code == 200
        mark_data = mark_read_response.json()

        assert mark_data["is_read"] is True
        assert mark_data["last_read_page"] == 19  # Should be set to last page when marked read

        # Verify series progress updated
        series_response = await client.get(f"/api/series/{series.id}/progress")
        series_data = series_response.json()
        assert series_data["series"]["read_chapters"] == 1

    @pytest.mark.asyncio
    async def test_reader_progress_preserves_higher_page_progress(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test that marking as read preserves higher page progress."""
        chapter = test_series_with_chapters["chapters"][0]

        # Set progress to page 15
        progress_update = {"last_read_page": 15, "is_read": False}

        await client.put(f"/api/reader/chapter/{chapter.id}/progress", json=progress_update)

        # Mark as read - should preserve higher progress
        mark_response = await client.put(f"/api/chapters/{chapter.id}/mark-read")
        assert mark_response.status_code == 200

        mark_data = mark_response.json()
        assert mark_data["is_read"] is True
        assert mark_data["last_read_page"] == 19  # Set to completion

    @pytest.mark.asyncio
    async def test_reader_series_chapters_with_progress_integration(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test reader series chapters endpoint integration with progress."""
        series = test_series_with_chapters["series"]
        chapters = test_series_with_chapters["chapters"]

        # Set different progress states for different chapters
        # Chapter 1: Complete
        await client.put(f"/api/chapters/{chapters[0].id}/mark-read")

        # Chapter 2: Partial progress
        await client.put(
            f"/api/reader/chapter/{chapters[1].id}/progress",
            json={"last_read_page": 10, "is_read": False},
        )

        # Chapter 3: Unread (default state)

        # Get series chapters through reader API
        response = await client.get(f"/api/reader/series/{series.id}/chapters")

        assert response.status_code == 200
        data = response.json()

        # Check series information
        assert data["series"]["id"] == str(series.id)
        assert data["series"]["title"] == series.title_primary
        assert data["series"]["read_chapters"] == 1

        # Check individual chapter progress
        chapters_data = {ch["id"]: ch for ch in data["chapters"]}

        # Chapter 1: Should be read
        ch1_data = chapters_data[str(chapters[0].id)]
        assert ch1_data["is_read"] is True
        assert ch1_data["last_read_page"] == 19

        # Chapter 2: Should have partial progress
        ch2_data = chapters_data[str(chapters[1].id)]
        assert ch2_data["is_read"] is False
        assert ch2_data["last_read_page"] == 10

        # Chapter 3: Should be unread
        ch3_data = chapters_data[str(chapters[2].id)]
        assert ch3_data["is_read"] is False
        assert ch3_data["last_read_page"] == 0

    @pytest.mark.asyncio
    async def test_reader_progress_validation_edge_cases(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test reader progress update validation with edge cases."""
        chapter = test_series_with_chapters["chapters"][0]

        # Test invalid page number (too high)
        invalid_update = {
            "last_read_page": 50,  # Chapter only has 20 pages
            "is_read": False,
        }

        response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=invalid_update
        )

        assert response.status_code == 400
        assert "Invalid page number" in response.json()["detail"]

        # Test invalid page number (negative)
        negative_update = {"last_read_page": -1, "is_read": False}

        response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=negative_update
        )

        assert response.status_code == 422  # Validation error

        # Test valid edge case (last page)
        last_page_update = {
            "last_read_page": 19,  # Last page (0-indexed)
            "is_read": True,
        }

        response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=last_page_update
        )

        assert response.status_code == 200
        data = response.json()
        assert data["last_read_page"] == 19
        assert data["is_read"] is True

    @pytest.mark.asyncio
    async def test_reader_progress_automatic_read_completion(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test automatic read completion when reaching last page."""
        chapter = test_series_with_chapters["chapters"][0]

        # Progress to last page without explicitly marking as read
        progress_update = {
            "last_read_page": 19,  # Last page (0-indexed)
            "is_read": None,  # Let system decide
        }

        response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=progress_update
        )

        assert response.status_code == 200
        data = response.json()

        # Should automatically be marked as read
        assert data["is_read"] is True
        assert data["read_at"] is not None

    @pytest.mark.asyncio
    async def test_concurrent_reader_and_mark_read_operations(
        self, client: AsyncClient, test_series_with_chapters: dict, db_session: AsyncSession
    ):
        """Test concurrent operations between reader progress and mark-read APIs."""
        import asyncio

        chapter = test_series_with_chapters["chapters"][0]
        series = test_series_with_chapters["series"]

        async def update_reader_progress():
            """Update progress through reader API."""
            return await client.put(
                f"/api/reader/chapter/{chapter.id}/progress",
                json={"last_read_page": 15, "is_read": False},
            )

        async def mark_chapter_read():
            """Mark chapter read through mark-read API."""
            return await client.put(f"/api/chapters/{chapter.id}/mark-read")

        # Execute concurrent operations
        reader_response, mark_response = await asyncio.gather(
            update_reader_progress(), mark_chapter_read()
        )

        # Both operations should succeed
        assert reader_response.status_code == 200
        assert mark_response.status_code == 200

        # Verify final state consistency
        final_response = await client.get(f"/api/reader/chapter/{chapter.id}/info")
        final_data = final_response.json()

        # Chapter should be marked as read (mark-read takes precedence)
        assert final_data["is_read"] is True

        # Verify database consistency
        result = await db_session.execute(select(Chapter).where(Chapter.id == chapter.id))
        db_chapter = result.scalar_one()
        assert db_chapter.is_read is True

        # Verify series counter updated
        result = await db_session.execute(select(Series).where(Series.id == series.id))
        db_series = result.scalar_one()
        assert db_series.read_chapters == 1

    @pytest.mark.asyncio
    async def test_reader_progress_with_chapter_navigation(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test reader progress updates during chapter navigation."""
        chapters = test_series_with_chapters["chapters"]
        series = test_series_with_chapters["series"]

        # Simulate reading through multiple chapters
        for i, chapter in enumerate(chapters[:3]):  # Read first 3 chapters
            # Progress through chapter partially first
            mid_progress = {"last_read_page": 10, "is_read": False}

            progress_response = await client.put(
                f"/api/reader/chapter/{chapter.id}/progress", json=mid_progress
            )
            assert progress_response.status_code == 200

            # Complete the chapter
            complete_progress = {"last_read_page": 19, "is_read": True}

            complete_response = await client.put(
                f"/api/reader/chapter/{chapter.id}/progress", json=complete_progress
            )
            assert complete_response.status_code == 200

            # Verify series progress updated after each chapter
            series_response = await client.get(f"/api/series/{series.id}/progress")
            series_data = series_response.json()
            assert series_data["series"]["read_chapters"] == i + 1

        # Final verification
        final_series_response = await client.get(f"/api/reader/series/{series.id}/chapters")
        final_data = final_series_response.json()

        assert final_data["series"]["read_chapters"] == 3

        # Check individual chapter states
        for i in range(3):
            chapter_data = next(
                ch for ch in final_data["chapters"] if ch["id"] == str(chapters[i].id)
            )
            assert chapter_data["is_read"] is True
            assert chapter_data["last_read_page"] == 19

    @pytest.mark.asyncio
    async def test_reader_error_handling_with_progress_integration(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test error handling in reader API with progress integration."""
        chapter = test_series_with_chapters["chapters"][0]

        # Test progress update for non-existent chapter
        fake_chapter_id = uuid4()
        response = await client.put(
            f"/api/reader/chapter/{fake_chapter_id}/progress",
            json={"last_read_page": 5, "is_read": False},
        )

        assert response.status_code == 404
        assert "Chapter not found" in response.json()["detail"]

        # Test chapter info for non-existent chapter
        info_response = await client.get(f"/api/reader/chapter/{fake_chapter_id}/info")
        assert info_response.status_code == 404

        # Test series chapters for non-existent series
        fake_series_id = uuid4()
        series_response = await client.get(f"/api/reader/series/{fake_series_id}/chapters")
        assert series_response.status_code == 404

        # Verify valid operations still work after errors
        valid_response = await client.get(f"/api/reader/chapter/{chapter.id}/info")
        assert valid_response.status_code == 200

    @pytest.mark.asyncio
    async def test_reader_progress_timestamp_consistency(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test timestamp consistency across reader and mark-read APIs."""
        chapter = test_series_with_chapters["chapters"][0]

        # Mark chapter as read through reader API
        progress_update = {"last_read_page": 19, "is_read": True}

        reader_response = await client.put(
            f"/api/reader/chapter/{chapter.id}/progress", json=progress_update
        )

        assert reader_response.status_code == 200
        reader_data = reader_response.json()
        reader_timestamp = reader_data["read_at"]

        # Get chapter info through different APIs
        info_response = await client.get(f"/api/reader/chapter/{chapter.id}/info")
        info_data = info_response.json()

        chapter_response = await client.get(f"/api/chapters/{chapter.id}")
        chapter_data = chapter_response.json()

        # Timestamps should be consistent across APIs
        assert info_data["read_at"] == reader_timestamp
        assert chapter_data["read_at"] == reader_timestamp

        # Timestamp should be recent
        read_time = datetime.fromisoformat(reader_timestamp.replace("Z", "+00:00"))
        time_diff = datetime.utcnow().replace(tzinfo=read_time.tzinfo) - read_time
        assert time_diff.total_seconds() < 60  # Within last minute

    @pytest.mark.asyncio
    async def test_reader_batch_progress_tracking(
        self, client: AsyncClient, test_series_with_chapters: dict
    ):
        """Test batch progress tracking through reader API workflow."""
        chapters = test_series_with_chapters["chapters"]
        series = test_series_with_chapters["series"]

        # Simulate a reading session with multiple chapters
        reading_session = [
            {"chapter_idx": 0, "final_page": 19, "is_read": True},
            {"chapter_idx": 1, "final_page": 15, "is_read": False},
            {"chapter_idx": 2, "final_page": 8, "is_read": False},
        ]

        for session in reading_session:
            chapter = chapters[session["chapter_idx"]]

            # Update progress
            progress_update = {
                "last_read_page": session["final_page"],
                "is_read": session["is_read"],
            }

            response = await client.put(
                f"/api/reader/chapter/{chapter.id}/progress", json=progress_update
            )

            assert response.status_code == 200

        # Verify final state through series endpoint
        series_response = await client.get(f"/api/reader/series/{series.id}/chapters")
        series_data = series_response.json()

        # Should have 1 read chapter
        assert series_data["series"]["read_chapters"] == 1

        # Verify individual progress
        chapters_data = {ch["id"]: ch for ch in series_data["chapters"]}

        for session in reading_session:
            chapter = chapters[session["chapter_idx"]]
            chapter_data = chapters_data[str(chapter.id)]

            assert chapter_data["is_read"] == session["is_read"]
            assert chapter_data["last_read_page"] == session["final_page"]
