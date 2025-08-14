"""Push notification subscription and management API endpoints."""

import asyncio
import base64
import html
import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, HttpUrl, validator
from pywebpush import WebPushException, webpush
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.config import get_settings
from kiremisu.core.unified_auth import get_current_user
from kiremisu.database.connection import get_db, get_db_session
from kiremisu.database.models import Chapter, Notification, PushSubscription, Series, User


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

    endpoint: HttpUrl
    keys: dict[str, str]
    expires_at: datetime | None = None
    user_agent: str | None = Field(None, max_length=500)

    @validator('endpoint')
    def validate_endpoint(self, v):
        """Validate push notification endpoint URL."""
        url = str(v)

        # Parse URL and validate structure
        parsed = urlparse(url)

        # Must use HTTPS (except localhost for development)
        if parsed.scheme != 'https':
            if not (parsed.netloc in ['localhost', '127.0.0.1'] or parsed.netloc.startswith('localhost:')):
                raise ValueError("Push notification endpoints must use HTTPS")

        # Check for valid push service domains (exact match for security)
        valid_domains = {
            'fcm.googleapis.com',
            'updates.push.services.mozilla.com',
            'updates-autopush.stage.mozaws.net',  # Mozilla staging
            'updates-autopush.dev.mozaws.net',    # Mozilla dev
            'notify.windows.com',
            'push.apple.com',
            'web.push.apple.com',
            'android.googleapis.com',
            'localhost',  # Development only
            '127.0.0.1'   # Development only
        }

        # Extract hostname without port
        hostname = parsed.netloc.split(':')[0]

        if hostname not in valid_domains:
            raise ValueError(f"Invalid push service endpoint domain: {hostname}. Only trusted push services are allowed.")

        # Additional security checks
        if len(url) > 2000:  # Reasonable URL length limit
            raise ValueError("Push notification endpoint URL too long")

        # Check for suspicious patterns
        suspicious_patterns = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in suspicious_patterns):
            raise ValueError("Invalid URL scheme detected")

        return v

    @validator('keys')
    def validate_keys(self, v):
        """Validate push subscription keys."""
        required_keys = {'p256dh', 'auth'}
        if not required_keys.issubset(v.keys()):
            raise ValueError(f"Missing required keys. Required: {required_keys}")

        # Validate base64 format
        for key, value in v.items():
            if key in required_keys:
                try:
                    # Check if it's valid base64 URL-safe
                    base64.urlsafe_b64decode(value + '==')  # Add padding
                except Exception:
                    raise ValueError(f"Invalid base64 format for key: {key}")

        return v

    @validator('user_agent')
    def sanitize_user_agent(self, v):
        """Sanitize user agent string to prevent XSS and injection attacks."""
        if not v:
            return None

        # Strip whitespace and limit length
        v = v.strip()[:500]

        # HTML escape to prevent XSS
        v = html.escape(v)

        # Additional sanitization: remove control characters and non-printable chars
        v = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', v)

        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'data:',
            r'on\w+\s*=',  # Event handlers like onclick=
        ]

        for pattern in dangerous_patterns:
            v = re.sub(pattern, '', v, flags=re.IGNORECASE)

        return v if v else None

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
    last_used: datetime | None
    failure_count: int


class TestPushRequest(BaseModel):
    """Test push notification request."""

    title: str = "Test Notification"
    body: str = "This is a test notification from KireMisu"
    icon: str | None = None
    badge: str | None = None
    vibrate: list[int] | None = [200, 100, 200]
    data: dict[str, Any] | None = None


class PushNotificationRequest(BaseModel):
    """Manual push notification request."""

    subscription_ids: list[UUID] | None = Field(
        None, description="Specific subscriptions to target"
    )
    title: str
    body: str
    type: str = "system_alert"
    icon: str | None = None
    badge: str | None = None
    tag: str | None = None
    require_interaction: bool = False
    silent: bool = False
    data: dict[str, Any] | None = None


