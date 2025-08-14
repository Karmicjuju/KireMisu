"""Application configuration using Pydantic settings."""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Security
    secret_key: str = Field(
        default="",
        description="Secret key for JWT tokens (must be at least 32 characters)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_hours: int = Field(default=24, description="JWT token expiration in hours")

    # Authentication security settings
    password_min_length: int = Field(default=8, description="Minimum password length")
    max_login_attempts: int = Field(default=5, description="Max failed login attempts before lockout")
    lockout_duration_minutes: int = Field(default=30, description="Account lockout duration in minutes")

    # Rate limiting
    auth_rate_limit_attempts: int = Field(default=5, description="Max auth attempts per IP")
    auth_rate_limit_window_minutes: int = Field(default=30, description="Auth rate limit window")

    # General rate limiting
    general_rate_limit_per_minute: int = Field(default=120, description="General API requests per minute per IP")
    general_rate_limit_per_hour: int = Field(default=3600, description="General API requests per hour per IP")
    general_rate_limit_burst: int = Field(default=20, description="General API burst limit per IP")

    # Admin user configuration
    default_admin_username: str = Field(default="admin", description="Default admin username")
    default_admin_password: str = Field(default="", description="Default admin password (set via env)")
    default_admin_email: str = Field(default="admin@kiremisu.local", description="Default admin email")

    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://kiremisu:kiremisu@localhost:5432/kiremisu",
        description="Database connection URL",
    )

    # Storage
    manga_storage_paths: list[Path] = Field(
        default_factory=list, description="List of manga storage paths to scan"
    )

    # External APIs
    mangadx_api_url: str = Field(
        default="https://api.mangadex.org", description="MangaDx API base URL"
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

    # Push notifications (Web Push / VAPID)
    vapid_public_key: str = Field(default="", description="VAPID public key for push notifications")
    vapid_private_key: str = Field(
        default="", description="VAPID private key for push notifications"
    )
    vapid_claims: dict = Field(
        default_factory=lambda: {"sub": "mailto:admin@kiremisu.local"},
        description="VAPID claims for push notifications",
    )

    class Config:
        # Look for .env file in project root
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_security_config(self) -> None:
        """Validate security configuration on startup."""
        if not self.secret_key:
            raise ValueError("SECRET_KEY environment variable must be set")

        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

        if self.default_admin_password and len(self.default_admin_password) < self.password_min_length:
            raise ValueError(f"DEFAULT_ADMIN_PASSWORD must be at least {self.password_min_length} characters")


settings = Settings()

# Validate security configuration on import
try:
    settings.validate_security_config()
except ValueError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Configuration error: {e}")
    logger.error("Please check your environment variables and ensure proper security settings")
    # Don't raise in production to allow for configuration fixes
    import os
    if os.getenv("KIREMISU_ENV") != "production":
        raise


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
