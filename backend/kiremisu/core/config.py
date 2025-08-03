"""Application configuration using Pydantic settings."""

import os
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Security
    secret_key: str = Field(description="Secret key for JWT tokens")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiration")

    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://kiremisu:kiremisu@localhost:5432/kiremisu",
        description="Database connection URL",
    )

    # Storage
    manga_storage_paths: List[Path] = Field(
        default_factory=list, description="List of manga storage paths to scan"
    )

    # External APIs
    mangadx_api_url: str = Field(
        default="https://api.mangadx.org", description="MangaDx API base URL"
    )
    mangadx_rate_limit_per_minute: int = Field(
        default=60, description="MangaDx API rate limit per minute"
    )

    # File processing
    max_file_size_mb: int = Field(default=500, description="Maximum file size in MB")
    thumbnail_size: tuple[int, int] = Field(default=(300, 400), description="Thumbnail dimensions")

    # Background jobs
    job_poll_interval_seconds: int = Field(default=5, description="Job polling interval")
    max_concurrent_jobs: int = Field(default=2, description="Maximum concurrent background jobs")

    class Config:
        # Look for .env file in project root
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
