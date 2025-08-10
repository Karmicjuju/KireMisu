"""Push notification subscription and management API endpoints."""

from typing import Optional, Dict, Any, List
from uuid import UUID
import json
import base64
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from pywebpush import webpush, WebPushException
from pydantic import BaseModel, Field

from kiremisu.database.connection import get_db
from kiremisu.database.models import PushSubscription, Notification, Series, Chapter
from kiremisu.core.config import get_settings

# Simple metrics stub
def track_api_request(operation: str):
    """Stub for API request tracking."""
    logger.debug(f"API request: {operation}")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/push", tags=["push-notifications"])
settings = get_settings()


class VapidKeysResponse(BaseModel):
    """VAPID public key response."""

    public_key: str


class PushSubscriptionCreate(BaseModel):
    """Push subscription creation request."""

    endpoint: str
    keys: Dict[str, str]
    expires_at: Optional[datetime] = None
    user_agent: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/...",
                "keys": {"p256dh": "public_key_here", "auth": "auth_secret_here"},
                "user_agent": "Mozilla/5.0...",
            }
        }


class PushSubscriptionResponse(BaseModel):
    """Push subscription response."""

    id: UUID
    endpoint: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime]
    failure_count: int


class TestPushRequest(BaseModel):
    """Test push notification request."""

    title: str = "Test Notification"
    body: str = "This is a test notification from KireMisu"
    icon: Optional[str] = None
    badge: Optional[str] = None
    vibrate: Optional[List[int]] = [200, 100, 200]
    data: Optional[Dict[str, Any]] = None


class PushNotificationRequest(BaseModel):
    """Manual push notification request."""

    subscription_ids: Optional[List[UUID]] = Field(
        None, description="Specific subscriptions to target"
    )
    title: str
    body: str
    type: str = "system_alert"
    icon: Optional[str] = None
    badge: Optional[str] = None
    tag: Optional[str] = None
    require_interaction: bool = False
    silent: bool = False
    data: Optional[Dict[str, Any]] = None


@router.get("/vapid-public-key", response_model=VapidKeysResponse)
async def get_vapid_public_key():
    """Get the VAPID public key for push subscriptions."""
    track_api_request("push_get_vapid_key")

    vapid_public_key = settings.vapid_public_key
    if not vapid_public_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured",
        )

    return VapidKeysResponse(public_key=vapid_public_key)