@router.get("/vapid-public-key", response_model=VapidKeysResponse)
async def get_vapid_public_key(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get the VAPID public key for push subscriptions.

    This endpoint can be accessed without authentication but has rate limiting.
    """
    track_api_request("push_get_vapid_key")

    # All requests now require JWT authentication

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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subscribe to push notifications. Requires authentication."""
    track_api_request("push_subscribe")

    # Get user ID - handle both User model and dict for backwards compatibility
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')

    # Check if subscription already exists for this user
    endpoint_str = str(subscription.endpoint)
    existing = await db.execute(
        select(PushSubscription).where(
            and_(
                PushSubscription.endpoint == endpoint_str,
                PushSubscription.user_id == user_id
            )
        )
    )
    existing_sub = existing.scalar_one_or_none()

    if existing_sub:
        # Update existing subscription
        existing_sub.keys = subscription.keys
        existing_sub.is_active = True
        existing_sub.failure_count = 0
        existing_sub.user_agent = subscription.user_agent
        existing_sub.expires_at = subscription.expires_at

        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription"
            )

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
        user_id=user_id,
        endpoint=endpoint_str,
        keys=subscription.keys,
        user_agent=subscription.user_agent,
        expires_at=subscription.expires_at,
        is_active=True,
        failure_count=0,
    )

    db.add(new_subscription)

    try:
        await db.commit()
        await db.refresh(new_subscription)
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )

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
    current_user: User = Depends(get_current_user),
):
    """Unsubscribe from push notifications. Requires authentication."""
    track_api_request("push_unsubscribe")

    # Get user ID
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')

    result = await db.execute(
        select(PushSubscription).where(
            and_(
                PushSubscription.id == subscription_id,
                PushSubscription.user_id == user_id
            )
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    try:
        await db.delete(subscription)
        await db.commit()
        logger.info(f"Deleted push subscription: {subscription_id}")
        return {"message": "Successfully unsubscribed"}
    except Exception as e:
        logger.error(f"Failed to delete subscription: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe"
        )


class UnsubscribeByEndpointRequest(BaseModel):
    """Request to unsubscribe by endpoint."""
    endpoint: str


@router.post("/unsubscribe")
async def unsubscribe_by_endpoint(
    request_data: UnsubscribeByEndpointRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unsubscribe from push notifications by endpoint. Requires authentication."""
    track_api_request("push_unsubscribe_by_endpoint")

    # Get user ID
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')

    result = await db.execute(
        select(PushSubscription).where(
            and_(
                PushSubscription.endpoint == request_data.endpoint,
                PushSubscription.user_id == user_id
            )
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        # Don't error if subscription not found - might already be cleaned up
        return {"message": "Successfully unsubscribed"}

    try:
        await db.delete(subscription)
        await db.commit()
        logger.info(f"Deleted push subscription by endpoint: {subscription.id}")
        return {"message": "Successfully unsubscribed"}
    except Exception as e:
        logger.error(f"Failed to delete subscription by endpoint: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe"
        )


@router.get("/subscriptions", response_model=list[PushSubscriptionResponse])
async def list_subscriptions(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List push subscriptions for current user. Requires authentication."""
    track_api_request("push_list_subscriptions")

    # Get user ID
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')

    query = select(PushSubscription).where(PushSubscription.user_id == user_id)
    if active_only:
        query = query.where(PushSubscription.is_active)

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
    current_user: User = Depends(get_current_user),
):
    """Send a test push notification to a specific subscription. Requires authentication."""
    track_api_request("push_test_notification")

    # Get user ID
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')

    # Get subscription for current user only
    result = await db.execute(
        select(PushSubscription).where(
            and_(
                PushSubscription.id == subscription_id,
                PushSubscription.user_id == user_id,
                PushSubscription.is_active
            )
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
    current_user: User = Depends(get_current_user),
):
    """Send a manual push notification to user's subscriptions. Requires authentication."""
    track_api_request("push_send_manual")

    # Get user ID
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')

    # Get target subscriptions for current user only
    query = select(PushSubscription).where(
        and_(
            PushSubscription.is_active,
            PushSubscription.user_id == user_id
        )
    )

    if request.subscription_ids:
        query = query.where(PushSubscription.id.in_(request.subscription_ids))

    result = await db.execute(query)
    subscriptions = result.scalars().all()

    if not subscriptions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscriptions found"
        )

    # Queue sending notifications in background with fresh DB session
    subscription_ids = [str(sub.id) for sub in subscriptions]
    background_tasks.add_task(
        send_push_to_multiple_background,
        subscription_ids=subscription_ids,
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
    icon: str | None = None,
    badge: str | None = None,
    tag: str | None = None,
    data: dict[str, Any] | None = None,
    actions: list[dict[str, str]] | None = None,
    db: AsyncSession | None = None,
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
        webpush(
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
    subscriptions: list[PushSubscription],
    title: str,
    body: str,
    notification_type: str = "system_alert",
    icon: str | None = None,
    badge: str | None = None,
    tag: str | None = None,
    require_interaction: bool = False,
    silent: bool = False,
    data: dict[str, Any] | None = None,
    batch_size: int = 10,  # Process in batches to avoid overwhelming the system
    db: AsyncSession | None = None,  # Pass database session for subscription updates
):
    """Send push notifications to multiple subscriptions in parallel."""

    async def send_single(subscription: PushSubscription) -> bool:
        """Helper to send a single notification."""
        notification_data = data or {}
        notification_data["type"] = notification_type
        notification_data["requireInteraction"] = require_interaction
        notification_data["silent"] = silent

        return await send_push_notification(
            subscription=subscription,
            title=title,
            body=body,
            icon=icon,
            badge=badge,
            tag=tag,
            data=notification_data,
            db=db,  # Pass database session for subscription updates
        )

    # Process subscriptions in batches to avoid too many concurrent connections
    results = []
    for i in range(0, len(subscriptions), batch_size):
        batch = subscriptions[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[send_single(sub) for sub in batch],
            return_exceptions=True  # Don't fail the whole batch if one fails
        )

        # Handle results, counting successes and failures
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Exception during push send: {result}")
                results.append(False)
            else:
                results.append(result)

    successful = sum(1 for r in results if r is True)
    failed = len(results) - successful

    logger.info(f"Push notifications sent: {successful} successful, {failed} failed")
    return {"successful": successful, "failed": failed}


async def send_push_to_multiple_background(
    subscription_ids: list[str],
    title: str,
    body: str,
    notification_type: str = "system_alert",
    icon: str | None = None,
    badge: str | None = None,
    tag: str | None = None,
    require_interaction: bool = False,
    silent: bool = False,
    data: dict[str, Any] | None = None,
):
    """Background task-safe version of send_push_to_multiple that creates its own DB session."""
    async with get_db_session() as db:
        try:
            # Fetch subscriptions by IDs
            from uuid import UUID
            subscription_uuids = [UUID(sub_id) for sub_id in subscription_ids]

            result = await db.execute(
                select(PushSubscription).where(
                    and_(
                        PushSubscription.id.in_(subscription_uuids),
                        PushSubscription.is_active
                    )
                )
            )
            subscriptions = result.scalars().all()

            if subscriptions:
                # Use the regular send_push_to_multiple with fresh session
                await send_push_to_multiple(
                    subscriptions=subscriptions,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    icon=icon,
                    badge=badge,
                    tag=tag,
                    require_interaction=require_interaction,
                    silent=silent,
                    data=data,
                    db=db,  # Pass the database session
                )
            else:
                logger.warning("No active subscriptions found for background push task")

        except Exception as e:
            logger.error(f"Error in background push notification task: {e}")


async def send_chapter_notification(
    db: AsyncSession, series: Series, chapter: Chapter, notification: Notification
):
    """Send push notification for a new chapter."""
    # Get all active push subscriptions
    result = await db.execute(select(PushSubscription).where(PushSubscription.is_active))
    subscriptions = result.scalars().all()

    if not subscriptions:
        return

    # Prepare notification data
    title = f"New Chapter: {series.title}"
    body = f"Chapter {chapter.chapter_number}: {chapter.title or 'Untitled'}"


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
        db=db,  # Pass database session for subscription updates
    )
