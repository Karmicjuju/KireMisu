import os
from typing import List, Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "KireMisu"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str  # Required environment variable - no default for security
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - restrictive defaults, override in production
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Storage paths
    MANGA_LIBRARY_PATH: str = "/manga"
    THUMBNAILS_PATH: str = "/thumbnails"
    PROCESSED_DATA_PATH: str = "/processed"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Rate limiting (configurable per environment)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_READ_REQUESTS: int = 200
    RATE_LIMIT_WRITE_REQUESTS: int = 50
    RATE_LIMIT_SEARCH_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 3600
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            origins = [i.strip() for i in v.split(",")]
            # Security validation: ensure no wildcard origins in production
            for origin in origins:
                if origin == "*":
                    raise ValueError("Wildcard CORS origins (*) are not allowed for security reasons")
                if not (origin.startswith("http://") or origin.startswith("https://")):
                    raise ValueError(f"CORS origin must be a valid HTTP/HTTPS URL: {origin}")
            return origins
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            return v
        # Fallback to environment variables if DATABASE_URL not set
        # SECURITY: No default passwords - all credentials must be explicitly set
        postgres_user = os.getenv("POSTGRES_USER")
        postgres_password = os.getenv("POSTGRES_PASSWORD")
        postgres_server = os.getenv("POSTGRES_SERVER", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "kiremisu")
        
        if not postgres_user or not postgres_password:
            raise ValueError("POSTGRES_USER and POSTGRES_PASSWORD environment variables are required")
        
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()