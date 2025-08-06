# KireMisu Reading Progress Test Suite

This directory contains comprehensive tests for the R-2 reading progress features, ensuring that users have an amazing experience when tracking their manga reading progress.

## Test Architecture

### 🧪 Unit Tests (`tests/unit/`)

**File:** `reading-progress-comprehensive.test.tsx`

Comprehensive component-level testing covering:
- **ProgressBar**: Visual indicators with animations, accessibility, and edge cases
- **MarkReadButton**: Interactive toggles with API integration and error handling
- **DashboardStats**: Statistics display with loading states and data validation
- **ChapterList**: Progress visualization with real-time updates

**Key Features:**
- Mock API responses and SWR data fetching
- Accessibility compliance testing (ARIA attributes, screen readers)
- Performance validation (animation smoothness, rapid updates)
- Error handling and edge case coverage
- Cross-browser compatibility considerations

### 🔗 Integration Tests (`tests/integration/`)

**File:** `reading-progress-integration.test.tsx`

Cross-component integration testing covering:
- **Navigation Flows**: Dashboard ↔ Library ↔ Series transitions
- **State Consistency**: Real-time updates across all UI components
- **Data Integrity**: Progress calculations remain accurate during user interactions
- **Concurrent Operations**: Multiple rapid chapter marking operations
- **Error Recovery**: Graceful handling of API failures

**Key Features:**
- Full application state management simulation
- Multi-component interaction testing
- Progress calculation validation
- Performance under load testing
- Error resilience validation

### 🎭 End-to-End Tests (`tests/e2e/`)

#### `reading-progress-comprehensive.spec.ts`
Complete user workflow validation:
- **Critical User Journeys**: Complete reading workflows with progress tracking
- **Dashboard Integration**: Statistics accuracy and real-time updates
- **Bulk Operations**: Series-wide mark-read functionality
- **Cross-Component Sync**: Progress consistency across different views

#### `reading-progress-performance.spec.ts`
Performance validation for production readiness:
- **Dashboard Performance**: Load times with large libraries (1000+ series)
- **Progress Calculations**: Efficiency with high chapter counts
- **Network Resilience**: Functionality on slow connections
- **Memory Management**: Resource usage during extended sessions

#### `reading-progress-accessibility.spec.ts`
Comprehensive accessibility compliance:
- **WCAG 2.1 AA Compliance**: Automated accessibility testing
- **Screen Reader Support**: Proper announcements and navigation
- **Keyboard Navigation**: Full keyboard-only operation
- **Visual Accessibility**: High contrast, reduced motion support

## Test Data & Utilities

### 📊 Test Fixtures (`tests/fixtures/progress-test-data.ts`)

Realistic test data generation:
- **Series Generation**: Configurable manga series with various states
- **Chapter Creation**: Realistic chapter data with progress states
- **Library Scenarios**: Pre-built test scenarios (empty, small, large libraries)
- **Statistics Calculation**: Accurate dashboard stats generation

**Available Scenarios:**
```typescript
TestScenarios.SMALL_LIBRARY()      // 5 series for quick testing
TestScenarios.MEDIUM_LIBRARY()     // 25 series for realistic testing  
TestScenarios.LARGE_LIBRARY()      // 100 series for performance testing
TestScenarios.COMPLETED_LIBRARY()  // All chapters read
TestScenarios.FRESH_LIBRARY()      // No chapters read
TestScenarios.MIXED_PROGRESS_LIBRARY() // Realistic reading patterns
```

### 🛠️ Test Helpers (`tests/utils/progress-test-helpers.ts`)

Utility functions for test setup and validation:

#### Jest/Unit Test Helpers
- **ProgressMockHelpers**: SWR mocking, API response setup, state management
- **ProgressAssertions**: Specialized assertions for progress data validation

#### Playwright/E2E Helpers  
- **ProgressE2EHelpers**: Navigation, element interaction, progress verification
- **Performance Measurement**: Load time tracking, interaction timing
- **Accessibility Testing**: ARIA validation, keyboard navigation testing

## Running Tests

### Quick Start

```bash
# Run all reading progress tests
./scripts/test-progress-features.sh

# Run with coverage
./scripts/test-progress-features.sh --coverage

# Run only unit tests
./scripts/test-progress-features.sh --unit-only

# Run E2E tests only
./scripts/test-progress-features.sh --e2e-only

# Include performance and accessibility tests
./scripts/test-progress-features.sh --all
```

### Individual Test Categories

```bash
# Unit tests only
npm test tests/unit/reading-progress-comprehensive.test.tsx

# Integration tests
npm test tests/integration/reading-progress-integration.test.tsx

# E2E comprehensive tests
npx playwright test tests/e2e/reading-progress-comprehensive.spec.ts

# Performance tests
npx playwright test tests/e2e/reading-progress-performance.spec.ts

# Accessibility tests
npx playwright test tests/e2e/reading-progress-accessibility.spec.ts
```

