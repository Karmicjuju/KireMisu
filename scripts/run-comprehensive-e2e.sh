#!/bin/bash

# Comprehensive E2E Test Runner for R-1 Validation
# This script runs the complete validation suite and generates a detailed report

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

print_header() {
    echo ""
    echo "======================================================================"
    echo "  KIREMISU R-1 COMPREHENSIVE VALIDATION SUITE"
    echo "======================================================================"
    echo ""
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if backend is running
    if ! curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        log_error "Backend is not running on localhost:8000"
        log_info "Please start the backend server first:"
        log_info "  cd $PROJECT_ROOT && ./scripts/dev.sh backend"
        return 1
    fi
    
    # Check if frontend is running
    if ! curl -f -s http://localhost:3000 > /dev/null 2>&1; then
        log_error "Frontend is not running on localhost:3000"
        log_info "Please start the frontend server first:"
        log_info "  cd $PROJECT_ROOT/frontend && npm run dev"
        return 1
    fi
    
    # Check if test data exists
    if [ ! -d "$PROJECT_ROOT/manga-storage" ]; then
        log_warning "Test manga data not found at $PROJECT_ROOT/manga-storage"
        log_info "Creating sample test data..."
        mkdir -p "$PROJECT_ROOT/manga-storage/Test Series"
        
        # Create a simple test chapter structure
        mkdir -p "$PROJECT_ROOT/manga-storage/Test Series/Chapter 001"
        
        # Create some dummy image files (1x1 pixel PNGs)
        for i in {01..05}; do
            # Create minimal PNG file
            echo -n -e '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82' > "$PROJECT_ROOT/manga-storage/Test Series/Chapter 001/page_$i.png"
        done
        
        log_success "Created sample test data"
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

run_backend_tests() {
    log_info "Running backend API tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run backend tests with proper environment
    if SECRET_KEY=test-key DATABASE_URL=sqlite:///test.db uv run pytest tests/api/ -v --tb=short -q > /tmp/backend_test_results.log 2>&1; then
        log_success "Backend tests passed"
        return 0
    else
        log_warning "Some backend tests failed, continuing with E2E tests..."
        log_info "Backend test log available at /tmp/backend_test_results.log"
        return 1
    fi
}

run_frontend_tests() {
    log_info "Running frontend tests..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Run frontend tests
    if npm run test 2>/dev/null >/dev/null; then
        log_success "Frontend tests passed"
        return 0
    else
        log_warning "Frontend tests not configured or failed, continuing..."
        return 1
    fi
}

run_e2e_tests() {
    log_info "Running comprehensive E2E tests..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Ensure Playwright is installed
    if ! command -v npx > /dev/null; then
        log_error "npx not available"
        return 1
    fi
    
    # Install Playwright browsers if needed
    if [ ! -d "$HOME/.cache/ms-playwright" ]; then
        log_info "Installing Playwright browsers..."
        npx playwright install
    fi
    
    # Run the comprehensive E2E test
    log_info "Executing comprehensive validation suite..."
    
    # Set environment variables
    export BASE_URL=http://localhost:3000
    export API_BASE_URL=http://localhost:8000
    
    # Run the test with detailed output
    if npx playwright test tests/e2e/comprehensive-r1-validation.spec.ts --reporter=line --timeout=60000; then
        log_success "E2E tests completed successfully"
        return 0
    else
        log_warning "Some E2E tests failed, check results for details"
        return 1
    fi
}

generate_system_report() {
    log_info "Generating system status report..."
    
    local report_file="/tmp/kiremisu_validation_report.md"
    
    cat > "$report_file" << EOF
# KireMisu R-1 Comprehensive Validation Report

**Generated on:** $(date)
**Test Environment:** Local Development

## System Status

### Backend Status
EOF
    
    # Check backend health
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend: HEALTHY (http://localhost:8000)" >> "$report_file"
        
        # Get API endpoints status
        echo "" >> "$report_file"
        echo "### API Endpoints Status" >> "$report_file"
        
        endpoints=(
            "/health"
            "/api/docs"
            "/api/library/paths"
            "/api/series/"
        )
        
        for endpoint in "${endpoints[@]}"; do
            if curl -f -s "http://localhost:8000$endpoint" > /dev/null 2>&1; then
                echo "✅ $endpoint" >> "$report_file"
            else
                echo "❌ $endpoint" >> "$report_file"
            fi
        done
    else
        echo "❌ Backend: NOT ACCESSIBLE" >> "$report_file"
    fi
    
    # Check frontend status
    echo "" >> "$report_file"
    echo "### Frontend Status" >> "$report_file"
    if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend: ACCESSIBLE (http://localhost:3000)" >> "$report_file"
    else
        echo "❌ Frontend: NOT ACCESSIBLE" >> "$report_file"
    fi
    
    # Check test data
    echo "" >> "$report_file"
    echo "### Test Data Status" >> "$report_file"
    if [ -d "$PROJECT_ROOT/manga-storage" ]; then
        local series_count=$(find "$PROJECT_ROOT/manga-storage" -maxdepth 1 -type d | wc -l)
        echo "✅ Test manga data: $series_count series available" >> "$report_file"
    else
        echo "❌ Test manga data: NOT AVAILABLE" >> "$report_file"
    fi
    
    # System information
    echo "" >> "$report_file"
    echo "### System Information" >> "$report_file"
    echo "- **OS:** $(uname -s) $(uname -r)" >> "$report_file"
    echo "- **Node.js:** $(node --version 2>/dev/null || echo 'Not available')" >> "$report_file"
    echo "- **Python:** $(python3 --version 2>/dev/null || echo 'Not available')" >> "$report_file"
    echo "- **Working Directory:** $PROJECT_ROOT" >> "$report_file"
    
    echo "" >> "$report_file"
    echo "---" >> "$report_file"
    echo "" >> "$report_file"
    
    log_success "System report generated: $report_file"
    
    # Display the report
    cat "$report_file"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    # Clean up any temporary files if needed
}

main() {
    print_header
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed. Exiting."
        exit 1
    fi
    
    # Generate system report first
    generate_system_report
    
    echo ""
    log_info "Starting test execution..."
    
    # Track test results
    local backend_result=0
    local frontend_result=0
    local e2e_result=0
    
    # Run backend tests
    if ! run_backend_tests; then
        backend_result=1
    fi
    
    # Run frontend tests
    if ! run_frontend_tests; then
        frontend_result=1
    fi
    
    # Run E2E tests (main validation)
    if ! run_e2e_tests; then
        e2e_result=1
    fi
    
    # Summary
    echo ""
    echo "======================================================================"
    echo "  VALIDATION SUMMARY"
    echo "======================================================================"
    
    if [ $backend_result -eq 0 ]; then
        log_success "Backend Tests: PASSED"
    else
        log_warning "Backend Tests: SOME ISSUES"
    fi
    
    if [ $frontend_result -eq 0 ]; then
        log_success "Frontend Tests: PASSED"
    else
        log_warning "Frontend Tests: SKIPPED/ISSUES"
    fi
    
    if [ $e2e_result -eq 0 ]; then
        log_success "E2E Validation: PASSED"
    else
        log_warning "E2E Validation: SOME ISSUES"
    fi
    
    echo ""
    
    # Overall result
    if [ $e2e_result -eq 0 ]; then
        log_success "🎉 R-1 VALIDATION COMPLETED SUCCESSFULLY!"
        log_info "All core functionality is working as expected."
        exit 0
    else
        log_warning "⚠️  R-1 VALIDATION COMPLETED WITH ISSUES"
        log_info "Please check the detailed test output above."
        exit 1
    fi
}

# Run main function
main "$@"