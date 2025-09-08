"""
Database initialization module.

This module handles database table creation and initial setup.
"""

import asyncio
from sqlalchemy import inspect
from app.db.database import engine, create_db_and_tables
from app.models import User, Series, Chapter, StoragePath


async def init_db_async():
    """Initialize database with all tables (async)."""
    print("Initializing database...")
    
    # Create all tables using the async function
    await create_db_and_tables()
    
    print("✅ Database tables created successfully")
    print("Database initialization complete!")


def init_db():
    """Initialize database with all tables (sync wrapper)."""
    asyncio.run(init_db_async())


if __name__ == "__main__":
    init_db()