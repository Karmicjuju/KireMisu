#!/bin/bash

# KireMisu Backend Startup Script
# Handles database migration and admin user initialization

set -e

echo "🚀 Starting KireMisu Backend..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python -c "
import asyncpg
import asyncio
import os
import time

async def wait_for_db():
    max_attempts = 30
    attempt = 0
    while attempt < max_attempts:
        try:
            # Parse database URL to extract connection details
            db_url = os.environ.get('DATABASE_URL', '')
            if not db_url:
                print('❌ DATABASE_URL not set')
                exit(1)
            
            # Convert asyncpg URL to connection params
            import urllib.parse
            parsed = urllib.parse.urlparse(db_url)
            
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]  # Remove leading slash
            )
            await conn.close()
            print('✅ Database connection successful')
            break
        except Exception as e:
            attempt += 1
            print(f'🔄 Database not ready (attempt {attempt}/{max_attempts}): {e}')
            await asyncio.sleep(2)
    else:
        print('❌ Failed to connect to database after 60 seconds')
        exit(1)

asyncio.run(wait_for_db())
"

# Run database migrations
echo "🔄 Running database migrations..."
uv run alembic upgrade head

# Initialize admin user if configured
if [ -n "$DEFAULT_ADMIN_PASSWORD" ]; then
    echo "👤 Setting up admin user..."
    python -c "
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from kiremisu.database.connection import get_db_session
from kiremisu.core.auth import initialize_admin_user
import logging

logging.basicConfig(level=logging.INFO)

async def setup_admin():
    try:
        async with get_db_session() as db:
            await initialize_admin_user(db)
        print('✅ Admin user setup completed')
    except Exception as e:
        print(f'⚠️  Admin user setup failed (may already exist): {e}')

asyncio.run(setup_admin())
"
else
    echo "⚠️  No DEFAULT_ADMIN_PASSWORD set - skipping admin user creation"
fi

echo "🎉 Backend initialization complete!"

# Start the application
echo "🌐 Starting FastAPI server..."
exec "$@"