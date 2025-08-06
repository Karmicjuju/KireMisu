#!/bin/bash

# Reading Progress Features Test Suite Runner
# This script runs all R-2 reading progress tests with proper environment setup

set -e

echo "🚀 KireMisu Reading Progress Test Suite"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test categories
run_unit_tests=true
run_integration_tests=true
run_e2e_tests=true
run_performance_tests=false
run_accessibility_tests=false
run_with_coverage=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --unit-only)
      run_integration_tests=false
      run_e2e_tests=false
      shift
      ;;
    --e2e-only)
      run_unit_tests=false
      run_integration_tests=false
      shift
      ;;
    --performance)
      run_performance_tests=true
      shift
      ;;
    --accessibility)
      run_accessibility_tests=true
      shift
      ;;
    --coverage)
      run_with_coverage=true
      shift
      ;;
    --all)
      run_performance_tests=true
      run_accessibility_tests=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --unit-only        Run only unit tests"
      echo "  --e2e-only         Run only E2E tests"
      echo "  --performance      Include performance tests"
      echo "  --accessibility    Include accessibility tests"
      echo "  --coverage         Run with coverage reporting"
      echo "  --all              Run all test categories"
      echo "  -h, --help         Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Function to check if Docker containers are running
check_docker_containers() {
  echo -e "${BLUE}📦 Checking Docker containers...${NC}"
  
  if ! docker-compose -f ../docker-compose.dev.yml ps | grep -q "Up"; then
    echo -e "${RED}❌ Docker containers are not running${NC}"
    echo "Please start the development environment:"
    echo "  cd .. && docker-compose -f docker-compose.dev.yml up -d"
    exit 1
  fi
  
  # Wait for services to be ready
  echo "⏳ Waiting for services to be ready..."
  sleep 5
  
  # Check if backend is responsive
  if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${YELLOW}⚠️  Backend not ready, waiting...${NC}"
    sleep 10
  fi
  
  # Check if frontend is responsive
  if ! curl -s http://localhost:3000 > /dev/null; then
    echo -e "${YELLOW}⚠️  Frontend not ready, waiting...${NC}"
    sleep 10
  fi
  
  echo -e "${GREEN}✅ Docker containers are ready${NC}"
}

# Function to run unit tests
run_unit() {
  echo -e "\n${BLUE}🧪 Running Unit Tests...${NC}"
  echo "=========================="
  
  local coverage_flag=""
  if [ "$run_with_coverage" = true ]; then
    coverage_flag="--coverage"
  fi
  
  # Run specific progress-related unit tests
  npm test -- tests/unit/reading-progress-comprehensive.test.tsx --verbose $coverage_flag
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
  else
    echo -e "${RED}❌ Unit tests failed${NC}"
    exit 1
  fi
}

# Function to run integration tests
run_integration() {
  echo -e "\n${BLUE}🔗 Running Integration Tests...${NC}"
  echo "==============================="
  
  local coverage_flag=""
  if [ "$run_with_coverage" = true ]; then
    coverage_flag="--coverage"
  fi
  
  npm test -- tests/integration/reading-progress-integration.test.tsx --verbose $coverage_flag
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Integration tests passed${NC}"
  else
    echo -e "${RED}❌ Integration tests failed${NC}"
    exit 1
  fi
}

# Function to run E2E tests
run_e2e() {
  echo -e "\n${BLUE}🎭 Running E2E Tests...${NC}"
  echo "======================="
  
  # Run comprehensive reading progress E2E tests
  npx playwright test tests/e2e/reading-progress-comprehensive.spec.ts --reporter=html
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ E2E tests passed${NC}"
  else
    echo -e "${RED}❌ E2E tests failed${NC}"
    echo "Check the Playwright report: npx playwright show-report"
    exit 1
  fi
}

# Function to run performance tests
run_performance() {
  echo -e "\n${BLUE}⚡ Running Performance Tests...${NC}"
  echo "==============================="
  
  npx playwright test tests/e2e/reading-progress-performance.spec.ts --reporter=html
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Performance tests passed${NC}"
  else
    echo -e "${RED}❌ Performance tests failed${NC}"
    exit 1
  fi
}

