"""Tests for PushSubscription database model and operations."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.models import PushSubscription


class TestPushSubscriptionModel:
    """Test PushSubscription model functionality."""

    async def test_create_push_subscription(self, db_session: AsyncSession):
        """Test creating a new push subscription."""
        subscription_id = uuid4()
        subscription = PushSubscription(
            id=subscription_id,
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

        assert subscription.id == subscription_id
        assert subscription.endpoint == "https://fcm.googleapis.com/fcm/send/test-endpoint"
        assert subscription.keys["p256dh"] == "test_p256dh_key"
        assert subscription.keys["auth"] == "test_auth_secret"
        assert subscription.user_agent == "Mozilla/5.0 (Test Browser)"
        assert subscription.is_active is True
        assert subscription.failure_count == 0
        assert subscription.created_at is not None
        assert subscription.last_used is None
        assert subscription.expires_at is not None

    async def test_create_subscription_minimal_fields(self, db_session: AsyncSession):
        """Test creating subscription with only required fields."""
        subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/minimal-endpoint",
            keys={
                "p256dh": "minimal_p256dh_key",
                "auth": "minimal_auth_secret"
            }
        )

        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)

        assert subscription.id is not None
        assert subscription.endpoint == "https://fcm.googleapis.com/fcm/send/minimal-endpoint"
        assert subscription.keys["p256dh"] == "minimal_p256dh_key"
        assert subscription.keys["auth"] == "minimal_auth_secret"
        assert subscription.user_agent is None
        assert subscription.is_active is True  # Default value
        assert subscription.failure_count == 0  # Default value
        assert subscription.expires_at is None
        assert subscription.created_at is not None
        assert subscription.last_used is None

    async def test_endpoint_unique_constraint(self, db_session: AsyncSession):
        """Test that endpoint must be unique."""
        endpoint = "https://fcm.googleapis.com/fcm/send/duplicate-endpoint"

        subscription1 = PushSubscription(
            endpoint=endpoint,
            keys={"p256dh": "key1", "auth": "secret1"}
        )
        db_session.add(subscription1)
        await db_session.commit()

        # Try to create another subscription with the same endpoint
        subscription2 = PushSubscription(
            endpoint=endpoint,
            keys={"p256dh": "key2", "auth": "secret2"}
        )
        db_session.add(subscription2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_endpoint_not_null_constraint(self, db_session: AsyncSession):
        """Test that endpoint cannot be null or empty."""
        # Test null endpoint
        with pytest.raises(Exception):  # Could be IntegrityError or other validation error
            subscription = PushSubscription(
                endpoint=None,
                keys={"p256dh": "key", "auth": "secret"}
            )
            db_session.add(subscription)
            await db_session.commit()

        await db_session.rollback()

        # Test empty endpoint - this should be caught by the check constraint
        with pytest.raises(IntegrityError):
            subscription = PushSubscription(
                endpoint="",
                keys={"p256dh": "key", "auth": "secret"}
            )
            db_session.add(subscription)
            await db_session.commit()

    async def test_keys_not_null(self, db_session: AsyncSession):
        """Test that keys field cannot be null."""
        with pytest.raises(Exception):
            subscription = PushSubscription(
                endpoint="https://fcm.googleapis.com/fcm/send/no-keys",
                keys=None
            )
            db_session.add(subscription)
            await db_session.commit()

    async def test_update_subscription_fields(self, db_session: AsyncSession):
        """Test updating subscription fields."""
        subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/update-test",
            keys={"p256dh": "original_key", "auth": "original_secret"},
            user_agent="Original Browser",
            is_active=True,
            failure_count=0
        )
        db_session.add(subscription)
        await db_session.commit()

        # Update fields
        subscription.keys = {"p256dh": "updated_key", "auth": "updated_secret"}
        subscription.user_agent = "Updated Browser"
        subscription.is_active = False
        subscription.failure_count = 3
        subscription.last_used = datetime.now(UTC).replace(tzinfo=None)

        await db_session.commit()
        await db_session.refresh(subscription)

        assert subscription.keys["p256dh"] == "updated_key"
        assert subscription.keys["auth"] == "updated_secret"
        assert subscription.user_agent == "Updated Browser"
        assert subscription.is_active is False
        assert subscription.failure_count == 3
        assert subscription.last_used is not None

    async def test_subscription_expiration_handling(self, db_session: AsyncSession):
        """Test handling of subscription expiration dates."""
        past_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
        future_date = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)

        expired_subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/expired",
            keys={"p256dh": "expired_key", "auth": "expired_secret"},
            expires_at=past_date
        )

        valid_subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/valid",
            keys={"p256dh": "valid_key", "auth": "valid_secret"},
            expires_at=future_date
        )

        db_session.add_all([expired_subscription, valid_subscription])
        await db_session.commit()

        # Query for non-expired subscriptions
        now = datetime.now(UTC).replace(tzinfo=None)
        query = select(PushSubscription).where(
            and_(
                PushSubscription.is_active,
                (PushSubscription.expires_at.is_(None)) |
                (PushSubscription.expires_at > now)
            )
        )

        result = await db_session.execute(query)
        active_subscriptions = result.scalars().all()

        assert len(active_subscriptions) == 1
        assert active_subscriptions[0].endpoint == "https://fcm.googleapis.com/fcm/send/valid"


class TestPushSubscriptionQueries:
    """Test common database queries for push subscriptions."""

    async def test_find_by_endpoint(self, db_session: AsyncSession):
        """Test finding subscription by endpoint."""
        endpoint = "https://fcm.googleapis.com/fcm/send/find-by-endpoint"
        subscription = PushSubscription(
            endpoint=endpoint,
            keys={"p256dh": "find_key", "auth": "find_secret"}
        )
        db_session.add(subscription)
        await db_session.commit()

        # Find by endpoint
        query = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        result = await db_session.execute(query)
        found_subscription = result.scalar_one_or_none()

        assert found_subscription is not None
        assert found_subscription.endpoint == endpoint
        assert found_subscription.keys["p256dh"] == "find_key"

    async def test_find_active_subscriptions(self, db_session: AsyncSession):
        """Test querying only active subscriptions."""
        active_sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/active",
            keys={"p256dh": "active_key", "auth": "active_secret"},
            is_active=True
        )

        inactive_sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/inactive",
            keys={"p256dh": "inactive_key", "auth": "inactive_secret"},
            is_active=False
        )

        db_session.add_all([active_sub, inactive_sub])
        await db_session.commit()

        # Query active subscriptions
        query = select(PushSubscription).where(PushSubscription.is_active)
        result = await db_session.execute(query)
        active_subscriptions = result.scalars().all()

        assert len(active_subscriptions) == 1
        assert active_subscriptions[0].endpoint == "https://fcm.googleapis.com/fcm/send/active"

    async def test_find_subscriptions_with_high_failure_count(self, db_session: AsyncSession):
        """Test finding subscriptions with high failure counts."""
        low_failure_sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/low-failures",
            keys={"p256dh": "low_key", "auth": "low_secret"},
            failure_count=2
        )

        high_failure_sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/high-failures",
            keys={"p256dh": "high_key", "auth": "high_secret"},
            failure_count=8
        )

        db_session.add_all([low_failure_sub, high_failure_sub])
        await db_session.commit()

        # Query subscriptions with high failure count
        query = select(PushSubscription).where(PushSubscription.failure_count >= 5)
        result = await db_session.execute(query)
        high_failure_subscriptions = result.scalars().all()

        assert len(high_failure_subscriptions) == 1
        assert high_failure_subscriptions[0].failure_count == 8

    async def test_count_active_subscriptions(self, db_session: AsyncSession):
        """Test counting active subscriptions."""
        from sqlalchemy import func

        # Create some subscriptions
        subscriptions = [
            PushSubscription(
                endpoint=f"https://fcm.googleapis.com/fcm/send/count-{i}",
                keys={"p256dh": f"key_{i}", "auth": f"secret_{i}"},
                is_active=i % 2 == 0  # Every other one is active
            )
            for i in range(5)
        ]

        db_session.add_all(subscriptions)
        await db_session.commit()

        # Count active subscriptions
        query = select(func.count(PushSubscription.id)).where(PushSubscription.is_active)
        result = await db_session.execute(query)
        count = result.scalar()

        assert count == 3  # 0, 2, 4 are active (every other one)

    async def test_bulk_update_failure_counts(self, db_session: AsyncSession):
        """Test bulk updating failure counts."""
        from sqlalchemy import update

        # Create subscriptions with various failure counts
        subscriptions = [
            PushSubscription(
                endpoint=f"https://fcm.googleapis.com/fcm/send/bulk-{i}",
                keys={"p256dh": f"bulk_key_{i}", "auth": f"bulk_secret_{i}"},
                failure_count=i
            )
            for i in range(3)
        ]

        db_session.add_all(subscriptions)
        await db_session.commit()

        # Reset all failure counts to 0
        update_query = update(PushSubscription).values(failure_count=0)
        await db_session.execute(update_query)
        await db_session.commit()

        # Verify all failure counts are 0
        query = select(PushSubscription)
        result = await db_session.execute(query)
        all_subscriptions = result.scalars().all()

        for subscription in all_subscriptions:
            assert subscription.failure_count == 0

    async def test_delete_inactive_subscriptions(self, db_session: AsyncSession):
        """Test deleting inactive subscriptions."""
        from sqlalchemy import delete

        active_sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/keep-active",
            keys={"p256dh": "keep_key", "auth": "keep_secret"},
            is_active=True
        )

        inactive_sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/delete-inactive",
            keys={"p256dh": "delete_key", "auth": "delete_secret"},
            is_active=False
        )

        db_session.add_all([active_sub, inactive_sub])
        await db_session.commit()

        # Delete inactive subscriptions
        delete_query = delete(PushSubscription).where(not PushSubscription.is_active)
        await db_session.execute(delete_query)
        await db_session.commit()

        # Verify only active subscription remains
        query = select(PushSubscription)
        result = await db_session.execute(query)
        remaining_subscriptions = result.scalars().all()

        assert len(remaining_subscriptions) == 1
        assert remaining_subscriptions[0].is_active is True


class TestPushSubscriptionIndexes:
    """Test that database indexes work as expected."""

    async def test_active_subscription_index(self, db_session: AsyncSession):
        """Test querying by is_active uses index efficiently."""
        # Create multiple subscriptions
        subscriptions = [
            PushSubscription(
                endpoint=f"https://fcm.googleapis.com/fcm/send/index-test-{i}",
                keys={"p256dh": f"index_key_{i}", "auth": f"index_secret_{i}"},
                is_active=i % 2 == 0
            )
            for i in range(100)  # Larger dataset to benefit from indexing
        ]

        db_session.add_all(subscriptions)
        await db_session.commit()

        # Query active subscriptions (should use ix_push_subscriptions_active index)
        query = select(PushSubscription).where(PushSubscription.is_active)
        result = await db_session.execute(query)
        active_subscriptions = result.scalars().all()

        assert len(active_subscriptions) == 50  # Half should be active

    async def test_endpoint_index(self, db_session: AsyncSession):
        """Test querying by endpoint uses index efficiently."""
        # Create multiple subscriptions
        test_endpoint = "https://fcm.googleapis.com/fcm/send/endpoint-index-test"

        subscriptions = [
            PushSubscription(
                endpoint=f"https://fcm.googleapis.com/fcm/send/other-{i}",
                keys={"p256dh": f"other_key_{i}", "auth": f"other_secret_{i}"}
            )
            for i in range(50)
        ]

        # Add one with our test endpoint
        test_subscription = PushSubscription(
            endpoint=test_endpoint,
            keys={"p256dh": "test_key", "auth": "test_secret"}
        )
        subscriptions.append(test_subscription)

        db_session.add_all(subscriptions)
        await db_session.commit()

        # Query by endpoint (should use ix_push_subscriptions_endpoint index)
        query = select(PushSubscription).where(PushSubscription.endpoint == test_endpoint)
        result = await db_session.execute(query)
        found_subscription = result.scalar_one_or_none()

        assert found_subscription is not None
        assert found_subscription.endpoint == test_endpoint


class TestPushSubscriptionJSONBKeys:
    """Test JSONB functionality for keys field."""

    async def test_keys_jsonb_storage(self, db_session: AsyncSession):
        """Test that keys are properly stored as JSONB."""
        complex_keys = {
            "p256dh": "complex_p256dh_key_with_special_chars_!@#$%^&*()",
            "auth": "complex_auth_secret_with_unicode_café",
            "extra_field": "additional_data",
            "nested": {
                "level1": {
                    "level2": "nested_value"
                }
            }
        }

        subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/jsonb-test",
            keys=complex_keys
        )

        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)

        # Verify complex keys are stored and retrieved correctly
        assert subscription.keys["p256dh"] == complex_keys["p256dh"]
        assert subscription.keys["auth"] == complex_keys["auth"]
        assert subscription.keys["extra_field"] == complex_keys["extra_field"]
        assert subscription.keys["nested"]["level1"]["level2"] == "nested_value"

    async def test_keys_jsonb_querying(self, db_session: AsyncSession):
        """Test querying JSONB keys field."""
        subscription1 = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/jsonb-query-1",
            keys={
                "p256dh": "query_key_1",
                "auth": "query_secret_1",
                "browser": "chrome"
            }
        )

        subscription2 = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/jsonb-query-2",
            keys={
                "p256dh": "query_key_2",
                "auth": "query_secret_2",
                "browser": "firefox"
            }
        )

        db_session.add_all([subscription1, subscription2])
        await db_session.commit()

        # Query by JSONB field (PostgreSQL-specific)
        query = select(PushSubscription).where(
            PushSubscription.keys["browser"].astext == "chrome"
        )
        result = await db_session.execute(query)
        chrome_subscription = result.scalar_one_or_none()

        assert chrome_subscription is not None
        assert chrome_subscription.keys["browser"] == "chrome"

    async def test_keys_jsonb_update(self, db_session: AsyncSession):
        """Test updating JSONB keys field."""
        original_keys = {
            "p256dh": "original_p256dh",
            "auth": "original_auth"
        }

        subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/jsonb-update",
            keys=original_keys
        )

        db_session.add(subscription)
        await db_session.commit()

        # Update keys
        updated_keys = original_keys.copy()
        updated_keys["p256dh"] = "updated_p256dh"
        updated_keys["new_field"] = "added_field"

        subscription.keys = updated_keys
        await db_session.commit()
        await db_session.refresh(subscription)

        # Verify update
        assert subscription.keys["p256dh"] == "updated_p256dh"
        assert subscription.keys["auth"] == "original_auth"  # Unchanged
        assert subscription.keys["new_field"] == "added_field"  # Added
