#!/bin/bash

# Start production environment for KireMisu
# This script sets up secure production infrastructure

set -e

echo "🚀 Starting KireMisu Production Environment..."

# Check for required environment file
if [ ! -f "config/.env.production" ]; then
    echo "❌ Error: config/.env.production not found"
    echo "Please copy config/.env.production.example and configure it for your environment"
    exit 1
fi

# Load production environment variables
echo "Loading production environment variables..."
export $(grep -v '^#' config/.env.production | xargs)

# Validate required environment variables
required_vars=("JWT_SECRET_KEY" "POSTGRES_PASSWORD" "NEXT_PUBLIC_API_URL")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" = "CHANGE_ME_SECURE_PASSWORD" ] || [ "${!var}" = "CHANGE_ME_LONG_RANDOM_SECRET_KEY" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Error: Missing or unconfigured environment variables:"
    printf "  %s\n" "${missing_vars[@]}"
    echo "Please update config/.env.production with secure values"
    exit 1
fi

# Security checks
echo "Running security checks..."

if [ "$JWT_SECRET_KEY" = "test_jwt_secret_key_not_for_production" ]; then
    echo "❌ Error: Test JWT secret detected in production"
    exit 1
fi

if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo "❌ Error: JWT secret key must be at least 32 characters"
    exit 1
fi

if [ "$SECURE_COOKIES" != "true" ]; then
    echo "⚠️  Warning: SECURE_COOKIES should be true in production"
fi

if [ "$CSRF_PROTECTION_ENABLED" != "true" ]; then
    echo "⚠️  Warning: CSRF_PROTECTION_ENABLED should be true in production"
fi

echo "✅ Security checks passed"

# Create production volumes and networks
echo "Setting up production infrastructure..."
docker network create kiremisu_production_network 2>/dev/null || true

# Start production services
echo "Starting production services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "Waiting for production services to be ready..."
timeout=120
elapsed=0

services=("postgres" "backend" "frontend")

for service in "${services[@]}"; do
    echo "Checking $service health..."
    elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f docker-compose.prod.yml exec -T $service echo "healthy" > /dev/null 2>&1; then
            echo "✅ $service is ready"
            break
        fi
        
        echo "⏳ Waiting for $service... ($elapsed/$timeout)"
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    if [ $elapsed -ge $timeout ]; then
        echo "❌ $service failed to start within $timeout seconds"
        echo "Check logs: docker-compose -f docker-compose.prod.yml logs $service"
        exit 1
    fi
done

echo ""
echo "🎉 Production environment is ready!"
echo ""
echo "Services available at:"
echo "  Frontend: $NEXT_PUBLIC_API_URL"
echo "  Backend:  $NEXT_PUBLIC_API_URL/api"
echo ""
echo "To monitor logs:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To stop production environment:"
echo "  docker-compose -f docker-compose.prod.yml down"
echo ""
echo "⚠️  IMPORTANT: Ensure your domain is properly configured and SSL certificates are in place"
echo ""