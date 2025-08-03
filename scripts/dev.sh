#!/bin/bash

# KireMisu Development Helper Script
# This script provides common development commands

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "KireMisu Development Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup          - Install all dependencies and set up development environment"
    echo "  backend        - Start backend development server"
    echo "  frontend       - Start frontend development server"
    echo "  db-setup       - Set up PostgreSQL database"
    echo "  db-migrate     - Run database migrations"
    echo "  db-revision    - Generate new database migration"
    echo "  db-reset       - Reset database (drops and recreates)"
    echo "  lint           - Run linting for all code"
    echo "  format         - Format all code"
    echo "  test           - Run all tests"
    echo "  test-e2e       - Run frontend E2E tests"
    echo "  clean          - Clean build artifacts and dependencies"
    echo ""
    echo "Docker Commands:"
    echo "  docker-dev     - Start development environment with Docker Compose"
    echo "  docker-stop    - Stop Docker development environment"
    echo "  docker-clean   - Clean up all KireMisu containers"
    echo "  docker-reset   - Clean containers and start fresh environment"
    echo ""
    echo "Troubleshooting:"
    echo "  ports          - Check and handle port conflicts"
    echo ""
}

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

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        return 1
    fi
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

kill_port() {
    local port=$1
    log_info "Killing processes on port $port..."
    
    # Try to find and kill processes using the port
    local pids=$(lsof -ti :$port)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 2
        
        # Check if port is still in use
        if check_port $port; then
            log_warning "Port $port is still in use after kill attempt"
            return 1
        else
            log_success "Port $port freed successfully"
            return 0
        fi
    else
        log_info "No processes found on port $port"
        return 0
    fi
}

cleanup_containers() {
    log_info "Cleaning up existing KireMisu containers..."
    
    # Stop and remove containers with kiremisu prefix
    docker ps -a --filter "name=kiremisu" --format "{{.Names}}" | while read container; do
        if [ -n "$container" ]; then
            log_info "Stopping container: $container"
            docker stop "$container" >/dev/null 2>&1 || true
            log_info "Removing container: $container"
            docker rm "$container" >/dev/null 2>&1 || true
        fi
    done
    
    # Clean up any orphaned containers from docker-compose
    if [ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]; then
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.dev.yml down --remove-orphans >/dev/null 2>&1 || true
    fi
    
    log_success "Container cleanup complete"
}

