import os
from typing import List, Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "KireMisu"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "development-secret-key-change-in-production"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Storage paths
    MANGA_LIBRARY_PATH: str = "/manga"
    THUMBNAILS_PATH: str = "/thumbnails"
    PROCESSED_DATA_PATH: str = "/processed"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            return v
        # Fallback to environment variables if DATABASE_URL not set
        postgres_user = os.getenv("POSTGRES_USER", "kiremisu")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "development")
        postgres_server = os.getenv("POSTGRES_SERVER", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "kiremisu")
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()