# Function to run accessibility tests
run_accessibility() {
  echo -e "\n${BLUE}♿ Running Accessibility Tests...${NC}"
  echo "=================================="
  
  # Install axe-playwright if not present
  if ! npm list axe-playwright > /dev/null 2>&1; then
    echo "Installing axe-playwright..."
    npm install --save-dev axe-playwright @axe-core/playwright
  fi
  
  npx playwright test tests/e2e/reading-progress-accessibility.spec.ts --reporter=html
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Accessibility tests passed${NC}"
  else
    echo -e "${RED}❌ Accessibility tests failed${NC}"
    exit 1
  fi
}

# Function to generate test report
generate_report() {
  echo -e "\n${BLUE}📊 Generating Test Report...${NC}"
  echo "============================"
  
  local report_file="test-results/progress-test-report-$(date +%Y%m%d-%H%M%S).md"
  mkdir -p test-results
  
  cat > "$report_file" << EOF
# Reading Progress Features Test Report

**Generated:** $(date)
**Environment:** Development Docker containers

## Test Summary

EOF

  if [ "$run_unit_tests" = true ]; then
    echo "- ✅ Unit Tests: Comprehensive component testing" >> "$report_file"
  fi
  
  if [ "$run_integration_tests" = true ]; then
    echo "- ✅ Integration Tests: Cross-component functionality" >> "$report_file"
  fi
  
  if [ "$run_e2e_tests" = true ]; then
    echo "- ✅ E2E Tests: Complete user workflows" >> "$report_file"
  fi
  
  if [ "$run_performance_tests" = true ]; then
    echo "- ✅ Performance Tests: Load and responsiveness validation" >> "$report_file"
  fi
  
  if [ "$run_accessibility_tests" = true ]; then
    echo "- ✅ Accessibility Tests: WCAG 2.1 AA compliance" >> "$report_file"
  fi

  cat >> "$report_file" << EOF

## Test Coverage Areas

### Core Components
- ProgressBar: Visual progress indicators with accessibility
- MarkReadButton: Interactive read/unread toggles
- DashboardStats: Statistics display and calculations
- ChapterList: Chapter progress visualization

### User Workflows
- Dashboard → Library → Series navigation
- Chapter marking and progress updates
- Real-time UI synchronization
- Cross-component state consistency

### Performance Metrics
- Page load times < 3 seconds
- Progress updates < 1 second
- Smooth animations and transitions
- Memory usage optimization

### Accessibility Compliance
- Screen reader compatibility
- Keyboard navigation support
- High contrast mode support
- WCAG 2.1 AA standards compliance

## Files Tested

### Unit Tests
- \`tests/unit/reading-progress-comprehensive.test.tsx\`

### Integration Tests
- \`tests/integration/reading-progress-integration.test.tsx\`

### E2E Tests
- \`tests/e2e/reading-progress-comprehensive.spec.ts\`
- \`tests/e2e/reading-progress-performance.spec.ts\`
- \`tests/e2e/reading-progress-accessibility.spec.ts\`

### Test Data & Utilities
- \`tests/fixtures/progress-test-data.ts\`
- \`tests/utils/progress-test-helpers.ts\`

EOF

  echo -e "${GREEN}📋 Test report generated: $report_file${NC}"
}

# Main execution
main() {
  echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
  
  # Check if we're in the frontend directory
  if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Must be run from the frontend directory${NC}"
    exit 1
  fi
  
  # Check Docker containers
  check_docker_containers
  
  # Install dependencies if needed
  if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
  fi
  
  # Run tests based on configuration
  if [ "$run_unit_tests" = true ]; then
    run_unit
  fi
  
  if [ "$run_integration_tests" = true ]; then
    run_integration
  fi
  
  if [ "$run_e2e_tests" = true ]; then
    run_e2e
  fi
  
  if [ "$run_performance_tests" = true ]; then
    run_performance
  fi
  
  if [ "$run_accessibility_tests" = true ]; then
    run_accessibility
  fi
  
  # Generate report
  generate_report
  
  echo -e "\n${GREEN}🎉 All tests completed successfully!${NC}"
  echo -e "${BLUE}📊 View detailed results in test-results/ directory${NC}"
  
  if [ "$run_e2e_tests" = true ] || [ "$run_performance_tests" = true ] || [ "$run_accessibility_tests" = true ]; then
    echo -e "${BLUE}🎭 View Playwright report: npx playwright show-report${NC}"
  fi
}

# Run main function
main "$@"