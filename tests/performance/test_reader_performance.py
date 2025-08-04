"""Performance tests for reader functionality."""

import asyncio
import time
import tempfile
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Series, Chapter
from tests.fixtures.reader_fixtures import create_test_cbz, create_large_chapter_files


@pytest.fixture
async def performance_test_series(db_session: AsyncSession):
    """Create a series with multiple chapters for performance testing."""
    series = Series(
        title_primary="Performance Test Series",
        file_path="/test/manga/performance_series",
        author="Performance Tester",
        total_chapters=10,
    )
    db_session.add(series)
    await db_session.flush()

    chapters = []
    for i in range(10):
        chapter = Chapter(
            series_id=series.id,
            chapter_number=float(i + 1),
            volume_number=1,
            title=f"Performance Chapter {i + 1}",
            file_path=f"/test/manga/performance_series/chapter_{i + 1:03d}.cbz",
            file_size=1024000,
            page_count=20,
            is_read=False,
            last_read_page=0,
        )
        chapters.append(chapter)
        db_session.add(chapter)

    await db_session.commit()

    for chapter in chapters:
        await db_session.refresh(chapter)

    return series, chapters


@pytest.fixture
async def large_chapter(db_session: AsyncSession):
    """Create a chapter with many pages for performance testing."""
    series = Series(
        title_primary="Large Chapter Series",
        file_path="/test/manga/large_series",
        total_chapters=1,
    )
    db_session.add(series)
    await db_session.flush()

    chapter = Chapter(
        series_id=series.id,
        chapter_number=1.0,
        volume_number=1,
        title="Large Chapter",
        file_path="/test/manga/large_series/large_chapter.cbz",
        file_size=50 * 1024 * 1024,  # 50MB
        page_count=100,  # 100 pages
        is_read=False,
        last_read_page=0,
    )
    db_session.add(chapter)
    await db_session.commit()
    await db_session.refresh(chapter)

    return chapter


