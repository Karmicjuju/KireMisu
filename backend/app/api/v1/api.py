from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, series

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(series.router, prefix="/series", tags=["series"])