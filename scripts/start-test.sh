#!/bin/bash

# Start test environment for KireMisu
# This script sets up isolated test infrastructure

set -e

echo "🧪 Starting KireMisu Test Environment..."

# Load test environment variables
if [ -f "config/.env.test" ]; then
    echo "Loading test environment variables..."
    export $(grep -v '^#' config/.env.test | xargs)
else
    echo "⚠️  Warning: config/.env.test not found, using defaults"
fi

# Clean up any existing test containers
echo "Cleaning up existing test containers..."
docker-compose -f docker-compose.test.yml down --remove-orphans || true

# Clean up test volumes if requested
if [ "$1" = "--clean" ]; then
    echo "Removing test volumes..."
    docker volume rm kiremisu_postgres_test_data 2>/dev/null || true
fi

# Start test services
echo "Starting test services..."
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be healthy
echo "Waiting for test services to be ready..."
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.test.yml exec -T postgres-test pg_isready -U kiremisu_test -d kiremisu_test > /dev/null 2>&1; then
        echo "✅ Test database is ready"
        break
    fi
    
    echo "⏳ Waiting for test database... ($elapsed/$timeout)"
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ Test database failed to start within $timeout seconds"
    exit 1
fi

# Check backend health
echo "Checking test backend health..."
timeout=30
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if curl -f http://localhost:8001/api/jobs/status > /dev/null 2>&1; then
        echo "✅ Test backend is ready"
        break
    fi
    
    echo "⏳ Waiting for test backend... ($elapsed/$timeout)"
    sleep 2
    elapsed=$((elapsed + 2))
done

# Check frontend health
echo "Checking test frontend health..."
timeout=30
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if curl -f http://localhost:3001 > /dev/null 2>&1; then
        echo "✅ Test frontend is ready"
        break
    fi
    
    echo "⏳ Waiting for test frontend... ($elapsed/$timeout)"
    sleep 2
    elapsed=$((elapsed + 2))
done

echo ""
echo "🎉 Test environment is ready!"
echo ""
echo "Services available at:"
echo "  Frontend: http://localhost:3001"
echo "  Backend:  http://localhost:8001"
echo "  Database: localhost:5433"
echo ""
echo "Test credentials:"
echo "  Username: admin"
echo "  Password: KireMisu2025!"
echo ""
echo "To run E2E tests:"
echo "  cd frontend && npm run test:e2e"
echo ""
echo "To stop test environment:"
echo "  docker-compose -f docker-compose.test.yml down"
echo ""