class TestReaderPerformance:
    """Performance tests for reader API endpoints."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_page_requests_performance(
        self, client: AsyncClient, performance_test_series
    ):
        """Test performance of concurrent page requests."""
        _, chapters = performance_test_series
        chapter = chapters[0]

        # Mock file operations for consistent timing
        mock_image_data = b"x" * 1024  # 1KB mock image

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip_instance = mock_zip.return_value.__enter__.return_value
                mock_zip_instance.namelist.return_value = [f"page_{i:03d}.png" for i in range(20)]
                mock_zip_instance.read.return_value = mock_image_data

                # Test different concurrency levels
                concurrency_levels = [1, 5, 10, 20]
                results = {}

                for concurrency in concurrency_levels:
                    start_time = time.time()

                    # Create concurrent requests
                    tasks = [
                        client.get(f"/api/reader/chapter/{chapter.id}/page/{i % 20}")
                        for i in range(concurrency)
                    ]

                    responses = await asyncio.gather(*tasks)

                    end_time = time.time()
                    duration = end_time - start_time
                    results[concurrency] = duration

                    # All requests should succeed
                    for response in responses:
                        assert response.status_code == 200

                    print(
                        f"Concurrency {concurrency}: {duration:.3f}s, {concurrency / duration:.1f} req/s"
                    )

                # Performance should scale reasonably
                # Higher concurrency shouldn't be dramatically slower per request
                assert results[20] < results[1] * 10  # Should not be 10x slower

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_chapter_performance(self, client: AsyncClient, large_chapter: Chapter):
        """Test performance with large chapters."""
        # Mock large image data
        large_image_data = b"x" * 100 * 1024  # 100KB per page

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip_instance = mock_zip.return_value.__enter__.return_value
                mock_zip_instance.namelist.return_value = [f"page_{i:03d}.png" for i in range(100)]
                mock_zip_instance.read.return_value = large_image_data

                # Test accessing different pages in the large chapter
                page_indices = [0, 25, 50, 75, 99]  # First, middle, last pages

                total_start_time = time.time()

                for page_index in page_indices:
                    start_time = time.time()

                    response = await client.get(
                        f"/api/reader/chapter/{large_chapter.id}/page/{page_index}"
                    )

                    end_time = time.time()
                    duration = end_time - start_time

                    assert response.status_code == 200
                    assert len(response.content) == len(large_image_data)

                    # Each page should load in reasonable time
                    assert duration < 2.0, f"Page {page_index} took {duration:.3f}s (too slow)"

                    print(f"Page {page_index}: {duration:.3f}s")

                total_duration = time.time() - total_start_time
                print(f"Total time for 5 pages: {total_duration:.3f}s")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_progress_update_performance(self, client: AsyncClient, performance_test_series):
        """Test performance of rapid progress updates."""
        _, chapters = performance_test_series
        chapter = chapters[0]

        # Test rapid progress updates (simulating fast page turning)
        num_updates = 50
        start_time = time.time()

        for i in range(num_updates):
            progress_data = {"last_read_page": i % chapter.page_count}

            response = await client.put(
                f"/api/reader/chapter/{chapter.id}/progress", json=progress_data
            )

            assert response.status_code == 200

        end_time = time.time()
        duration = end_time - start_time
        updates_per_second = num_updates / duration

        print(f"Progress updates: {updates_per_second:.1f} updates/s")

        # Should handle at least 10 updates per second
        assert updates_per_second > 10

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_series_chapters_query_performance(
        self, client: AsyncClient, performance_test_series
    ):
        """Test performance of series chapters query."""
        series, chapters = performance_test_series

        # Test multiple requests to series chapters endpoint
        num_requests = 20
        start_time = time.time()

        for _ in range(num_requests):
            response = await client.get(f"/api/reader/series/{series.id}/chapters")

            assert response.status_code == 200
            data = response.json()
            assert len(data["chapters"]) == 10

        end_time = time.time()
        duration = end_time - start_time
        requests_per_second = num_requests / duration

        print(f"Series chapters queries: {requests_per_second:.1f} req/s")

        # Should handle at least 20 requests per second
        assert requests_per_second > 20

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_usage_large_pages(self, client: AsyncClient, large_chapter: Chapter):
        """Test memory usage with large page images."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Mock very large image data (10MB per page)
        very_large_image = b"x" * 10 * 1024 * 1024

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip_instance = mock_zip.return_value.__enter__.return_value
                mock_zip_instance.namelist.return_value = ["page_001.png"]
                mock_zip_instance.read.return_value = very_large_image

                # Request the same large page multiple times
                for i in range(10):
                    response = await client.get(f"/api/reader/chapter/{large_chapter.id}/page/0")
                    assert response.status_code == 200

                    # Force garbage collection
                    import gc

                    gc.collect()

                final_memory = process.memory_info().rss
                memory_increase = final_memory - initial_memory
                memory_increase_mb = memory_increase / (1024 * 1024)

                print(f"Memory increase: {memory_increase_mb:.1f} MB")

                # Memory increase should be reasonable (< 100MB for 10 requests)
                assert memory_increase_mb < 100

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_page_caching_performance(self, client: AsyncClient, performance_test_series):
        """Test page response caching headers."""
        _, chapters = performance_test_series
        chapter = chapters[0]

        mock_image_data = b"test_image_data"

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip_instance = mock_zip.return_value.__enter__.return_value
                mock_zip_instance.namelist.return_value = ["page_001.png"]
                mock_zip_instance.read.return_value = mock_image_data

                # First request
                start_time = time.time()
                response1 = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")
                first_request_time = time.time() - start_time

                assert response1.status_code == 200
                assert "Cache-Control" in response1.headers
                assert "max-age" in response1.headers["Cache-Control"]

                # Second request (should have same caching headers)
                start_time = time.time()
                response2 = await client.get(f"/api/reader/chapter/{chapter.id}/page/0")
                second_request_time = time.time() - start_time

                assert response2.status_code == 200
                assert response2.headers["Cache-Control"] == response1.headers["Cache-Control"]

                print(f"First request: {first_request_time:.3f}s")
                print(f"Second request: {second_request_time:.3f}s")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_series_access(self, client: AsyncClient, performance_test_series):
        """Test concurrent access to different series and chapters."""
        series, chapters = performance_test_series

        mock_image_data = b"test_image_data"

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip_instance = mock_zip.return_value.__enter__.return_value
                mock_zip_instance.namelist.return_value = ["page_001.png"]
                mock_zip_instance.read.return_value = mock_image_data

                # Create mixed requests: info, pages, progress updates
                tasks = []

                # Add chapter info requests
                for chapter in chapters[:5]:
                    tasks.append(client.get(f"/api/reader/chapter/{chapter.id}/info"))

                # Add page requests
                for chapter in chapters[:5]:
                    tasks.append(client.get(f"/api/reader/chapter/{chapter.id}/page/0"))

                # Add progress updates
                for chapter in chapters[:5]:
                    tasks.append(
                        client.put(
                            f"/api/reader/chapter/{chapter.id}/progress", json={"last_read_page": 1}
                        )
                    )

                # Add series chapters request
                tasks.append(client.get(f"/api/reader/series/{series.id}/chapters"))

                start_time = time.time()
                responses = await asyncio.gather(*tasks)
                duration = time.time() - start_time

                # All requests should succeed
                for response in responses:
                    assert response.status_code == 200

                requests_per_second = len(tasks) / duration
                print(f"Mixed requests: {requests_per_second:.1f} req/s ({len(tasks)} requests)")

                # Should handle reasonable throughput
                assert requests_per_second > 30

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_database_query_performance(self, client: AsyncClient, db_session: AsyncSession):
        """Test database query performance with many chapters."""
        # Create a series with many chapters
        series = Series(
            title_primary="Query Performance Series",
            file_path="/test/manga/query_series",
            total_chapters=100,
        )
        db_session.add(series)
        await db_session.flush()

        # Add 100 chapters
        chapters = []
        for i in range(100):
            chapter = Chapter(
                series_id=series.id,
                chapter_number=float(i + 1),
                volume_number=(i // 20) + 1,  # 20 chapters per volume
                title=f"Query Chapter {i + 1}",
                file_path=f"/test/manga/query_series/chapter_{i + 1:03d}.cbz",
                file_size=1024000,
                page_count=20,
                is_read=i < 30,  # First 30 are read
                last_read_page=19 if i < 30 else 0,
            )
            chapters.append(chapter)
            db_session.add(chapter)

        await db_session.commit()

        # Test series chapters query with many chapters
        start_time = time.time()
        response = await client.get(f"/api/reader/series/{series.id}/chapters")
        query_duration = time.time() - start_time

        assert response.status_code == 200
        data = response.json()
        assert len(data["chapters"]) == 100

        print(f"Query 100 chapters: {query_duration:.3f}s")

        # Should complete in reasonable time
        assert query_duration < 1.0  # Less than 1 second

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_thread_pool_performance(self, client: AsyncClient, performance_test_series):
        """Test thread pool utilization for page extraction."""
        _, chapters = performance_test_series

        # Mock slow file extraction to test thread pool
        def slow_read(*args, **kwargs):
            import time

            time.sleep(0.1)  # 100ms processing time
            return b"test_image_data"

        with patch("os.path.exists", return_value=True):
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip_instance = mock_zip.return_value.__enter__.return_value
                mock_zip_instance.namelist.return_value = ["page_001.png"]
                mock_zip_instance.read.side_effect = slow_read

                # Send 10 concurrent requests
                tasks = [
                    client.get(f"/api/reader/chapter/{chapters[i % len(chapters)].id}/page/0")
                    for i in range(10)
                ]

                start_time = time.time()
                responses = await asyncio.gather(*tasks)
                duration = time.time() - start_time

                # All should succeed
                for response in responses:
                    assert response.status_code == 200

                print(f"10 concurrent slow requests: {duration:.3f}s")

                # With proper thread pool, should complete faster than sequential
                # (10 * 0.1s = 1s sequential, should be much faster with concurrency)
                assert duration < 0.8  # Should be faster than 0.8s
