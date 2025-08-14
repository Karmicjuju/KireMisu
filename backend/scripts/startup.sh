#!/bin/bash

# KireMisu Backend Startup Script
# Handles database migration and admin user initialization

set -e

echo "🚀 Starting KireMisu Backend..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
sleep 10

# Simple database connection check with curl
check_db_simple() {
    # Use curl to check if postgres is responding on port 5432
    nc -z postgres 5432 >/dev/null 2>&1
}

# Wait for database with retries
echo "🔄 Waiting for database to be ready..."
for i in {1..30}; do
    if check_db_simple; then
        echo "✅ Database port accessible"
        break
    fi
    echo "⏳ Database not ready, waiting... (attempt $i/30)"
    sleep 2
    if [ $i -eq 30 ]; then
        echo "⚠️  Database check failed, but continuing with startup..."
        break
    fi
done

# Run database migrations
echo "📊 Running database migrations..."
cd /app/backend && uv run alembic upgrade head && cd /app

# Admin user creation will be handled by the FastAPI app on startup
echo "ℹ️  Admin user creation will be handled by FastAPI app startup"

echo "🎉 Backend initialization complete!"

# Start the application
echo "🌐 Starting FastAPI server..."
exec "$@"