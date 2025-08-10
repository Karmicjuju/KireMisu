"""API endpoints for dashboard statistics."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from kiremisu.database.connection import get_db
from kiremisu.core.auth import get_current_user
from kiremisu.database.models import Series, Chapter
from kiremisu.database.schemas import DashboardStatsResponse, ChapterResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> DashboardStatsResponse:
    """Get comprehensive dashboard statistics."""

    # Get total series count
    total_series_result = await db.execute(select(func.count()).select_from(Series))
    total_series = total_series_result.scalar() or 0

    # Get total chapters count
    total_chapters_result = await db.execute(select(func.count()).select_from(Chapter))
    total_chapters = total_chapters_result.scalar() or 0

    # Get total read chapters count
    read_chapters_result = await db.execute(select(func.count()).where(Chapter.is_read == True))
    read_chapters = read_chapters_result.scalar() or 0

    # Calculate overall reading progress percentage
    reading_progress_percentage = 0.0
    if total_chapters > 0:
        reading_progress_percentage = (read_chapters / total_chapters) * 100

    # Get recent activity (recently read chapters, up to 10)
    recent_activity_result = await db.execute(
        select(Chapter)
        .where(Chapter.is_read == True)
        .order_by(Chapter.read_at.desc().nulls_last())
        .limit(10)
    )
    recent_activity_chapters = recent_activity_result.scalars().all()

    # Get series counts by reading status
    series_status_result = await db.execute(
        select(
            func.count(case((Series.read_chapters == 0, 1))).label("unread"),
            func.count(
                case(
                    (
                        (Series.read_chapters > 0) & (Series.read_chapters < Series.total_chapters),
                        1,
                    )
                )
            ).label("in_progress"),
            func.count(
                case(
                    (
                        (Series.read_chapters > 0)
                        & (Series.read_chapters >= Series.total_chapters),
                        1,
                    )
                )
            ).label("completed"),
        ).select_from(Series)
    )
    status_counts = series_status_result.first()

    series_by_status = {
        "unread": status_counts.unread if status_counts else 0,
        "in_progress": status_counts.in_progress if status_counts else 0,
        "completed": status_counts.completed if status_counts else 0,
    }

    return DashboardStatsResponse(
        total_series=total_series,
        total_chapters=total_chapters,
        read_chapters=read_chapters,
        reading_progress_percentage=round(reading_progress_percentage, 2),
        recent_activity=[
            ChapterResponse.from_model(chapter) for chapter in recent_activity_chapters
        ],
        series_by_status=series_by_status,
        last_updated=datetime.utcnow(),
    )
