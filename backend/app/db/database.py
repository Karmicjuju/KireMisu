from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase

from app.core.config import settings

# Convert sync URL to async URL
database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def create_db_and_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """Get user database for FastAPI-Users."""
    # Import here to avoid circular imports
    from app.models.user import User
    yield SQLAlchemyUserDatabase(session, User)


# Legacy compatibility function for existing endpoints
def get_db():
    """Legacy sync database session - deprecated, use get_async_session instead."""
    # For now, raise an error to identify code that needs updating
    raise NotImplementedError(
        "Synchronous database sessions are no longer supported. "
        "Please update to use get_async_session() and AsyncSession."
    )