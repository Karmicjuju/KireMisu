#!/bin/bash

# KireMisu Development Workflow Helper
# This script provides common development workflows and handles container cleanup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Common development workflows
print_usage() {
    echo "KireMisu Development Workflow Helper"
    echo ""
    echo "Usage: $0 [workflow]"
    echo ""
    echo "Workflows:"
    echo "  fresh-start    - Clean everything and start fresh development environment"
    echo "  test-cleanup   - Run tests and clean up containers afterwards"
    echo "  restart-dev    - Restart development environment (handles port conflicts)"
    echo "  emergency-stop - Force stop all KireMisu containers and free ports"
    echo "  status         - Show status of all KireMisu services"
    echo ""
}

fresh_start() {
    log_info "Starting fresh development environment..."
    
    # Stop and clean any existing containers
    "$SCRIPT_DIR/dev.sh" docker-stop || true
    "$SCRIPT_DIR/dev.sh" docker-clean || true
    
    # Clean build artifacts
    "$SCRIPT_DIR/dev.sh" clean
    
    # Check and handle any remaining port conflicts
    "$SCRIPT_DIR/dev.sh" ports
    
    # Start fresh environment
    "$SCRIPT_DIR/dev.sh" docker-dev
    
    log_success "Fresh development environment ready!"
}

test_cleanup() {
    log_info "Running tests with cleanup..."
    
    # Start test environment
    "$SCRIPT_DIR/dev.sh" docker-dev
    
    # Wait for services to be ready
    sleep 10
    
    # Run tests
    log_info "Running tests..."
    "$SCRIPT_DIR/dev.sh" test || {
        log_error "Tests failed, but cleaning up containers anyway..."
    }
    
    # Clean up containers after tests
    log_info "Cleaning up test environment..."
    "$SCRIPT_DIR/dev.sh" docker-stop
    "$SCRIPT_DIR/dev.sh" docker-clean
    
    log_success "Test cleanup complete"
}

restart_dev() {
    log_info "Restarting development environment..."
    
    # Stop current environment
    "$SCRIPT_DIR/dev.sh" docker-stop || true
    
    # Wait a moment for ports to be freed
    sleep 2
    
    # Handle any port conflicts
    "$SCRIPT_DIR/dev.sh" ports
    
    # Start environment
    "$SCRIPT_DIR/dev.sh" docker-dev
    
    log_success "Development environment restarted"
}

emergency_stop() {
    log_warning "Emergency stop - forcing cleanup of all KireMisu resources..."
    
    # Force stop all KireMisu containers
    docker ps -a --filter "name=kiremisu" --format "{{.Names}}" | while read container; do
        if [ -n "$container" ]; then
            log_info "Force stopping container: $container"
            docker kill "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        fi
    done
    
    # Kill processes on common ports
    for port in 3000 8000 5432; do
        log_info "Freeing port $port..."
        lsof -ti :$port | xargs kill -9 2>/dev/null || true
    done
    
    # Clean up Docker Compose
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true
    docker-compose down --remove-orphans 2>/dev/null || true
    
    log_success "Emergency cleanup complete"
}

show_status() {
    log_info "KireMisu Development Environment Status"
    echo ""
    
    # Check for running containers
    echo "=== Docker Containers ==="
    if docker ps --filter "name=kiremisu" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q kiremisu; then
        docker ps --filter "name=kiremisu" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "No KireMisu containers running"
    fi
    echo ""
    
    # Check port usage
    echo "=== Port Status ==="
    for port in 3000 8000 5432; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            process=$(lsof -Pi :$port -sTCP:LISTEN -t | head -1)
            process_name=$(ps -p $process -o comm= 2>/dev/null || echo "unknown")
            echo "Port $port: OCCUPIED by $process_name (PID: $process)"
        else
            echo "Port $port: FREE"
        fi
    done
    echo ""
    
    # Check service health
    echo "=== Service Health ==="
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend API: HEALTHY (http://localhost:8000)"
    else
        echo "Backend API: NOT RESPONDING"
    fi
    
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "Frontend: HEALTHY (http://localhost:3000)"
    else
        echo "Frontend: NOT RESPONDING"
    fi
    
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "PostgreSQL: HEALTHY (localhost:5432)"
    else
        echo "PostgreSQL: NOT RESPONDING"
    fi
}

# Main command handling
case "$1" in
    fresh-start)
        fresh_start
        ;;
    test-cleanup)
        test_cleanup
        ;;
    restart-dev)
        restart_dev
        ;;
    emergency-stop)
        emergency_stop
        ;;
    status)
        show_status
        ;;
    "")
        print_usage
        ;;
    *)
        log_error "Unknown workflow: $1"
        print_usage
        exit 1
        ;;
esac