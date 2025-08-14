"""API endpoints for notifications management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.core.unified_auth import get_current_user
from kiremisu.database.connection import get_db
from kiremisu.database.schemas import (
    NotificationBulkMarkReadResponse,
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationResponse,
    NotificationStatsResponse,
)
from kiremisu.database.utils import log_slow_query, with_db_retry
from kiremisu.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationListResponse)
@with_db_retry(max_attempts=2)
@log_slow_query("get_notifications", 2.0)
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
) -> NotificationListResponse:
    """Get paginated list of notifications."""
    notifications = await NotificationService.get_notifications(
        db=db, skip=skip, limit=limit, unread_only=unread_only
    )

    return NotificationListResponse(
        notifications=[NotificationResponse.from_model(n) for n in notifications],
        total=len(notifications),
        unread_only=unread_only,
    )


@router.get("/count", response_model=dict)
async def get_notification_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get count of unread notifications."""
    unread_count = await NotificationService.get_unread_count(db)

    return {
        "unread_count": unread_count,
    }


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> NotificationStatsResponse:
    """Get comprehensive notification statistics."""
    stats = await NotificationService.get_notification_stats(db)

    return NotificationStatsResponse(
        total_notifications=stats["total_notifications"],
        unread_notifications=stats["unread_notifications"],
        read_notifications=stats["read_notifications"],
        notifications_by_type=stats["notifications_by_type"],
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> NotificationResponse:
    """Get a specific notification by ID."""
    notification = await NotificationService.get_notification_by_id(db, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return NotificationResponse.from_model(notification)


@router.post("/{notification_id}/read", response_model=NotificationMarkReadResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> NotificationMarkReadResponse:
    """Mark a single notification as read."""
    notification = await NotificationService.mark_notification_read(db, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Get updated unread count
    unread_count = await NotificationService.get_unread_count(db)

    return NotificationMarkReadResponse(
        id=notification.id,
        is_read=notification.is_read,
        read_at=notification.read_at,
        unread_count=unread_count,
    )


@router.post("/read-all", response_model=NotificationBulkMarkReadResponse)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> NotificationBulkMarkReadResponse:
    """Mark all notifications as read."""
    marked_count = await NotificationService.mark_all_read(db)

    return NotificationBulkMarkReadResponse(
        marked_count=marked_count,
        unread_count=0,  # Should be 0 after marking all as read
    )