check_and_handle_ports() {
    local ports=("5432" "8000" "3000")
    local conflicts=()
    
    log_info "Checking for port conflicts..."
    
    for port in "${ports[@]}"; do
        if check_port $port; then
            conflicts+=($port)
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        log_warning "Port conflicts detected on: ${conflicts[*]}"
        
        # Check if conflicts are from Docker containers
        local docker_conflicts=()
        for port in "${conflicts[@]}"; do
            # Get container using the port
            local container=$(docker ps --filter "publish=$port" --format "{{.Names}}" 2>/dev/null | head -1)
            if [ -n "$container" ]; then
                docker_conflicts+=("$port:$container")
            fi
        done
        
        if [ ${#docker_conflicts[@]} -gt 0 ]; then
            log_info "Found Docker containers using ports:"
            for conflict in "${docker_conflicts[@]}"; do
                log_info "  Port ${conflict%:*} - Container: ${conflict#*:}"
            done
            
            read -p "Stop conflicting containers? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cleanup_containers
                return 0
            fi
        fi
        
        # If not all conflicts resolved, offer to kill processes
        remaining_conflicts=()
        for port in "${conflicts[@]}"; do
            if check_port $port; then
                remaining_conflicts+=($port)
            fi
        done
        
        if [ ${#remaining_conflicts[@]} -gt 0 ]; then
            log_warning "Remaining port conflicts: ${remaining_conflicts[*]}"
            read -p "Force kill processes on these ports? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                for port in "${remaining_conflicts[@]}"; do
                    kill_port $port
                done
            else
                log_error "Cannot start development environment with port conflicts"
                return 1
            fi
        fi
    else
        log_success "No port conflicts detected"
    fi
}

ensure_venv() {
    cd "$PROJECT_ROOT"
    
    # Check if we're already in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        log_info "Already in virtual environment: $VIRTUAL_ENV"
        return 0
    fi
    
    # Check if .venv exists
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv .venv
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source .venv/bin/activate
    
    # Verify activation
    if [ -n "$VIRTUAL_ENV" ]; then
        log_success "Virtual environment activated: $VIRTUAL_ENV"
    else
        log_error "Failed to activate virtual environment"
        return 1
    fi
}

setup_backend() {
    log_info "Setting up Python backend..."
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    # Check for uv, fallback to pip
    if command -v uv &> /dev/null; then
        log_info "Installing dependencies with uv..."
        uv sync --dev
    else
        log_info "Installing dependencies with pip..."
        python -m pip install --upgrade pip
        python -m pip install -e ".[dev]"
    fi
    
    log_success "Backend setup complete"
}

setup_frontend() {
    log_info "Setting up Next.js frontend..."
    cd "$PROJECT_ROOT/frontend"
    
    if command -v npm &> /dev/null; then
        npm install
    else
        log_error "npm is required but not installed"
        return 1
    fi
    
    log_success "Frontend setup complete"
}

setup_dev_environment() {
    log_info "Setting up development environment..."
    
    # Check prerequisites
    check_command "python3" || exit 1
    check_command "node" || exit 1
    check_command "npm" || exit 1
    
    # Setup backend
    setup_backend
    
    # Setup frontend
    setup_frontend
    
    # Setup pre-commit hooks (ensure venv is active)
    ensure_venv || return 1
    if command -v pre-commit &> /dev/null; then
        log_info "Installing pre-commit hooks..."
        pre-commit install
    else
        log_warning "pre-commit not found, skipping hooks setup"
    fi
    
    # Copy environment file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_info "Creating .env file from template..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        log_warning "Please edit .env file with your configuration"
    fi
    
    log_success "Development environment setup complete!"
    log_info "Next steps:"
    log_info "1. Edit .env file with your configuration"
    log_info "2. Set up PostgreSQL database: $0 db-setup"
    log_info "3. Run migrations: $0 db-migrate"
    log_info "4. Start development servers: $0 backend (in one terminal) and $0 frontend (in another)"
}

start_backend() {
    log_info "Starting backend development server..."
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    if command -v uv &> /dev/null; then
        uv run python -m kiremisu.main
    else
        python -m kiremisu.main
    fi
}

start_frontend() {
    log_info "Starting frontend development server..."
    cd "$PROJECT_ROOT/frontend"
    npm run dev
}

setup_database() {
    log_info "Setting up PostgreSQL database..."
    
    # Check if PostgreSQL is running
    if ! pg_isready -h localhost -p 5432 &> /dev/null; then
        log_error "PostgreSQL is not running on localhost:5432"
        log_info "Please start PostgreSQL or run 'docker-compose up postgres' for a Docker instance"
        return 1
    fi
    
    # Create database if it doesn't exist
    if ! psql -h localhost -p 5432 -U postgres -lqt | cut -d \| -f 1 | grep -qw kiremisu; then
        log_info "Creating kiremisu database..."
        createdb -h localhost -p 5432 -U postgres kiremisu
    else
        log_info "Database kiremisu already exists"
    fi
    
    log_success "Database setup complete"
}

run_migrations() {
    log_info "Running database migrations..."
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    # Navigate to backend directory for alembic
    cd "$PROJECT_ROOT/backend"
    
    if command -v uv &> /dev/null; then
        uv run alembic upgrade head
    else
        alembic upgrade head
    fi
    
    log_success "Migrations complete"
}

generate_migration() {
    log_info "Generating new database migration..."
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    # Navigate to backend directory for alembic
    cd "$PROJECT_ROOT/backend"
    
    # Check if message was provided as argument
    local message="$1"
    if [ -z "$message" ]; then
        read -p "Enter migration message: " message
        if [ -z "$message" ]; then
            log_error "Migration message is required"
            return 1
        fi
    fi
    
    if command -v uv &> /dev/null; then
        uv run alembic revision --autogenerate -m "$message"
    else
        alembic revision --autogenerate -m "$message"
    fi
    
    log_success "Migration generated successfully"
}

reset_database() {
    log_warning "This will drop and recreate the database. All data will be lost!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Dropping database..."
        dropdb -h localhost -p 5432 -U postgres kiremisu --if-exists
        setup_database
        run_migrations
        log_success "Database reset complete"
    else
        log_info "Database reset cancelled"
    fi
}

run_lint() {
    log_info "Running linting..."
    
    # Backend linting
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    if command -v uv &> /dev/null; then
        uv run ruff check .
    else
        ruff check .
    fi
    
    # Frontend linting
    cd "$PROJECT_ROOT/frontend"
    npm run lint
    
    log_success "Linting complete"
}

run_format() {
    log_info "Running code formatting..."
    
    # Backend formatting
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    if command -v uv &> /dev/null; then
        uv run ruff format .
    else
        ruff format .
    fi
    
    # Frontend formatting
    cd "$PROJECT_ROOT/frontend"
    npm run format
    
    log_success "Formatting complete"
}

run_tests() {
    log_info "Running tests..."
    
    # Backend tests
    cd "$PROJECT_ROOT"
    
    # Ensure we're in a virtual environment
    ensure_venv || return 1
    
    if command -v uv &> /dev/null; then
        uv run pytest
    else
        pytest
    fi
    
    # Frontend type checking
    cd "$PROJECT_ROOT/frontend"
    npm run type-check
    
    log_success "Tests complete"
}

run_e2e_tests() {
    log_info "Running frontend E2E tests..."
    
    # Frontend E2E tests
    cd "$PROJECT_ROOT/frontend"
    npm run test:e2e
    
    log_success "E2E tests complete"
}

clean_environment() {
    log_info "Cleaning development environment..."
    
    # Clean Python cache
    find "$PROJECT_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean frontend
    if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
        rm -rf "$PROJECT_ROOT/frontend/node_modules"
    fi
    if [ -d "$PROJECT_ROOT/frontend/.next" ]; then
        rm -rf "$PROJECT_ROOT/frontend/.next"
    fi
    
    log_success "Environment cleaned"
}

start_docker_dev() {
    log_info "Starting Docker development environment..."
    cd "$PROJECT_ROOT"
    
    if [ ! -f "docker-compose.dev.yml" ]; then
        log_error "docker-compose.dev.yml not found"
        return 1
    fi
    
    # Check for port conflicts and handle them
    check_and_handle_ports || return 1
    
    # Start the development environment
    log_info "Starting Docker Compose services..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait a moment for services to start
    sleep 3
    
    # Check service health
    log_info "Checking service health..."
    docker-compose -f docker-compose.dev.yml ps
    
    log_success "Docker development environment started"
    log_info "Services available at:"
    log_info "  Frontend: http://localhost:3000"
    log_info "  Backend API: http://localhost:8000"
    log_info "  API Docs: http://localhost:8000/api/docs"
    log_info "  PostgreSQL: localhost:5432"
}

stop_docker_dev() {
    log_info "Stopping Docker development environment..."
    cd "$PROJECT_ROOT"
    
    if [ -f "docker-compose.dev.yml" ]; then
        docker-compose -f docker-compose.dev.yml down
    fi
    
    log_success "Docker development environment stopped"
}

# Main command handling
case "$1" in
    setup)
        setup_dev_environment
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    db-setup)
        setup_database
        ;;
    db-migrate)
        run_migrations
        ;;
    db-revision)
        generate_migration "$2"
        ;;
    db-reset)
        reset_database
        ;;
    lint)
        run_lint
        ;;
    format)
        run_format
        ;;
    test)
        run_tests
        ;;
    test-e2e)
        run_e2e_tests
        ;;
    clean)
        clean_environment
        ;;
    docker-dev)
        start_docker_dev
        ;;
    docker-stop)
        stop_docker_dev
        ;;
    docker-clean)
        cleanup_containers
        ;;
    docker-reset)
        cleanup_containers
        start_docker_dev
        ;;
    ports)
        check_and_handle_ports
        ;;
    "")
        print_usage
        ;;
    *)
        log_error "Unknown command: $1"
        print_usage
        exit 1
        ;;
esac