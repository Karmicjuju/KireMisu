from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import get_async_session

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_async_session)):
    """Health check endpoint with database connectivity test."""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "service": "kiremisu-api"
    }