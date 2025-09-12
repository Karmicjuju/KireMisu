from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, series, storage, search, reader, progress, chapters, library_paths, filter_presets

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(filter_presets.router, prefix="/filter-presets", tags=["filter-presets"])
api_router.include_router(chapters.router, prefix="/chapters", tags=["chapters"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(reader.router, prefix="/reader", tags=["reader"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(library_paths.router, prefix="/library-paths", tags=["library-paths"])