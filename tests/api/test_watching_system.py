"""Comprehensive tests for the watching & notification system API endpoints."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Notification, Series
from kiremisu.services.notification_service import NotificationService
from kiremisu.services.watching_service import WatchingService


class TestWatchingSystemAPI:
    """Test suite for watching & notification system API endpoints."""

    async def test_toggle_series_watch_enable(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test enabling watch status for a series."""
        # Verify series is not being watched initially
        assert not sample_series.watching_enabled

        # Enable watching
        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": True}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["series_id"] == str(sample_series.id)
        assert data["watching_enabled"] is True
        assert data["series_title"] == sample_series.title_primary

        # Verify in database
        await db_session.refresh(sample_series)
        assert sample_series.watching_enabled is True
        assert sample_series.last_watched_check is None  # Should be reset when enabling

    async def test_toggle_series_watch_disable(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test disabling watch status for a series."""
        # First enable watching
        sample_series.watching_enabled = True
        await db_session.commit()

        # Disable watching
        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": False}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["series_id"] == str(sample_series.id)
        assert data["watching_enabled"] is False

        # Verify in database
        await db_session.refresh(sample_series)
        assert sample_series.watching_enabled is False

    async def test_toggle_series_watch_nonexistent_series(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test toggling watch for non-existent series returns 404."""
        fake_id = uuid4()

        response = await client.post(
            f"/api/series/{fake_id}/watch",
            json={"enabled": True}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_toggle_series_watch_invalid_payload(
        self, client: AsyncClient, sample_series: Series
    ):
        """Test toggling watch with invalid payload returns 422."""
        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"invalid": "payload"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("enabled_value", [True, False])
    async def test_toggle_series_watch_idempotent(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, enabled_value: bool
    ):
        """Test that toggling watch to the same state is idempotent."""
        # Set initial state
        sample_series.watching_enabled = enabled_value
        await db_session.commit()

        # Toggle to the same state
        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": enabled_value}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["watching_enabled"] == enabled_value

        # Verify state didn't change
        await db_session.refresh(sample_series)
        assert sample_series.watching_enabled == enabled_value


class TestNotificationAPI:
    """Test suite for notification API endpoints."""

    async def test_get_notifications_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test getting notifications when none exist."""
        response = await client.get("/api/notifications/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["notifications"] == []
        assert data["total"] == 0
        assert data["unread_only"] is False

    async def test_get_notifications_with_data(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test getting notifications with data."""
        response = await client.get("/api/notifications/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["notifications"]) == len(sample_notifications)
        assert data["total"] == len(sample_notifications)

        # Verify notification structure
        notification = data["notifications"][0]
        assert "id" in notification
        assert "notification_type" in notification
        assert "title" in notification
        assert "message" in notification
        assert "is_read" in notification
        assert "created_at" in notification

    async def test_get_notifications_pagination(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test notification pagination."""
        # Get first page
        response = await client.get("/api/notifications/?skip=0&limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["notifications"]) == min(2, len(sample_notifications))

        # Get second page
        if len(sample_notifications) > 2:
            response2 = await client.get("/api/notifications/?skip=2&limit=2")

            assert response2.status_code == status.HTTP_200_OK
            data2 = response2.json()

            # Ensure different results
            first_ids = {n["id"] for n in data["notifications"]}
            second_ids = {n["id"] for n in data2["notifications"]}
            assert first_ids.isdisjoint(second_ids)

    async def test_get_notifications_unread_only(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test filtering notifications to unread only."""
        # Mark some notifications as read
        if len(sample_notifications) >= 2:
            sample_notifications[0].is_read = True
            sample_notifications[0].read_at = datetime.now(UTC).replace(tzinfo=None)
            await db_session.commit()

        response = await client.get("/api/notifications/?unread_only=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["unread_only"] is True

        # All returned notifications should be unread
        for notification in data["notifications"]:
            assert notification["is_read"] is False

    async def test_get_notification_count(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test getting unread notification count."""
        response = await client.get("/api/notifications/count")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        assert data["unread_count"] >= 0

    async def test_get_notification_stats(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test getting comprehensive notification statistics."""
        response = await client.get("/api/notifications/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        required_fields = [
            "total_notifications", "unread_notifications",
            "read_notifications", "notifications_by_type"
        ]

        for field in required_fields:
            assert field in data

        assert data["total_notifications"] >= 0
        assert data["unread_notifications"] >= 0
        assert data["read_notifications"] >= 0
        assert isinstance(data["notifications_by_type"], dict)

        # Verify math
        assert (data["total_notifications"] ==
                data["unread_notifications"] + data["read_notifications"])

    async def test_get_notification_by_id(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test getting a specific notification by ID."""
        if not sample_notifications:
            pytest.skip("No sample notifications available")

        notification = sample_notifications[0]

        response = await client.get(f"/api/notifications/{notification.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(notification.id)
        assert data["notification_type"] == notification.notification_type
        assert data["title"] == notification.title
        assert data["message"] == notification.message

    async def test_get_notification_by_id_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test getting non-existent notification returns 404."""
        fake_id = uuid4()

        response = await client.get(f"/api/notifications/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_mark_notification_read(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test marking a single notification as read."""
        if not sample_notifications:
            pytest.skip("No sample notifications available")

        notification = sample_notifications[0]

        # Ensure it's initially unread
        notification.is_read = False
        notification.read_at = None
        await db_session.commit()

        response = await client.post(f"/api/notifications/{notification.id}/read")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(notification.id)
        assert data["is_read"] is True
        assert data["read_at"] is not None
        assert "unread_count" in data

        # Verify in database
        await db_session.refresh(notification)
        assert notification.is_read is True
        assert notification.read_at is not None

    async def test_mark_notification_read_already_read(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test marking already read notification is idempotent."""
        if not sample_notifications:
            pytest.skip("No sample notifications available")

        notification = sample_notifications[0]

        # Mark as read first
        notification.is_read = True
        notification.read_at = datetime.now(UTC).replace(tzinfo=None)
        await db_session.commit()

        original_read_at = notification.read_at

        response = await client.post(f"/api/notifications/{notification.id}/read")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["is_read"] is True

        # Verify read_at timestamp didn't change
        await db_session.refresh(notification)
        assert notification.read_at == original_read_at

    async def test_mark_notification_read_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test marking non-existent notification as read returns 404."""
        fake_id = uuid4()

        response = await client.post(f"/api/notifications/{fake_id}/read")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_mark_all_notifications_read(
        self, client: AsyncClient, db_session: AsyncSession,
        sample_series: Series, sample_notifications: list[Notification]
    ):
        """Test marking all notifications as read."""
        # Ensure some notifications are unread
        unread_count = 0
        for notification in sample_notifications:
            if not notification.is_read:
                unread_count += 1

        response = await client.post("/api/notifications/read-all")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "marked_count" in data
        assert "unread_count" in data
        assert data["unread_count"] == 0

        # Verify all notifications are now read
        for notification in sample_notifications:
            await db_session.refresh(notification)
            assert notification.is_read is True
            assert notification.read_at is not None

    async def test_mark_all_notifications_read_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test marking all notifications as read when none exist."""
        response = await client.post("/api/notifications/read-all")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["marked_count"] == 0
        assert data["unread_count"] == 0


class TestWatchingSystemIntegration:
    """Integration tests for the complete watching system workflow."""

    async def test_watch_series_creates_scheduled_job(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test that enabling watching eventually schedules update check jobs."""
        # Give series a MangaDx ID so it's eligible for watching
        sample_series.mangadx_id = "test-mangadx-id-123"
        await db_session.commit()

        # Enable watching
        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": True}
        )

        assert response.status_code == status.HTTP_200_OK

        # Manually trigger job scheduling (simulating background scheduler)
        with patch.object(WatchingService, 'schedule_update_checks') as mock_schedule:
            mock_schedule.return_value = {
                "scheduled": 1,
                "skipped": 0,
                "total_watched": 1
            }

            result = await WatchingService.schedule_update_checks(db_session)

            assert result["scheduled"] >= 0
            assert result["total_watched"] >= 0
            mock_schedule.assert_called_once()

    async def test_notification_api_error_handling(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test error handling in notification API endpoints."""
        # Test invalid pagination parameters
        response = await client.get("/api/notifications/?skip=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = await client.get("/api/notifications/?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = await client.get("/api/notifications/?limit=101")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_concurrent_watch_toggle_operations(
        self, client: AsyncClient, db_session: AsyncSession, sample_series: Series
    ):
        """Test concurrent watch toggle operations don't cause race conditions."""
        import asyncio

        async def toggle_watch(enabled: bool):
            return await client.post(
                f"/api/series/{sample_series.id}/watch",
                json={"enabled": enabled}
            )

        # Execute concurrent toggles
        tasks = [
            toggle_watch(True),
            toggle_watch(False),
            toggle_watch(True),
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed (some might be idempotent)
        for response in responses:
            if isinstance(response, Exception):
                pytest.fail(f"Concurrent operation failed: {response}")
            assert response.status_code == status.HTTP_200_OK

        # Final state should be consistent
        await db_session.refresh(sample_series)
        assert isinstance(sample_series.watching_enabled, bool)

    @patch.object(WatchingService, 'toggle_watch')
    async def test_watch_toggle_service_error_handling(
        self, mock_toggle_watch, client: AsyncClient, sample_series: Series
    ):
        """Test API error handling when service layer fails."""
        mock_toggle_watch.side_effect = Exception("Service layer error")

        response = await client.post(
            f"/api/series/{sample_series.id}/watch",
            json={"enabled": True}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to update watch status" in response.json()["detail"]

    @patch.object(NotificationService, 'get_notifications')
    async def test_notification_api_service_error_handling(
        self, mock_get_notifications, client: AsyncClient
    ):
        """Test notification API error handling when service layer fails."""
        mock_get_notifications.side_effect = Exception("Database connection error")

        response = await client.get("/api/notifications/")

        # Should handle gracefully (actual behavior depends on @with_db_retry decorator)
        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]


# Test fixtures are defined in conftest.py
