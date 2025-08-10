"""Integration tests for the complete watching & notification system workflow."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Series, Chapter, Notification, JobQueue
from kiremisu.services.watching_service import WatchingService
from kiremisu.services.notification_service import NotificationService
from kiremisu.services.job_worker import JobWorker


class TestWatchingSystemIntegration:
    """Integration tests for the complete watching system workflow."""

    async def test_complete_watching_workflow(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test the complete workflow from enabling watch to receiving notifications."""
        # Step 1: Prepare series with MangaDx ID
        sample_series.mangadx_id = "test-mangadx-abc123"
        await db_session.commit()
        
        # Step 2: Enable watching via API
        watch_response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": True}
        )
        
        assert watch_response.status_code == 200
        watch_data = watch_response.json()
        assert watch_data["watching_enabled"] is True
        
        # Step 3: Schedule update check jobs
        schedule_result = await WatchingService.schedule_update_checks(db_session)
        assert schedule_result["scheduled"] == 1
        assert schedule_result["total_watched"] == 1
        
        # Step 4: Verify job was created
        job_result = await db_session.execute(
            select(JobQueue).where(
                JobQueue.job_type == "chapter_update_check",
                JobQueue.payload.op("->>")(text("series_id")) == str(sample_series.id)
            )
        )
        job = job_result.scalar_one()
        assert job.status == "pending"
        assert job.payload["mangadx_id"] == sample_series.mangadx_id
        
        # Step 5: Simulate job processing finding new chapters
        new_chapters = []
        for i in range(2):
            chapter = Chapter(
                title=f"New Chapter {i+1}",
                chapter_number=float(i + 100),
                volume_number=10,
                series_id=sample_series.id,
                file_path=f"/test/new_chapter_{i+1}.cbz",
                file_size=2000000,
                page_count=25
            )
            db_session.add(chapter)
            new_chapters.append(chapter)
        
        await db_session.commit()
        
        # Step 6: Create notifications for new chapters
        notifications = await NotificationService.create_chapter_notifications(
            db=db_session, series=sample_series, new_chapters=new_chapters
        )
        
        assert len(notifications) == 2
        for notification in notifications:
            assert notification.notification_type == "new_chapter"
            assert notification.series_id == sample_series.id
            assert not notification.is_read
        
        # Step 7: Verify notifications via API
        notifications_response = await client.get("/api/notifications/")
        assert notifications_response.status_code == 200
        notifications_data = notifications_response.json()
        
        assert notifications_data["total"] == 2
        assert all(not n["is_read"] for n in notifications_data["notifications"])
        
        # Step 8: Check notification count
        count_response = await client.get("/api/notifications/count")
        assert count_response.status_code == 200
        count_data = count_response.json()
        assert count_data["unread_count"] == 2
        
        # Step 9: Mark one notification as read
        notification_id = notifications[0].id
        read_response = await client.post(f"/api/notifications/{notification_id}/read")
        assert read_response.status_code == 200
        read_data = read_response.json()
        assert read_data["is_read"] is True
        assert read_data["unread_count"] == 1
        
        # Step 10: Disable watching
        disable_response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": False}
        )
        assert disable_response.status_code == 200
        disable_data = disable_response.json()
        assert disable_data["watching_enabled"] is False

    async def test_multiple_series_watching_workflow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test watching multiple series simultaneously."""
        # Create multiple series
        series_list = []
        for i in range(3):
            series = Series(
                title_primary=f"Test Series {i}",
                file_path=f"/test/series_{i}",
                mangadx_id=f"mangadx-{i}"
            )
            db_session.add(series)
            series_list.append(series)
        
        await db_session.commit()
        
        # Enable watching for all series
        for series in series_list:
            response = await client.post(
                f"/api/series/{series.id}/watch",
                json={"enabled": True}
            )
            assert response.status_code == 200
        
        # Schedule update checks
        schedule_result = await WatchingService.schedule_update_checks(db_session)
        assert schedule_result["scheduled"] == 3
        assert schedule_result["total_watched"] == 3
        
        # Verify jobs were created for all series
        jobs_result = await db_session.execute(
            select(func.count(JobQueue.id)).where(JobQueue.job_type == "chapter_update_check")
        )
        job_count = jobs_result.scalar()
        assert job_count == 3
        
        # Create notifications for multiple series
        all_notifications = []
        for i, series in enumerate(series_list):
            # Create chapters for this series
            chapters = []
            for j in range(2):
                chapter = Chapter(
                    title=f"Series {i} Chapter {j}",
                    chapter_number=float(j + 1),
                    series_id=series.id,
                    file_path=f"/test/series_{i}/chapter_{j}.cbz",
                    file_size=1000000,
                    page_count=20
                )
                db_session.add(chapter)
                chapters.append(chapter)
            
            await db_session.commit()
            
            # Create notifications
            notifications = await NotificationService.create_chapter_notifications(
                db=db_session, series=series, new_chapters=chapters
            )
            all_notifications.extend(notifications)
        
        # Verify total notification count
        assert len(all_notifications) == 6  # 3 series * 2 chapters each
        
        # Test notification API with all notifications
        response = await client.get("/api/notifications/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6
        
        # Test notification stats
        stats_response = await client.get("/api/notifications/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["total_notifications"] == 6
        assert stats_data["unread_notifications"] == 6

    async def test_job_scheduling_prevents_duplicates(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test that job scheduling prevents duplicate jobs."""
        # Set up watched series
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-mangadx-duplicate"
        await db_session.commit()
        
        # First scheduling should create a job
        result1 = await WatchingService.schedule_update_checks(db_session)
        assert result1["scheduled"] == 1
        assert result1["skipped"] == 0
        
        # Second scheduling should skip (job already exists)
        result2 = await WatchingService.schedule_update_checks(db_session)
        assert result2["scheduled"] == 0
        assert result2["skipped"] == 1
        
        # Verify only one job exists
        jobs_result = await db_session.execute(
            select(func.count(JobQueue.id)).where(
                JobQueue.job_type == "chapter_update_check",
                JobQueue.payload.op("->>")(text("series_id")) == str(sample_series.id)
            )
        )
        job_count = jobs_result.scalar()
        assert job_count == 1

    async def test_notification_cleanup_integration(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test notification cleanup functionality."""
        # Create old and new notifications
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Old read notifications (should be cleaned up)
        old_notifications = []
        for i in range(3):
            notification = Notification(
                notification_type="new_chapter",
                title=f"Old Notification {i}",
                message=f"Old message {i}",
                series_id=sample_series.id,
                is_read=True,
                read_at=now - timedelta(days=40),
                created_at=now - timedelta(days=40)
            )
            db_session.add(notification)
            old_notifications.append(notification)
        
        # Old unread notifications (should be kept)
        old_unread = Notification(
            notification_type="new_chapter",
            title="Old Unread",
            message="Old unread message",
            series_id=sample_series.id,
            is_read=False,
            created_at=now - timedelta(days=40)
        )
        db_session.add(old_unread)
        
        # Recent notifications (should be kept)
        recent_notification = Notification(
            notification_type="new_chapter",
            title="Recent Notification",
            message="Recent message",
            series_id=sample_series.id,
            is_read=True,
            read_at=now - timedelta(days=10),
            created_at=now - timedelta(days=10)
        )
        db_session.add(recent_notification)
        
        await db_session.commit()
        
        # Verify initial count
        initial_count = await NotificationService.get_unread_count(db_session)
        all_notifications = await NotificationService.get_notifications(db_session, limit=100)
        assert len(all_notifications) == 5
        
        # Run cleanup
        deleted_count = await NotificationService.cleanup_old_notifications(
            db_session, days=30, keep_unread=True
        )
        
        assert deleted_count == 3  # Only old read notifications
        
        # Verify remaining notifications
        remaining_notifications = await NotificationService.get_notifications(db_session, limit=100)
        assert len(remaining_notifications) == 2
        
        remaining_titles = {n.title for n in remaining_notifications}
        assert "Old Unread" in remaining_titles
        assert "Recent Notification" in remaining_titles

    async def test_watch_statistics_integration(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test watching statistics across the entire system."""
        # Create test data
        series_data = [
            {"title": "Series A", "watching": True, "mangadx_id": "mangadx-a"},
            {"title": "Series B", "watching": True, "mangadx_id": "mangadx-b"},
            {"title": "Series C", "watching": False, "mangadx_id": "mangadx-c"},
            {"title": "Series D", "watching": True, "mangadx_id": None},  # No MangaDx ID
        ]
        
        created_series = []
        for data in series_data:
            series = Series(
                title_primary=data["title"],
                file_path=f"/test/{data['title'].lower()}",
                watching_enabled=data["watching"],
                mangadx_id=data["mangadx_id"]
            )
            db_session.add(series)
            created_series.append(series)
        
        await db_session.commit()
        
        # Schedule jobs for eligible series
        await WatchingService.schedule_update_checks(db_session)
        
        # Get comprehensive stats
        watching_stats = await WatchingService.get_watching_stats(db_session)
        
        assert watching_stats["watched_series"] == 3  # A, B, D are watching
        assert watching_stats["eligible_series"] == 3  # A, B, C have MangaDx IDs
        assert watching_stats["pending_update_checks"] == 2  # Only A, B get jobs (have MangaDx IDs)
        
        # Create some notifications and get notification stats
        for series in created_series[:2]:  # Create notifications for first 2 series
            chapter = Chapter(
                title="Test Chapter",
                chapter_number=1.0,
                series_id=series.id,
                file_path=f"/test/{series.title_primary}/chapter_1.cbz",
                file_size=1000000,
                page_count=20
            )
            db_session.add(chapter)
            await db_session.commit()
            
            await NotificationService.create_chapter_notifications(
                db=db_session, series=series, new_chapters=[chapter]
            )
        
        notification_stats = await NotificationService.get_notification_stats(db_session)
        
        assert notification_stats["total_notifications"] == 2
        assert notification_stats["unread_notifications"] == 2
        assert notification_stats["notifications_by_type"]["new_chapter"] == 2

    @patch('kiremisu.services.job_worker.JobWorker.process_job')
    async def test_job_processing_integration(
        self, mock_process_job, client: AsyncClient, 
        db_session: AsyncSession, sample_series: Series
    ):
        """Test integration with job processing system."""
        # Set up watched series
        sample_series.watching_enabled = True
        sample_series.mangadx_id = "test-job-processing"
        await db_session.commit()
        
        # Schedule job
        await WatchingService.schedule_update_checks(db_session)
        
        # Get the created job
        job_result = await db_session.execute(
            select(JobQueue).where(JobQueue.job_type == "chapter_update_check")
        )
        job = job_result.scalar_one()
        
        # Mock job processing to simulate finding new chapters
        async def mock_job_processing(job_data):
            # Simulate job worker processing
            chapter = Chapter(
                title="Processed Chapter",
                chapter_number=999.0,
                series_id=sample_series.id,
                file_path="/test/processed_chapter.cbz",
                file_size=1500000,
                page_count=30
            )
            db_session.add(chapter)
            await db_session.commit()
            
            # Create notification
            await NotificationService.create_chapter_notifications(
                db=db_session, series=sample_series, new_chapters=[chapter]
            )
            
            return {"status": "completed", "chapters_found": 1}
        
        mock_process_job.side_effect = lambda job: mock_job_processing(job)
        
        # Process the job
        job_worker = JobWorker(db_session)
        await job_worker.process_job(job)
        
        # Verify notification was created
        notifications = await NotificationService.get_notifications(db_session)
        assert len(notifications) == 1
        assert notifications[0].title == f"New chapter available: {sample_series.title_primary}"
        assert "Chapter 999" in notifications[0].message

    async def test_concurrent_watching_operations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test concurrent watching operations don't cause race conditions."""
        # Create multiple series
        series_list = []
        for i in range(5):
            series = Series(
                title_primary=f"Concurrent Series {i}",
                file_path=f"/test/concurrent_{i}",
                mangadx_id=f"concurrent-{i}"
            )
            db_session.add(series)
            series_list.append(series)
        
        await db_session.commit()
        
        # Perform concurrent watch toggle operations
        async def toggle_watch_for_series(series, enabled):
            return await client.post(
                f"/api/series/{series.id}/watch",
                json={"enabled": enabled}
            )
        
        # Create tasks for concurrent execution
        tasks = []
        for i, series in enumerate(series_list):
            enabled = i % 2 == 0  # Alternate enabled/disabled
            tasks.append(toggle_watch_for_series(series, enabled))
        
        # Execute all tasks concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                pytest.fail(f"Concurrent operation {i} failed: {response}")
            assert response.status_code == 200
        
        # Verify final state is consistent
        for i, series in enumerate(series_list):
            await db_session.refresh(series)
            expected_enabled = i % 2 == 0
            assert series.watching_enabled == expected_enabled

    async def test_error_recovery_integration(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test system recovery from various error scenarios."""
        # Test 1: API error recovery
        sample_series.mangadx_id = "test-error-recovery"
        await db_session.commit()
        
        # Simulate database connection error during watch toggle
        with patch('kiremisu.services.watching_service.WatchingService.toggle_watch') as mock_toggle:
            mock_toggle.side_effect = Exception("Database connection lost")
            
            response = await client.post(
                f"/api/series/{sample_series.id}/watch",
                json={"enabled": True}
            )
            
            # Should return 500 error but not crash
            assert response.status_code == 500
        
        # Test 2: Recovery after error - normal operation should work
        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": True}
        )
        assert response.status_code == 200
        
        # Test 3: Notification service error recovery
        with patch('kiremisu.services.notification_service.NotificationService.get_notifications') as mock_get:
            mock_get.side_effect = Exception("Database query failed")
            
            response = await client.get("/api/notifications/")
            
            # Should handle error gracefully (behavior depends on @with_db_retry decorator)
            assert response.status_code in [500, 503]
        
        # Test 4: Recovery - normal notification operations should work
        response = await client.get("/api/notifications/count")
        assert response.status_code == 200


# Additional integration test fixtures are defined in conftest.py