"""
Database initialization module.

This module handles database table creation and initial setup.
"""

from sqlalchemy import inspect
from app.db.database import engine
from app.models.user import Base as UserBase


def init_db():
    """Initialize database with all tables."""
    print("Initializing database...")
    
    # Create all tables
    UserBase.metadata.create_all(bind=engine)
    
    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if 'users' in tables:
        print("✅ Users table created successfully")
    else:
        print("❌ Failed to create users table")
        raise Exception("Database initialization failed")
    
    print("Database initialization complete!")


if __name__ == "__main__":
    init_db()