### Test Development

```bash
# Watch mode for unit tests
npm test -- --watch tests/unit/reading-progress-comprehensive.test.tsx

# Debug E2E tests
npx playwright test tests/e2e/reading-progress-comprehensive.spec.ts --debug

# UI mode for E2E development
npx playwright test --ui
```

## Docker Development Environment

All tests are designed to work with KireMisu's Docker development environment:

```bash
# Ensure containers are running
docker-compose -f ../docker-compose.dev.yml up -d

# Backend: http://localhost:8000
# Frontend: http://localhost:3000  
# Database: localhost:5432
```

## Success Criteria

The test suite validates that the R-2 reading progress feature provides an amazing user experience by ensuring:

### ✅ User Experience Excellence
- **Visual Feedback**: Progress bars are smooth, responsive, and accessible
- **Immediate Updates**: Changes reflect instantly across all UI components
- **Intuitive Navigation**: Users can easily track progress across their library
- **Error Resilience**: Graceful handling of network issues and API failures

### ✅ Performance Standards
- **Load Times**: Dashboard loads within 3 seconds, library within 4 seconds
- **Responsiveness**: Progress updates complete within 1 second
- **Scalability**: Handles libraries with 1000+ series without degradation
- **Memory Efficiency**: No memory leaks during extended usage

### ✅ Accessibility Compliance
- **WCAG 2.1 AA**: Full compliance with accessibility standards
- **Screen Readers**: Complete screen reader support with proper announcements
- **Keyboard Navigation**: All functionality accessible via keyboard
- **Visual Accessibility**: High contrast support, reduced motion respect

### ✅ Data Integrity
- **Calculation Accuracy**: Progress percentages are mathematically correct
- **State Consistency**: Data remains consistent across component boundaries
- **Persistence**: Progress survives page refreshes and session changes
- **Concurrent Safety**: Multiple operations don't corrupt data state

## Test Coverage Goals

- **Unit Tests**: 95%+ coverage of progress-related components
- **Integration Tests**: 100% coverage of critical user workflows  
- **E2E Tests**: Complete validation of all progress features
- **Performance Tests**: Validation under realistic load conditions
- **Accessibility Tests**: Full WCAG 2.1 AA compliance verification

## Contributing to Tests

When adding new progress-related features:

1. **Add Unit Tests**: Test component behavior in isolation
2. **Update Integration Tests**: Verify cross-component interactions
3. **Extend E2E Tests**: Validate complete user workflows
4. **Consider Performance**: Test impact on large libraries
5. **Verify Accessibility**: Ensure new features are accessible

### Test Patterns

```typescript
// Unit test example
describe('ProgressBar Component', () => {
  it('should display correct progress percentage', () => {
    render(<ProgressBar value={75} max={100} />);
    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('75%');
  });
});

// E2E test example  
test('user can mark chapter as read', async ({ page }) => {
  await page.goto('/library');
  await page.click('[data-testid="series-card"]');
  await page.click('[data-testid="mark-read-button"]');
  await expect(page.locator('[data-testid="mark-read-button"]')).toHaveText('✓ Read');
});
```

## Test Environment Setup

### Prerequisites
- Node.js 18+ with npm
- Docker and docker-compose
- KireMisu development environment running

### Dependencies
- **Jest**: Unit and integration testing
- **Playwright**: E2E testing with cross-browser support
- **Testing Library**: React component testing utilities
- **axe-playwright**: Accessibility testing automation

### Configuration Files
- `jest.config.js`: Jest configuration with coverage settings
- `playwright.config.ts`: Playwright configuration for E2E tests
- `tests/fixtures/`: Reusable test data and scenarios
- `tests/utils/`: Helper functions and test utilities

## Troubleshooting

### Common Issues

**Tests failing with network errors:**
- Ensure Docker containers are running: `docker-compose -f ../docker-compose.dev.yml up -d`
- Wait for services to be ready before running tests

**Playwright tests timing out:**
- Increase timeout in playwright.config.ts
- Check if frontend/backend are responding: `curl http://localhost:3000`

**Unit tests failing with import errors:**
- Verify Jest configuration includes module aliases
- Check that mocks are properly set up in test files

**Accessibility tests reporting violations:**
- Review specific violations in Playwright HTML report
- Update components to include proper ARIA attributes
- Test with actual screen readers for validation

### Debug Commands

```bash
# Verbose unit test output
npm test -- --verbose --no-coverage

# Debug specific E2E test
npx playwright test reading-progress-comprehensive.spec.ts --debug --headed

# Generate detailed coverage report
npm test -- --coverage --coverageReporters=html

# Check Docker container status
docker-compose -f ../docker-compose.dev.yml ps
```

---

This comprehensive test suite ensures that KireMisu's reading progress features deliver an exceptional user experience with reliability, performance, and accessibility at the forefront.