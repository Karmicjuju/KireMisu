#!/bin/bash

# KireMisu Reader Testing Script
# This script runs comprehensive tests for the manga reader functionality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RUN_BACKEND_TESTS=true
RUN_FRONTEND_UNIT_TESTS=true
RUN_E2E_TESTS=true
RUN_PERFORMANCE_TESTS=false
RUN_COVERAGE=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            RUN_FRONTEND_UNIT_TESTS=false
            RUN_E2E_TESTS=false
            shift
            ;;
        --frontend-only)
            RUN_BACKEND_TESTS=false
            shift
            ;;
        --e2e-only)
            RUN_BACKEND_TESTS=false
            RUN_FRONTEND_UNIT_TESTS=false
            shift
            ;;
        --performance)
            RUN_PERFORMANCE_TESTS=true
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "KireMisu Reader Testing Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --backend-only      Run only backend tests"
            echo "  --frontend-only     Run only frontend unit tests"
            echo "  --e2e-only          Run only E2E tests"
            echo "  --performance       Include performance tests (slow)"
            echo "  --coverage          Generate coverage reports"
            echo "  --verbose           Verbose output"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                  # Run all tests except performance"
            echo "  $0 --backend-only   # Run only backend tests"
            echo "  $0 --coverage       # Run all tests with coverage"
            echo "  $0 --performance    # Run all tests including performance"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if we're in the right directory
if [[ ! -f "CLAUDE.md" ]]; then
    print_error "This script must be run from the KireMisu root directory"
    exit 1
fi

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed"
        exit 1
    fi
    print_success "Node.js found: $(node --version)"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is required but not installed"
        exit 1
    fi
    print_success "npm found: $(npm --version)"
    
    # Check PostgreSQL (for backend tests)
    if [[ "$RUN_BACKEND_TESTS" == true ]]; then
        if ! command -v psql &> /dev/null; then
            print_warning "PostgreSQL not found - some backend tests may fail"
        else
            print_success "PostgreSQL found"
        fi
    fi
}

# Setup test environment
setup_environment() {
    print_header "Setting Up Test Environment"
    
    # Set test database URL if not already set
    if [[ -z "$TEST_DATABASE_URL" ]]; then
        export TEST_DATABASE_URL="postgresql+asyncpg://kiremisu:kiremisu@localhost:5432/kiremisu_test"
        print_info "Using default test database URL"
    else
        print_info "Using existing TEST_DATABASE_URL"
    fi
    
    # Create test database if it doesn't exist (best effort)
    if command -v createdb &> /dev/null; then
        createdb kiremisu_test 2>/dev/null || true
        print_info "Test database setup attempted"
    fi
}

