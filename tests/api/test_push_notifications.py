"""Tests for push notifications API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from pywebpush import WebPushException
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import Chapter, Notification, PushSubscription, Series


@pytest.fixture
async def mock_vapid_settings():
    """Mock VAPID settings for testing."""
    with patch('kiremisu.api.push_notifications.settings') as mock_settings:
        mock_settings.VAPID_PUBLIC_KEY = "test_public_key"
        mock_settings.VAPID_PRIVATE_KEY = "test_private_key"
        mock_settings.VAPID_CLAIMS = {"sub": "mailto:test@example.com"}
        yield mock_settings


@pytest.fixture
async def sample_push_subscription(db_session: AsyncSession):
    """Create a sample push subscription for testing."""
    subscription = PushSubscription(
        id=uuid4(),
        endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint",
        keys={
            "p256dh": "test_p256dh_key",
            "auth": "test_auth_secret"
        },
        user_agent="Mozilla/5.0 (Test Browser)",
        is_active=True,
        failure_count=0,
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


@pytest.fixture
async def sample_inactive_push_subscription(db_session: AsyncSession):
    """Create an inactive push subscription for testing."""
    subscription = PushSubscription(
        id=uuid4(),
        endpoint="https://fcm.googleapis.com/fcm/send/inactive-endpoint",
        keys={
            "p256dh": "test_p256dh_key_inactive",
            "auth": "test_auth_secret_inactive"
        },
        user_agent="Mozilla/5.0 (Inactive Browser)",
        is_active=False,
        failure_count=5
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


@pytest.fixture
async def sample_series_with_chapter(db_session: AsyncSession):
    """Create a sample series with chapter for notification testing."""
    series = Series(
        id=uuid4(),
        title_primary="Test Manga Series",
        language="en",
        file_path="/test/manga/series",
        total_chapters=1,
        read_chapters=0,
    )
    db_session.add(series)

    chapter = Chapter(
        id=uuid4(),
        series_id=series.id,
        chapter_number=1.0,
        title="Chapter 1",
        file_path="/test/manga/series/chapter_1.cbz",
        file_size=1024 * 1024,
        page_count=20,
    )
    db_session.add(chapter)

    await db_session.commit()
    await db_session.refresh(series)
    await db_session.refresh(chapter)

    return series, chapter


class TestVapidKeyEndpoint:
    """Test VAPID public key endpoint."""

    async def test_get_vapid_public_key_success(self, client: AsyncClient, mock_vapid_settings):
        """Test successful retrieval of VAPID public key."""
        response = await client.get("/api/push/vapid-public-key")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "public_key" in data
        assert data["public_key"] == "test_public_key"

    async def test_get_vapid_public_key_not_configured(self, client: AsyncClient):
        """Test VAPID key endpoint when not configured."""
        with patch('kiremisu.api.push_notifications.settings') as mock_settings:
            mock_settings.VAPID_PUBLIC_KEY = None

            response = await client.get("/api/push/vapid-public-key")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "Push notifications are not configured" in response.json()["detail"]


class TestSubscriptionEndpoints:
    """Test push subscription management endpoints."""

    async def test_subscribe_to_push_new_subscription(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        mock_vapid_settings
    ):
        """Test creating a new push subscription."""
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/new-endpoint",
            "keys": {
                "p256dh": "new_p256dh_key",
                "auth": "new_auth_secret"
            },
            "user_agent": "Mozilla/5.0 (New Browser)",
            "expires_at": "2024-12-31T23:59:59"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/subscribe", json=subscription_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "id" in data
        assert data["endpoint"] == subscription_data["endpoint"]
        assert data["is_active"] is True
        assert data["failure_count"] == 0
        assert data["created_at"] is not None

    async def test_subscribe_to_push_existing_subscription(
        self,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test updating an existing push subscription."""
        updated_subscription_data = {
            "endpoint": sample_push_subscription.endpoint,
            "keys": {
                "p256dh": "updated_p256dh_key",
                "auth": "updated_auth_secret"
            },
            "user_agent": "Mozilla/5.0 (Updated Browser)"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/subscribe", json=updated_subscription_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(sample_push_subscription.id)
        assert data["endpoint"] == sample_push_subscription.endpoint
        assert data["is_active"] is True
        assert data["failure_count"] == 0

    async def test_unsubscribe_from_push_success(
        self,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test successful unsubscription from push notifications."""
        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.delete(f"/api/push/unsubscribe/{sample_push_subscription.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Successfully unsubscribed"

    async def test_unsubscribe_from_push_not_found(
        self,
        client: AsyncClient,
        mock_vapid_settings
    ):
        """Test unsubscribing from non-existent subscription."""
        non_existent_id = uuid4()

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.delete(f"/api/push/unsubscribe/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Subscription not found" in response.json()["detail"]

    async def test_list_subscriptions_active_only(
        self,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        sample_inactive_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test listing only active subscriptions."""
        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.get("/api/push/subscriptions?active_only=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == str(sample_push_subscription.id)
        assert data[0]["is_active"] is True

    async def test_list_subscriptions_all(
        self,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        sample_inactive_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test listing all subscriptions."""
        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.get("/api/push/subscriptions?active_only=false")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 2
        subscription_ids = {sub["id"] for sub in data}
        assert str(sample_push_subscription.id) in subscription_ids
        assert str(sample_inactive_push_subscription.id) in subscription_ids


class TestPushNotificationSending:
    """Test push notification sending functionality."""

    @patch('kiremisu.api.push_notifications.webpush')
    async def test_test_push_notification_success(
        self,
        mock_webpush: MagicMock,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test sending a test push notification successfully."""
        mock_webpush.return_value = MagicMock(status_code=200)

        test_request = {
            "title": "Test Notification",
            "body": "This is a test",
            "icon": "/test-icon.png",
            "data": {"test": True}
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post(
                f"/api/push/test/{sample_push_subscription.id}",
                json=test_request
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Test notification sent successfully"

        # Verify webpush was called correctly
        mock_webpush.assert_called_once()
        call_args = mock_webpush.call_args
        assert call_args[1]["subscription_info"]["endpoint"] == sample_push_subscription.endpoint
        assert call_args[1]["subscription_info"]["keys"] == sample_push_subscription.keys

    @patch('kiremisu.api.push_notifications.webpush')
    async def test_test_push_notification_webpush_failure(
        self,
        mock_webpush: MagicMock,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test test push notification with WebPush failure."""
        mock_webpush.side_effect = WebPushException("Push service error")

        test_request = {
            "title": "Test Notification",
            "body": "This is a test"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post(
                f"/api/push/test/{sample_push_subscription.id}",
                json=test_request
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to send test notification" in response.json()["detail"]

    async def test_test_push_notification_not_found(
        self,
        client: AsyncClient,
        mock_vapid_settings
    ):
        """Test sending test notification to non-existent subscription."""
        non_existent_id = uuid4()
        test_request = {
            "title": "Test Notification",
            "body": "This is a test"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post(
                f"/api/push/test/{non_existent_id}",
                json=test_request
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Active subscription not found" in response.json()["detail"]

    async def test_test_push_notification_inactive_subscription(
        self,
        client: AsyncClient,
        sample_inactive_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test sending test notification to inactive subscription."""
        test_request = {
            "title": "Test Notification",
            "body": "This is a test"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post(
                f"/api/push/test/{sample_inactive_push_subscription.id}",
                json=test_request
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Active subscription not found" in response.json()["detail"]

    @patch('kiremisu.api.push_notifications.send_push_to_multiple')
    async def test_send_manual_push_success(
        self,
        mock_send_multiple: AsyncMock,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test sending manual push notification to all subscriptions."""
        mock_send_multiple.return_value = {"successful": 1, "failed": 0}

        push_request = {
            "title": "Manual Notification",
            "body": "This is a manual notification",
            "type": "system_alert",
            "require_interaction": True,
            "data": {"manual": True}
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/send", json=push_request)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Queued push notification for 1 subscriptions" in data["message"]
        assert data["subscription_count"] == 1

    @patch('kiremisu.api.push_notifications.send_push_to_multiple')
    async def test_send_manual_push_specific_subscriptions(
        self,
        mock_send_multiple: AsyncMock,
        client: AsyncClient,
        sample_push_subscription: PushSubscription,
        sample_inactive_push_subscription: PushSubscription,
        mock_vapid_settings
    ):
        """Test sending manual push to specific subscriptions."""
        mock_send_multiple.return_value = {"successful": 1, "failed": 0}

        push_request = {
            "subscription_ids": [str(sample_push_subscription.id)],
            "title": "Targeted Notification",
            "body": "This is targeted",
            "type": "user_mention"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/send", json=push_request)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Queued push notification for 1 subscriptions" in data["message"]

    async def test_send_manual_push_no_subscriptions(
        self,
        client: AsyncClient,
        mock_vapid_settings
    ):
        """Test sending manual push when no subscriptions exist."""
        push_request = {
            "title": "No Subscribers",
            "body": "This won't be sent",
            "type": "system_alert"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/send", json=push_request)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No active subscriptions found" in response.json()["detail"]


class TestPushNotificationHelpers:
    """Test helper functions for push notifications."""

    @patch('kiremisu.api.push_notifications.webpush')
    async def test_send_push_notification_success(
        self,
        mock_webpush: MagicMock,
        sample_push_subscription: PushSubscription,
        db_session: AsyncSession,
        mock_vapid_settings
    ):
        """Test successful push notification sending."""
        from kiremisu.api.push_notifications import send_push_notification

        mock_webpush.return_value = MagicMock(status_code=200)

        result = await send_push_notification(
            subscription=sample_push_subscription,
            title="Test Title",
            body="Test Body",
            icon="/test-icon.png",
            data={"test": True},
            db=db_session
        )

        assert result is True
        mock_webpush.assert_called_once()

        # Verify subscription was updated
        await db_session.refresh(sample_push_subscription)
        assert sample_push_subscription.last_used is not None
        assert sample_push_subscription.failure_count == 0

    @patch('kiremisu.api.push_notifications.webpush')
    async def test_send_push_notification_subscription_expired(
        self,
        mock_webpush: MagicMock,
        sample_push_subscription: PushSubscription,
        db_session: AsyncSession,
        mock_vapid_settings
    ):
        """Test handling subscription expiry (410 error)."""
        from kiremisu.api.push_notifications import send_push_notification

        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_webpush.side_effect = WebPushException("Gone", response=mock_response)

        result = await send_push_notification(
            subscription=sample_push_subscription,
            title="Test Title",
            body="Test Body",
            db=db_session
        )

        assert result is False

        # Verify subscription was marked inactive
        await db_session.refresh(sample_push_subscription)
        assert sample_push_subscription.is_active is False

    @patch('kiremisu.api.push_notifications.webpush')
    async def test_send_push_notification_increment_failure_count(
        self,
        mock_webpush: MagicMock,
        sample_push_subscription: PushSubscription,
        db_session: AsyncSession,
        mock_vapid_settings
    ):
        """Test failure count increment on push errors."""
        from kiremisu.api.push_notifications import send_push_notification

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_webpush.side_effect = WebPushException("Server Error", response=mock_response)

        result = await send_push_notification(
            subscription=sample_push_subscription,
            title="Test Title",
            body="Test Body",
            db=db_session
        )

        assert result is False

        # Verify failure count was incremented
        await db_session.refresh(sample_push_subscription)
        assert sample_push_subscription.failure_count == 1
        assert sample_push_subscription.is_active is True

    @patch('kiremisu.api.push_notifications.webpush')
    async def test_send_push_notification_deactivate_after_failures(
        self,
        mock_webpush: MagicMock,
        sample_push_subscription: PushSubscription,
        db_session: AsyncSession,
        mock_vapid_settings
    ):
        """Test subscription deactivation after multiple failures."""
        from kiremisu.api.push_notifications import send_push_notification

        # Set subscription to 4 failures (one more will deactivate)
        sample_push_subscription.failure_count = 4
        await db_session.commit()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_webpush.side_effect = WebPushException("Server Error", response=mock_response)

        result = await send_push_notification(
            subscription=sample_push_subscription,
            title="Test Title",
            body="Test Body",
            db=db_session
        )

        assert result is False

        # Verify subscription was deactivated after 5th failure
        await db_session.refresh(sample_push_subscription)
        assert sample_push_subscription.failure_count == 5
        assert sample_push_subscription.is_active is False

    async def test_send_push_notification_no_vapid_config(
        self,
        sample_push_subscription: PushSubscription,
        db_session: AsyncSession
    ):
        """Test push notification sending without VAPID configuration."""
        from kiremisu.api.push_notifications import send_push_notification

        with patch('kiremisu.api.push_notifications.settings') as mock_settings:
            mock_settings.VAPID_PRIVATE_KEY = None
            mock_settings.VAPID_CLAIMS = None

            result = await send_push_notification(
                subscription=sample_push_subscription,
                title="Test Title",
                body="Test Body",
                db=db_session
            )

            assert result is False

    @patch('kiremisu.api.push_notifications.send_push_notification')
    async def test_send_chapter_notification(
        self,
        mock_send_push: AsyncMock,
        sample_push_subscription: PushSubscription,
        sample_series_with_chapter,
        db_session: AsyncSession,
        mock_vapid_settings
    ):
        """Test sending chapter notification to subscribers."""
        from kiremisu.api.push_notifications import send_chapter_notification

        series, chapter = sample_series_with_chapter

        # Create a notification record
        notification = Notification(
            notification_type="new_chapter",
            title=f"New Chapter: {series.title_primary}",
            message=f"Chapter {chapter.chapter_number}: {chapter.title}",
            series_id=series.id
        )
        db_session.add(notification)
        await db_session.commit()
        await db_session.refresh(notification)

        mock_send_push.return_value = True

        await send_chapter_notification(
            db=db_session,
            series=series,
            chapter=chapter,
            notification=notification
        )

        # Verify send_push_to_multiple was called with correct parameters
        assert mock_send_push.called


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization for push notification endpoints."""

    async def test_endpoints_require_api_key(self, client: AsyncClient, mock_vapid_settings):
        """Test that all endpoints require API key authentication."""
        endpoints = [
            ("POST", "/api/push/subscribe", {"endpoint": "test", "keys": {"p256dh": "key", "auth": "secret"}}),
            ("DELETE", "/api/push/unsubscribe/123e4567-e89b-12d3-a456-426614174000"),
            ("GET", "/api/push/subscriptions"),
            ("POST", "/api/push/test/123e4567-e89b-12d3-a456-426614174000", {"title": "Test"}),
            ("POST", "/api/push/send", {"title": "Test", "body": "Test"})
        ]

        for method, url, *json_data in endpoints:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=json_data[0] if json_data else {})
            elif method == "DELETE":
                response = await client.delete(url)

            # Should return 401 or 403 for missing API key
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestInputValidation:
    """Test input validation for push notification endpoints."""

    async def test_subscribe_invalid_endpoint(self, client: AsyncClient, mock_vapid_settings):
        """Test subscription with invalid endpoint."""
        invalid_data = {
            "endpoint": "",  # Empty endpoint
            "keys": {
                "p256dh": "key",
                "auth": "secret"
            }
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/subscribe", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_subscribe_missing_keys(self, client: AsyncClient, mock_vapid_settings):
        """Test subscription with missing encryption keys."""
        invalid_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test",
            "keys": {
                "p256dh": "key"
                # Missing 'auth' key
            }
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/subscribe", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_test_notification_empty_title(self, client: AsyncClient, sample_push_subscription: PushSubscription, mock_vapid_settings):
        """Test test notification with empty title."""
        invalid_data = {
            "title": "",  # Empty title
            "body": "Test body"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post(f"/api/push/test/{sample_push_subscription.id}", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_manual_push_invalid_subscription_ids(self, client: AsyncClient, mock_vapid_settings):
        """Test manual push with invalid subscription IDs."""
        invalid_data = {
            "subscription_ids": ["not-a-uuid"],
            "title": "Test Title",
            "body": "Test Body"
        }

        with patch('kiremisu.api.push_notifications.get_api_key', return_value="test_api_key"):
            response = await client.post("/api/push/send", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
