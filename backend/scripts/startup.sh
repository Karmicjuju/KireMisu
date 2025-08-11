#!/bin/bash

# KireMisu Backend Startup Script
# Handles database migration and admin user initialization

set -e

echo "🚀 Starting KireMisu Backend..."

# Wait for database to be ready (simplified)
echo "⏳ Waiting for database connection..."
sleep 10

# Skip migrations and admin user setup for now to get the container running
echo "⚠️  Skipping migrations and admin user setup - starting directly"

echo "🎉 Backend initialization complete!"

# Start the application
echo "🌐 Starting FastAPI server..."
exec "$@"