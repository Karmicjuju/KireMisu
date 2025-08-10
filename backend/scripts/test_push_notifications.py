#!/usr/bin/env python3
"""Script to test push notifications functionality.

This script provides utilities to:
1. Generate VAPID keys for development
2. Subscribe a test endpoint
3. Send test push notifications
4. Simulate new chapter notifications
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from py_vapid import Vapid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.config import settings
from kiremisu.database.connection import get_db_session
from kiremisu.database.models import PushSubscription, Series, Chapter, Notification
from kiremisu.api.push_notifications import (
    send_push_notification,
    send_chapter_notification,
    send_push_to_multiple,
)


async def generate_vapid_keys():
    """Generate new VAPID keys for development."""
    print("🔑 Generating VAPID keys...")

    import tempfile
    import base64
    from cryptography.hazmat.primitives import serialization

    vapid = Vapid()
    vapid.generate_keys()

    # Extract keys and convert to base64 for storage
    public_key_bytes = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    private_key_bytes = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_key = base64.urlsafe_b64encode(public_key_bytes).decode('ascii').strip('=')
    private_key = private_key_bytes.decode('ascii')

    print("\n✅ VAPID keys generated successfully!")
    print("\nAdd these to your .env file:")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print(f'VAPID_CLAIMS={{"sub": "mailto:admin@kiremisu.local"}}')

    return public_key, private_key


async def create_test_subscription(db: AsyncSession) -> PushSubscription:
    """Create a test push subscription."""
    print("\n📱 Creating test subscription...")

    # Create a dummy subscription for testing
    test_subscription = PushSubscription(
        endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint",
        keys={"p256dh": "test-public-key", "auth": "test-auth-secret"},
        user_agent="Test Script",
        is_active=True,
        failure_count=0,
    )

    db.add(test_subscription)
    await db.commit()
    await db.refresh(test_subscription)

    print(f"✅ Created test subscription: {test_subscription.id}")
    return test_subscription


async def send_test_notification(db: AsyncSession, subscription_id: Optional[UUID] = None):
    """Send a test push notification."""
    print("\n📤 Sending test notification...")

    # Get subscription
    if subscription_id:
        query = select(PushSubscription).where(PushSubscription.id == subscription_id)
    else:
        query = select(PushSubscription).where(PushSubscription.is_active == True).limit(1)

    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        print("❌ No active subscription found")
        return

    # Send test notification
    success = await send_push_notification(
        subscription=subscription,
        title="Test Notification",
        body="This is a test notification from KireMisu",
        icon="/icon-192x192.png",
        badge="/badge-72x72.png",
        data={"type": "test", "timestamp": "2025-08-10T12:00:00Z"},
        db=db,
    )

    if success:
        print("✅ Test notification sent successfully!")
    else:
        print("❌ Failed to send test notification")


async def simulate_new_chapter(db: AsyncSession):
    """Simulate a new chapter notification."""
    print("\n📚 Simulating new chapter notification...")

    # Get a random series (or create one for testing)
    result = await db.execute(select(Series).limit(1))
    series = result.scalar_one_or_none()

    if not series:
        print("Creating test series...")
        series = Series(
            title_primary="Test Manga",
            author="Test Author",
            description="A test manga series",
            watching_enabled=True,
        )
        db.add(series)
        await db.commit()
        await db.refresh(series)

    # Create a test chapter
    chapter = Chapter(
        series_id=series.id,
        chapter_number=99.0,
        title="Test Chapter",
        volume_number=10,
        page_count=20,
    )
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)

    # Create notification
    notification = Notification(
        notification_type="new_chapter",
        title=f"New chapter available: {series.title_primary}",
        message=f"Chapter {chapter.chapter_number}: {chapter.title or 'Untitled'}",
        series_id=series.id,
        chapter_id=chapter.id,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Send push notification
    await send_chapter_notification(db, series, chapter, notification)

    print("✅ Chapter notification sent!")
    print(f"   Series: {series.title_primary}")
    print(f"   Chapter: {chapter.chapter_number} - {chapter.title}")


async def list_subscriptions(db: AsyncSession):
    """List all push subscriptions."""
    print("\n📋 Listing push subscriptions...")

    result = await db.execute(select(PushSubscription).order_by(PushSubscription.created_at.desc()))
    subscriptions = result.scalars().all()

    if not subscriptions:
        print("No subscriptions found")
        return

    print(f"\nFound {len(subscriptions)} subscription(s):")
    for sub in subscriptions:
        status = "✅ Active" if sub.is_active else "❌ Inactive"
        print(f"\n  ID: {sub.id}")
        print(f"  Status: {status}")
        print(f"  Endpoint: {sub.endpoint[:50]}...")
        print(f"  Created: {sub.created_at}")
        print(f"  Last Used: {sub.last_used or 'Never'}")
        print(f"  Failures: {sub.failure_count}")


async def broadcast_test(db: AsyncSession):
    """Send a broadcast notification to all active subscriptions."""
    print("\n📢 Broadcasting test notification...")

    result = await db.execute(select(PushSubscription).where(PushSubscription.is_active == True))
    subscriptions = result.scalars().all()

    if not subscriptions:
        print("No active subscriptions found")
        return

    print(f"Broadcasting to {len(subscriptions)} subscription(s)...")

    results = await send_push_to_multiple(
        subscriptions=subscriptions,
        title="KireMisu Broadcast",
        body="This is a broadcast test notification",
        notification_type="system_alert",
        data={"broadcast": True},
    )

    print(f"✅ Broadcast complete: {results}")


async def main():
    """Main entry point."""
    print("🚀 KireMisu Push Notification Test Script")
    print("=" * 50)

    # Check if VAPID keys are configured
    if not settings.vapid_public_key or not settings.vapid_private_key:
        print("\n⚠️  VAPID keys not configured!")
        print("Would you like to generate them? (y/n): ", end="")

        if input().lower() == "y":
            await generate_vapid_keys()
            print("\n⚠️  Please add the keys to your .env file and restart the script")
            return
        else:
            print("\n❌ Cannot proceed without VAPID keys")
            return

    # Get database session
    async with get_db_session() as db:
        while True:
            print("\n" + "=" * 50)
            print("Select an action:")
            print("1. Generate VAPID keys")
            print("2. Create test subscription")
            print("3. Send test notification")
            print("4. Simulate new chapter notification")
            print("5. List all subscriptions")
            print("6. Broadcast to all subscriptions")
            print("0. Exit")
            print("\nChoice: ", end="")

            choice = input().strip()

            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                await generate_vapid_keys()
            elif choice == "2":
                await create_test_subscription(db)
            elif choice == "3":
                await send_test_notification(db)
            elif choice == "4":
                await simulate_new_chapter(db)
            elif choice == "5":
                await list_subscriptions(db)
            elif choice == "6":
                await broadcast_test(db)
            else:
                print("❌ Invalid choice")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
