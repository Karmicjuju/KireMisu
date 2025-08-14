"""Performance tests for reading progress calculation with large collections."""

import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Series


class TestProgressCalculationPerformance:
    """Performance tests for progress calculation with large data sets."""

    @pytest.fixture
    async def large_library_dataset(self, db_session: AsyncSession):
        """Create a large library dataset for performance testing."""
        series_count = 100
        chapters_per_series = 50
        total_chapters = series_count * chapters_per_series

        print(f"Creating test dataset: {series_count} series, {total_chapters} chapters")

        start_time = time.time()

        series_list = []
        all_chapters = []

        # Create series and chapters in batches for better performance
        for s in range(series_count):
            # Vary read progress: 0-50% read chapters per series
            read_chapter_count = (s * chapters_per_series) // (100 + s % 10)

            series = Series(
                id=uuid4(),
                title_primary=f"Performance Test Series {s + 1:03d}",
                language="en",
                file_path=f"/test/perf_series_{s + 1:03d}",
                total_chapters=chapters_per_series,
                read_chapters=read_chapter_count,
            )
            series_list.append(series)
            db_session.add(series)

            # Create chapters for this series
            for c in range(chapters_per_series):
                is_read = c < read_chapter_count

                chapter = Chapter(
                    id=uuid4(),
                    series_id=series.id,
                    chapter_number=float(c + 1),
                    volume_number=(c // 10) + 1,  # 10 chapters per volume
                    title=f"Chapter {c + 1}",
                    file_path=f"/test/perf_series_{s + 1:03d}/chapter_{c + 1:03d}.cbz",
                    file_size=1024 * (c + 1),
                    page_count=20 + (c % 5),  # 20-24 pages per chapter
                    is_read=is_read,
                    last_read_page=19 + (c % 5) if is_read else (c % 10),
                    read_at=datetime.utcnow() - timedelta(days=c) if is_read else None,
                )
                all_chapters.append(chapter)
                db_session.add(chapter)

            # Commit in batches to avoid memory issues
            if (s + 1) % 10 == 0:
                await db_session.commit()
                print(f"Created {s + 1} series with {(s + 1) * chapters_per_series} chapters")

        # Final commit
        await db_session.commit()

        # Refresh series objects to get IDs
        for series in series_list:
            await db_session.refresh(series)

        creation_time = time.time() - start_time
        print(f"Dataset creation completed in {creation_time:.2f} seconds")

        return {
            "series_list": series_list,
            "all_chapters": all_chapters,
            "series_count": series_count,
            "chapters_per_series": chapters_per_series,
            "total_chapters": total_chapters,
        }

    @pytest.mark.asyncio
    async def test_dashboard_stats_performance_large_library(
        self, client: AsyncClient, large_library_dataset: dict
    ):
        """Test dashboard statistics calculation performance with large library."""
        dataset = large_library_dataset
        print(f"Testing dashboard stats with {dataset['total_chapters']} chapters")

        # Measure dashboard stats API performance
        start_time = time.time()

        response = await client.get("/api/dashboard/stats")

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        data = response.json()

        # Verify correctness
        assert data["total_series"] == dataset["series_count"]
        assert data["total_chapters"] == dataset["total_chapters"]

        # Performance assertion: should complete within reasonable time
        print(f"Dashboard stats completed in {response_time:.3f} seconds")
        assert response_time < 5.0, f"Dashboard stats took {response_time:.3f}s, exceeding 5s limit"

        # Additional performance metrics
        print("Performance metrics:")
        print(f"  - Series processed: {data['total_series']}")
        print(f"  - Chapters processed: {data['total_chapters']}")
        print(f"  - Processing rate: {data['total_chapters'] / response_time:.0f} chapters/second")

        return response_time

    @pytest.mark.asyncio
    async def test_series_progress_performance_many_chapters(
        self, client: AsyncClient, large_library_dataset: dict
    ):
        """Test series progress calculation performance for series with many chapters."""
        dataset = large_library_dataset
        series_to_test = dataset["series_list"][:10]  # Test first 10 series

        response_times = []

        for series in series_to_test:
            start_time = time.time()

            response = await client.get(f"/api/series/{series.id}/progress")

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            assert response.status_code == 200
            data = response.json()

            # Verify data integrity
            assert data["series"]["id"] == str(series.id)
            assert len(data["chapters"]) == dataset["chapters_per_series"]

            # Performance check per series
            print(
                f"Series {series.title_primary}: {response_time:.3f}s for {dataset['chapters_per_series']} chapters"
            )
            assert response_time < 2.0, (
                f"Series progress took {response_time:.3f}s, exceeding 2s limit"
            )

        # Overall performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        print("Series progress performance summary:")
        print(f"  - Average response time: {avg_response_time:.3f}s")
        print(f"  - Maximum response time: {max_response_time:.3f}s")
        print(f"  - Chapters per series: {dataset['chapters_per_series']}")

        assert avg_response_time < 1.0, f"Average response time {avg_response_time:.3f}s exceeds 1s"
        assert max_response_time < 2.0, f"Max response time {max_response_time:.3f}s exceeds 2s"

    @pytest.mark.asyncio
    async def test_concurrent_progress_requests_performance(
        self, client: AsyncClient, large_library_dataset: dict
    ):
        """Test performance of concurrent progress calculation requests."""
        dataset = large_library_dataset
        series_to_test = dataset["series_list"][:20]  # Test with 20 series

        print(f"Testing concurrent requests for {len(series_to_test)} series")

        async def get_series_progress(series):
            """Helper function to get series progress."""
            start_time = time.time()
            response = await client.get(f"/api/series/{series.id}/progress")
            end_time = time.time()

            assert response.status_code == 200
            return {
                "series_id": series.id,
                "response_time": end_time - start_time,
                "data": response.json(),
            }

        # Execute concurrent requests
        overall_start = time.time()

        tasks = [get_series_progress(series) for series in series_to_test]
        results = await asyncio.gather(*tasks)

        overall_end = time.time()
        total_time = overall_end - overall_start

        # Analyze results
        response_times = [result["response_time"] for result in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        print("Concurrent requests performance:")
        print(f"  - Total time: {total_time:.3f}s")
        print(f"  - Average individual response time: {avg_response_time:.3f}s")
        print(f"  - Maximum individual response time: {max_response_time:.3f}s")
        print(
            f"  - Concurrent efficiency: {len(series_to_test) * avg_response_time / total_time:.1f}x"
        )

        # Performance assertions
        assert total_time < 10.0, f"Concurrent requests took {total_time:.3f}s, exceeding 10s limit"
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.3f}s exceeds 2s"

        # Verify data integrity for all responses
        for result in results:
            data = result["data"]
            assert "series" in data
            assert "chapters" in data
            assert "progress_percentage" in data

    @pytest.mark.asyncio
    async def test_mark_read_performance_batch_operations(
        self, client: AsyncClient, large_library_dataset: dict
    ):
        """Test performance of batch mark-read operations."""
        dataset = large_library_dataset
        test_series = dataset["series_list"][0]  # Use first series

        # Get all chapters for the test series
        chapters_response = await client.get(f"/api/series/{test_series.id}/progress")
        chapters_data = chapters_response.json()["chapters"]

        # Find unread chapters
        unread_chapters = [ch for ch in chapters_data if not ch["is_read"]][
            :20
        ]  # Test with 20 chapters

        if not unread_chapters:
            pytest.skip("No unread chapters available for batch testing")

        print(f"Testing batch mark-read for {len(unread_chapters)} chapters")

        # Sequential mark-read operations
        start_time = time.time()

        for chapter in unread_chapters:
            response = await client.put(f"/api/chapters/{chapter['id']}/mark-read")
            assert response.status_code == 200

        sequential_time = time.time() - start_time

        # Verify all chapters were marked as read
        verification_response = await client.get(f"/api/series/{test_series.id}/progress")
        verification_data = verification_response.json()

        marked_chapters = {ch["id"]: ch for ch in verification_data["chapters"]}
        for chapter in unread_chapters:
            assert marked_chapters[chapter["id"]]["is_read"] is True

        print("Batch mark-read performance:")
        print(f"  - Chapters marked: {len(unread_chapters)}")
        print(f"  - Total time: {sequential_time:.3f}s")
        print(f"  - Average time per chapter: {sequential_time / len(unread_chapters):.3f}s")
        print(f"  - Throughput: {len(unread_chapters) / sequential_time:.1f} chapters/second")

        # Performance assertions
        avg_time_per_chapter = sequential_time / len(unread_chapters)
        assert avg_time_per_chapter < 0.5, (
            f"Average mark-read time {avg_time_per_chapter:.3f}s exceeds 0.5s"
        )
        assert sequential_time < 10.0, (
            f"Batch operation took {sequential_time:.3f}s, exceeding 10s limit"
        )

    @pytest.mark.asyncio
    async def test_progress_aggregation_performance(
        self, client: AsyncClient, large_library_dataset: dict, db_session: AsyncSession
    ):
        """Test performance of progress aggregation and database updates."""
        dataset = large_library_dataset
        test_series = dataset["series_list"][0]

        # Get initial state
        initial_response = await client.get(f"/api/series/{test_series.id}/progress")
        initial_data = initial_response.json()
        initial_read_count = initial_data["series"]["read_chapters"]

        # Find an unread chapter
        unread_chapters = [ch for ch in initial_data["chapters"] if not ch["is_read"]]
        if not unread_chapters:
            pytest.skip("No unread chapters available for aggregation testing")

        test_chapter = unread_chapters[0]

        # Measure aggregation performance
        start_time = time.time()

        # Mark chapter as read (triggers aggregation)
        mark_response = await client.put(f"/api/chapters/{test_chapter['id']}/mark-read")
        assert mark_response.status_code == 200

        # Verify aggregation completed
        final_response = await client.get(f"/api/series/{test_series.id}/progress")
        final_data = final_response.json()

        end_time = time.time()
        aggregation_time = end_time - start_time

        # Verify correctness
        assert final_data["series"]["read_chapters"] == initial_read_count + 1

        # Verify database consistency
        result = await db_session.execute(select(Series).where(Series.id == test_series.id))
        db_series = result.scalar_one()
        assert db_series.read_chapters == initial_read_count + 1

        print("Progress aggregation performance:")
        print(f"  - Aggregation time: {aggregation_time:.3f}s")
        print(f"  - Series chapters: {dataset['chapters_per_series']}")

        # Performance assertion
        assert aggregation_time < 1.0, (
            f"Aggregation took {aggregation_time:.3f}s, exceeding 1s limit"
        )

    @pytest.mark.asyncio
    async def test_database_query_performance_large_dataset(
        self, db_session: AsyncSession, large_library_dataset: dict
    ):
        """Test raw database query performance for progress calculations."""
        dataset = large_library_dataset

        # Test various queries that would be used in progress calculations
        queries_to_test = [
            {
                "name": "Count total series",
                "query": select(func.count(Series.id)),
            },
            {
                "name": "Count total chapters",
                "query": select(func.count(Chapter.id)),
            },
            {
                "name": "Count read chapters",
                "query": select(func.count(Chapter.id)).where(Chapter.is_read),
            },
            {
                "name": "Series with read counts",
                "query": select(
                    Series.id, Series.title_primary, Series.read_chapters, Series.total_chapters
                ),
            },
            {
                "name": "Chapters for first series",
                "query": select(Chapter).where(Chapter.series_id == dataset["series_list"][0].id),
            },
        ]

        print("Database query performance test:")

        for query_test in queries_to_test:
            start_time = time.time()

            result = await db_session.execute(query_test["query"])

            if query_test["name"].startswith("Count"):
                count = result.scalar()
                end_time = time.time()
                query_time = end_time - start_time

                print(f"  - {query_test['name']}: {query_time:.3f}s (result: {count})")
            else:
                rows = result.all()
                end_time = time.time()
                query_time = end_time - start_time

                print(f"  - {query_test['name']}: {query_time:.3f}s (rows: {len(rows)})")

            # Performance assertion: database queries should be fast
            assert query_time < 2.0, (
                f"Query '{query_test['name']}' took {query_time:.3f}s, exceeding 2s limit"
            )

    @pytest.mark.asyncio
    async def test_memory_usage_large_progress_calculation(
        self, client: AsyncClient, large_library_dataset: dict
    ):
        """Test memory usage during large progress calculations."""
        import os

        import psutil

        dataset = large_library_dataset
        process = psutil.Process(os.getpid())

        # Measure initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print("Memory usage test:")
        print(f"  - Initial memory: {initial_memory:.1f} MB")

        # Perform memory-intensive operations
        operations = [
            ("Dashboard stats", lambda: client.get("/api/dashboard/stats")),
            (
                "Series progress (largest)",
                lambda: client.get(f"/api/series/{dataset['series_list'][0].id}/progress"),
            ),
            (
                "Multiple series progress",
                lambda: asyncio.gather(
                    *[
                        client.get(f"/api/series/{series.id}/progress")
                        for series in dataset["series_list"][:5]
                    ]
                ),
            ),
        ]

        for operation_name, operation_func in operations:
            pre_op_memory = process.memory_info().rss / 1024 / 1024

            # Execute operation
            start_time = time.time()
            if asyncio.iscoroutinefunction(operation_func):
                await operation_func()
            else:
                result = await operation_func()
                if hasattr(result, "status_code"):
                    assert result.status_code == 200
            end_time = time.time()

            post_op_memory = process.memory_info().rss / 1024 / 1024
            operation_time = end_time - start_time
            memory_increase = post_op_memory - pre_op_memory

            print(f"  - {operation_name}:")
            print(f"    * Time: {operation_time:.3f}s")
            print(f"    * Memory before: {pre_op_memory:.1f} MB")
            print(f"    * Memory after: {post_op_memory:.1f} MB")
            print(f"    * Memory increase: {memory_increase:+.1f} MB")

            # Memory usage assertions
            assert memory_increase < 100, (
                f"Operation '{operation_name}' increased memory by {memory_increase:.1f}MB"
            )

        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory

        print(f"  - Final memory: {final_memory:.1f} MB")
        print(f"  - Total increase: {total_increase:+.1f} MB")

        # Overall memory usage should be reasonable
        assert total_increase < 200, (
            f"Total memory increase {total_increase:.1f}MB exceeds 200MB limit"
        )

    @pytest.mark.asyncio
    async def test_progress_calculation_scalability_limits(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test scalability limits for progress calculation."""
        # Create an extremely large series to test limits
        extreme_series = Series(
            id=uuid4(),
            title_primary="Extreme Scale Test Series",
            language="en",
            file_path="/test/extreme_series",
            total_chapters=1000,
            read_chapters=500,
        )
        db_session.add(extreme_series)
        await db_session.commit()
        await db_session.refresh(extreme_series)

        # Create 1000 chapters (this will be slow, but tests the limit)
        print("Creating 1000 chapters for scalability test...")

        batch_size = 100
        for batch_start in range(0, 1000, batch_size):
            batch_chapters = []

            for i in range(batch_start, min(batch_start + batch_size, 1000)):
                chapter = Chapter(
                    id=uuid4(),
                    series_id=extreme_series.id,
                    chapter_number=float(i + 1),
                    volume_number=(i // 50) + 1,  # 50 chapters per volume
                    title=f"Extreme Chapter {i + 1}",
                    file_path=f"/test/extreme_series/chapter_{i + 1:04d}.cbz",
                    file_size=1024,
                    page_count=20,
                    is_read=(i < 500),  # First 500 chapters read
                    last_read_page=19 if i < 500 else 0,
                    read_at=datetime.utcnow() - timedelta(days=1000 - i) if i < 500 else None,
                )
                batch_chapters.append(chapter)
                db_session.add(chapter)

            await db_session.commit()
            print(
                f"Created batch {batch_start // batch_size + 1}/10 ({batch_start + len(batch_chapters)} chapters)"
            )

        # Test progress calculation with extreme dataset
        print("Testing progress calculation with 1000 chapters...")

        start_time = time.time()
        response = await client.get(f"/api/series/{extreme_series.id}/progress")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        data = response.json()

        # Verify correctness
        assert data["series"]["total_chapters"] == 1000
        assert data["series"]["read_chapters"] == 500
        assert len(data["chapters"]) == 1000
        assert data["progress_percentage"] == 50.0

        print("Extreme scalability test results:")
        print("  - Chapters: 1000")
        print(f"  - Response time: {response_time:.3f}s")
        print(f"  - Processing rate: {1000 / response_time:.0f} chapters/second")

        # Scalability assertion - should handle 1000 chapters reasonably
        assert response_time < 10.0, (
            f"Extreme scale test took {response_time:.3f}s, exceeding 10s limit"
        )

        # Cleanup extreme test data
        await db_session.execute(select(Chapter).where(Chapter.series_id == extreme_series.id))
        await db_session.delete(extreme_series)
        await db_session.commit()

        return response_time
