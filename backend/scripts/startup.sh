#!/bin/bash

# KireMisu Backend Startup Script
# Handles database migration and admin user initialization

set -e

echo "🚀 Starting KireMisu Backend..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
sleep 10

# Function to check if database is ready
check_db() {
    python -c "
import asyncio
import sys
from kiremisu.database.connection import get_db_session
from sqlalchemy import text

async def test_connection():
    try:
        async with get_db_session() as session:
            await session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
"
}

# Wait for database with retries
echo "🔄 Testing database connection..."
for i in {1..30}; do
    if check_db; then
        echo "✅ Database connection successful"
        break
    fi
    echo "⏳ Database not ready, waiting... (attempt $i/30)"
    sleep 2
done

# Run database migrations
echo "📊 Running database migrations..."
cd /app/backend && uv run alembic upgrade head && cd /app

# Create admin user if environment variables are set
if [[ -n "$DEFAULT_ADMIN_USERNAME" && -n "$DEFAULT_ADMIN_PASSWORD" ]]; then
    echo "👤 Creating admin user..."
    python -c "
import asyncio
import os
from kiremisu.database.connection import get_db_session
from kiremisu.core.auth import create_user_db

async def create_admin():
    try:
        async with get_db_session() as session:
            admin_user = await create_user_db(
                db=session,
                username=os.environ['DEFAULT_ADMIN_USERNAME'],
                email=os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@kiremisu.local'),
                password=os.environ['DEFAULT_ADMIN_PASSWORD'],
                is_admin=True
            )
            print(f'✅ Admin user created: {admin_user.username}')
    except ValueError as e:
        if 'already' in str(e).lower():
            print('ℹ️  Admin user already exists')
        else:
            print(f'❌ Failed to create admin user: {e}')
    except Exception as e:
        print(f'❌ Error creating admin user: {e}')

asyncio.run(create_admin())
"
else
    echo "⚠️  No admin user credentials provided in environment variables"
fi

echo "🎉 Backend initialization complete!"

# Start the application
echo "🌐 Starting FastAPI server..."
exec "$@"