@router.post("/subscribe", response_model=PushSubscriptionResponse)
async def subscribe_to_push(
    subscription: PushSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Subscribe to push notifications."""
    track_api_request("push_subscribe")

    # Check if subscription already exists
    existing = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == subscription.endpoint)
    )
    existing_sub = existing.scalar_one_or_none()

    if existing_sub:
        # Update existing subscription
        existing_sub.keys = subscription.keys
        existing_sub.is_active = True
        existing_sub.failure_count = 0
        existing_sub.user_agent = subscription.user_agent
        existing_sub.expires_at = subscription.expires_at
        await db.commit()

        logger.info(f"Updated existing push subscription: {existing_sub.id}")

        return PushSubscriptionResponse(
            id=existing_sub.id,
            endpoint=existing_sub.endpoint,
            is_active=existing_sub.is_active,
            created_at=existing_sub.created_at,
            last_used=existing_sub.last_used,
            failure_count=existing_sub.failure_count,
        )

    # Create new subscription
    new_subscription = PushSubscription(
        endpoint=subscription.endpoint,
        keys=subscription.keys,
        user_agent=subscription.user_agent,
        expires_at=subscription.expires_at,
        is_active=True,
        failure_count=0,
    )

    db.add(new_subscription)
    await db.commit()
    await db.refresh(new_subscription)

    logger.info(f"Created new push subscription: {new_subscription.id}")

    return PushSubscriptionResponse(
        id=new_subscription.id,
        endpoint=new_subscription.endpoint,
        is_active=new_subscription.is_active,
        created_at=new_subscription.created_at,
        last_used=new_subscription.last_used,
        failure_count=new_subscription.failure_count,
    )


@router.delete("/unsubscribe/{subscription_id}")
async def unsubscribe_from_push(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe from push notifications."""
    track_api_request("push_unsubscribe")

    result = await db.execute(
        select(PushSubscription).where(PushSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    await db.delete(subscription)
    await db.commit()

    logger.info(f"Deleted push subscription: {subscription_id}")

    return {"message": "Successfully unsubscribed"}


@router.get("/subscriptions", response_model=List[PushSubscriptionResponse])
async def list_subscriptions(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all push subscriptions."""
    track_api_request("push_list_subscriptions")

    query = select(PushSubscription)
    if active_only:
        query = query.where(PushSubscription.is_active == True)

    result = await db.execute(query.order_by(PushSubscription.created_at.desc()))
    subscriptions = result.scalars().all()

    return [
        PushSubscriptionResponse(
            id=sub.id,
            endpoint=sub.endpoint,
            is_active=sub.is_active,
            created_at=sub.created_at,
            last_used=sub.last_used,
            failure_count=sub.failure_count,
        )
        for sub in subscriptions
    ]


@router.post("/test/{subscription_id}")
async def test_push_notification(
    subscription_id: UUID,
    request: TestPushRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a test push notification to a specific subscription."""
    track_api_request("push_test_notification")

    # Get subscription
    result = await db.execute(
        select(PushSubscription).where(
            and_(PushSubscription.id == subscription_id, PushSubscription.is_active == True)
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Active subscription not found"
        )

    # Send test notification
    success = await send_push_notification(
        subscription=subscription,
        title=request.title,
        body=request.body,
        icon=request.icon,
        badge=request.badge,
        data=request.data or {"type": "test", "timestamp": datetime.utcnow().isoformat()},
        db=db,
    )

    if success:
        return {"message": "Test notification sent successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification",
        )


@router.post("/send")
async def send_manual_push(
    request: PushNotificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send a manual push notification."""
    track_api_request("push_send_manual")

    # Get target subscriptions
    query = select(PushSubscription).where(PushSubscription.is_active == True)

    if request.subscription_ids:
        query = query.where(PushSubscription.id.in_(request.subscription_ids))

    result = await db.execute(query)
    subscriptions = result.scalars().all()

    if not subscriptions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscriptions found"
        )

    # Queue sending notifications in background
    background_tasks.add_task(
        send_push_to_multiple,
        subscriptions=subscriptions,
        title=request.title,
        body=request.body,
        notification_type=request.type,
        icon=request.icon,
        badge=request.badge,
        tag=request.tag,
        require_interaction=request.require_interaction,
        silent=request.silent,
        data=request.data,
    )

    return {
        "message": f"Queued push notification for {len(subscriptions)} subscriptions",
        "subscription_count": len(subscriptions),
    }


async def send_push_notification(
    subscription: PushSubscription,
    title: str,
    body: str,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    tag: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    actions: Optional[List[Dict[str, str]]] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Send a push notification to a single subscription."""
    try:
        vapid_private_key = settings.vapid_private_key
        vapid_claims = settings.vapid_claims

        if not vapid_private_key or not vapid_claims:
            logger.error("VAPID keys not configured")
            return False

        # Prepare notification payload
        payload = {
            "title": title,
            "body": body,
            "icon": icon or "/icon-192x192.png",
            "badge": badge or "/badge-72x72.png",
            "tag": tag or f"kiremisu-{datetime.utcnow().timestamp()}",
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if actions:
            payload["actions"] = actions

        # Send the notification
        response = webpush(
            subscription_info={"endpoint": subscription.endpoint, "keys": subscription.keys},
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims,
        )

        # Update last_used timestamp
        if db:
            subscription.last_used = datetime.utcnow()
            subscription.failure_count = 0
            await db.commit()

        logger.info(f"Push notification sent successfully to {subscription.id}")
        return True

    except WebPushException as e:
        logger.error(f"WebPush error for subscription {subscription.id}: {e}")

        # Handle different error codes
        if e.response and e.response.status_code == 410:
            # Subscription expired, mark as inactive
            if db:
                subscription.is_active = False
                await db.commit()
            logger.info(f"Subscription {subscription.id} expired, marked as inactive")
        elif db:
            # Increment failure count
            subscription.failure_count += 1
            if subscription.failure_count >= 5:
                subscription.is_active = False
            await db.commit()

        return False

    except Exception as e:
        logger.error(f"Error sending push notification to {subscription.id}: {e}")
        return False


async def send_push_to_multiple(
    subscriptions: List[PushSubscription],
    title: str,
    body: str,
    notification_type: str = "system_alert",
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    tag: Optional[str] = None,
    require_interaction: bool = False,
    silent: bool = False,
    data: Optional[Dict[str, Any]] = None,
):
    """Send push notifications to multiple subscriptions."""
    successful = 0
    failed = 0

    for subscription in subscriptions:
        notification_data = data or {}
        notification_data["type"] = notification_type
        notification_data["requireInteraction"] = require_interaction
        notification_data["silent"] = silent

        success = await send_push_notification(
            subscription=subscription,
            title=title,
            body=body,
            icon=icon,
            badge=badge,
            tag=tag,
            data=notification_data,
        )

        if success:
            successful += 1
        else:
            failed += 1

    logger.info(f"Push notifications sent: {successful} successful, {failed} failed")
    return {"successful": successful, "failed": failed}


async def send_chapter_notification(
    db: AsyncSession, series: Series, chapter: Chapter, notification: Notification
):
    """Send push notification for a new chapter."""
    # Get all active push subscriptions
    result = await db.execute(select(PushSubscription).where(PushSubscription.is_active == True))
    subscriptions = result.scalars().all()

    if not subscriptions:
        return

    # Prepare notification data
    title = f"New Chapter: {series.title}"
    body = f"Chapter {chapter.chapter_number}: {chapter.title or 'Untitled'}"

    actions = [
        {"action": "read", "title": "Read Now", "icon": "/icons/read.png"},
        {"action": "later", "title": "Read Later", "icon": "/icons/later.png"},
    ]

    data = {
        "type": "new_chapter",
        "notificationId": str(notification.id),
        "seriesId": str(series.id),
        "chapterId": str(chapter.id),
        "chapterNumber": chapter.chapter_number,
        "seriesTitle": series.title,
    }

    # Send to all subscriptions
    await send_push_to_multiple(
        subscriptions=subscriptions,
        title=title,
        body=body,
        notification_type="new_chapter",
        icon=series.cover_url,
        data=data,
    )