# Run backend tests
run_backend_tests() {
    print_header "Running Backend Tests"
    
    cd backend
    
    # Install dependencies if needed
    print_info "Installing backend dependencies..."
    pip install -e ".[dev]" > /dev/null 2>&1
    
    # Build test command
    PYTEST_ARGS="tests/api/test_reader.py tests/api/test_reader_error_handling.py"
    
    if [[ "$RUN_COVERAGE" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov=kiremisu.api.reader --cov-report=html --cov-report=term"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS -v"
    fi
    
    if [[ "$RUN_PERFORMANCE_TESTS" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS tests/performance/test_reader_performance.py -m slow"
        print_info "Including performance tests (this may take a while)"
    fi
    
    # Run tests
    print_info "Running backend tests..."
    if pytest $PYTEST_ARGS; then
        print_success "Backend tests passed"
    else
        print_error "Backend tests failed"
        cd ..
        exit 1
    fi
    
    if [[ "$RUN_COVERAGE" == true ]]; then
        print_info "Backend coverage report generated in backend/htmlcov/"
    fi
    
    cd ..
}

# Run frontend unit tests
run_frontend_unit_tests() {
    print_header "Running Frontend Unit Tests"
    
    cd frontend
    
    # Install dependencies if needed
    print_info "Installing frontend dependencies..."
    npm ci > /dev/null 2>&1
    
    # Build test command
    if [[ "$RUN_COVERAGE" == true ]]; then
        TEST_CMD="npm run test:coverage"
    else
        TEST_CMD="npm test -- --watchAll=false"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        TEST_CMD="$TEST_CMD --verbose"
    fi
    
    # Run tests
    print_info "Running frontend unit tests..."
    if eval $TEST_CMD; then
        print_success "Frontend unit tests passed"
    else
        print_error "Frontend unit tests failed"
        cd ..
        exit 1
    fi
    
    if [[ "$RUN_COVERAGE" == true ]]; then
        print_info "Frontend coverage report generated in frontend/coverage/"
    fi
    
    cd ..
}

# Run E2E tests
run_e2e_tests() {
    print_header "Running End-to-End Tests"
    
    cd frontend
    
    # Install Playwright browsers if needed
    print_info "Setting up Playwright browsers..."
    npx playwright install > /dev/null 2>&1
    
    # Build test command
    E2E_ARGS="tests/e2e/reader-smoke.spec.ts"
    
    if [[ "$VERBOSE" == true ]]; then
        E2E_ARGS="$E2E_ARGS --reporter=list"
    fi
    
    # Check if backend is running
    print_info "Checking if backend is available..."
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is running"
    else
        print_warning "Backend not detected - some E2E tests may fail"
        print_info "Start the backend with: cd backend && uvicorn kiremisu.main:app --reload"
    fi
    
    # Run E2E tests
    print_info "Running E2E tests..."
    if npx playwright test $E2E_ARGS; then
        print_success "E2E tests passed"
    else
        print_error "E2E tests failed"
        print_info "Check the Playwright report: npx playwright show-report"
        cd ..
        exit 1
    fi
    
    cd ..
}

# Generate summary report
generate_summary() {
    print_header "Test Summary"
    
    echo "Test execution completed successfully!"
    echo ""
    
    if [[ "$RUN_BACKEND_TESTS" == true ]]; then
        print_success "Backend API tests passed"
    fi
    
    if [[ "$RUN_FRONTEND_UNIT_TESTS" == true ]]; then
        print_success "Frontend unit tests passed"
    fi
    
    if [[ "$RUN_E2E_TESTS" == true ]]; then
        print_success "End-to-end tests passed"
    fi
    
    if [[ "$RUN_PERFORMANCE_TESTS" == true ]]; then
        print_success "Performance tests completed"
    fi
    
    if [[ "$RUN_COVERAGE" == true ]]; then
        echo ""
        print_info "Coverage reports generated:"
        if [[ "$RUN_BACKEND_TESTS" == true ]]; then
            echo "  - Backend: backend/htmlcov/index.html"
        fi
        if [[ "$RUN_FRONTEND_UNIT_TESTS" == true ]]; then
            echo "  - Frontend: frontend/coverage/lcov-report/index.html"
        fi
    fi
    
    echo ""
    print_info "All reader functionality tests completed successfully!"
}

# Main execution
main() {
    print_header "KireMisu Reader Testing Suite"
    
    print_info "Test configuration:"
    echo "  - Backend tests: $([[ "$RUN_BACKEND_TESTS" == true ]] && echo "enabled" || echo "disabled")"
    echo "  - Frontend unit tests: $([[ "$RUN_FRONTEND_UNIT_TESTS" == true ]] && echo "enabled" || echo "disabled")"
    echo "  - E2E tests: $([[ "$RUN_E2E_TESTS" == true ]] && echo "enabled" || echo "disabled")"
    echo "  - Performance tests: $([[ "$RUN_PERFORMANCE_TESTS" == true ]] && echo "enabled" || echo "disabled")"
    echo "  - Coverage reports: $([[ "$RUN_COVERAGE" == true ]] && echo "enabled" || echo "disabled")"
    
    check_prerequisites
    setup_environment
    
    # Run tests in order
    if [[ "$RUN_BACKEND_TESTS" == true ]]; then
        run_backend_tests
    fi
    
    if [[ "$RUN_FRONTEND_UNIT_TESTS" == true ]]; then
        run_frontend_unit_tests
    fi
    
    if [[ "$RUN_E2E_TESTS" == true ]]; then
        run_e2e_tests
    fi
    
    generate_summary
}

# Run main function
main "$@"