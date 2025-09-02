#!/bin/bash

# KireMisu DevContainer Post-Start Script
# This script runs every time the development container starts

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[STARTUP]${NC} $1"
}

# Wait for services to be ready
log "Checking service health..."

# Wait for PostgreSQL
until pg_isready -h postgres -p 5432 -U kiremisu >/dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 1
done

log "PostgreSQL is ready!"

# Update Python path for VS Code
export PYTHONPATH="/workspace/backend:$PYTHONPATH"

# Show helpful information
echo ""
echo -e "${BLUE}🚀 KireMisu Development Environment Ready!${NC}"
echo ""
echo -e "${BLUE}Available services:${NC}"
echo -e "  • PostgreSQL: postgres:5432"
echo -e "  • Backend API: http://localhost:8000"
echo -e "  • Frontend: http://localhost:3000"
echo ""
echo -e "${BLUE}Quick commands:${NC}"
echo -e "  • Start backend: ${GREEN}cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload${NC}"
echo -e "  • Start frontend: ${GREEN}cd frontend && pnpm dev${NC}"
echo -e "  • Database console: ${GREEN}psql -h postgres -U kiremisu -d kiremisu${NC}"
echo ""