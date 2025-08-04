#!/usr/bin/env python3
"""
Quick script to create test manga data for manual testing.
This creates a sample series and chapter directly in the database.
"""

import asyncio
import sys
import os
from pathlib import Path
from uuid import uuid4

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from kiremisu.database.connection import get_db_session_factory
from kiremisu.database.models import Series, Chapter


async def create_test_data():
    """Create test series and chapter data."""
    db_session_factory = get_db_session_factory()
    
    async with db_session_factory() as db:
        # Create test series
        series = Series(
            id=uuid4(),
            title_primary="Test Manga Series",
            author="Test Author",
            description="A test manga series for manual testing the reader",
            total_chapters=1,
            file_path="/test/manga/series"
        )
        db.add(series)
        await db.flush()
        
        # Create test chapter  
        chapter = Chapter(
            id=uuid4(),
            series_id=series.id,
            chapter_number=1.0,
            volume_number=1,
            title="Test Chapter",
            file_path="/test/manga/series/chapter_001.cbz",
            file_size=1024000,
            page_count=5,
            is_read=False,
            last_read_page=0
        )
        db.add(chapter)
        await db.commit()
        await db.refresh(series)
        await db.refresh(chapter)
        
        print(f"✅ Created test series: {series.id}")
        print(f"✅ Created test chapter: {chapter.id}")
        print(f"\n🔗 Test reader URL:")
        print(f"   http://localhost:3000/reader/{chapter.id}")
        print(f"\n📊 API endpoints to test:")
        print(f"   http://localhost:8000/api/chapters/{chapter.id}")
        print(f"   http://localhost:8000/api/chapters/{chapter.id}/pages")
        
        return series.id, chapter.id


if __name__ == "__main__":
    try:
        series_id, chapter_id = asyncio.run(create_test_data())
        print(f"\n✨ Test data created successfully!")
        print(f"\nNote: The reader will show 'Page image not found' errors")
        print(f"because the test files don't actually exist on disk.")
        print(f"This is expected - you're testing the reader interface, not file reading.")
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        print(f"\nMake sure the backend is running and database is accessible.")