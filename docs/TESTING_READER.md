# KireMisu Reader Testing Documentation

This document provides comprehensive testing documentation for the KireMisu manga reader functionality, including test strategies, implementation details, and instructions for running tests.

## Table of Contents

1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Test Categories](#test-categories)
4. [Running Tests](#running-tests)
5. [Test Data and Fixtures](#test-data-and-fixtures)
6. [Performance Testing](#performance-testing)
7. [Accessibility Testing](#accessibility-testing)
8. [Error Handling Tests](#error-handling-tests)
9. [CI/CD Integration](#cicd-integration)
10. [Writing New Tests](#writing-new-tests)

## Overview

The KireMisu reader testing strategy covers all aspects of the manga reading experience:

- **Frontend Component Testing**: React component unit tests with Jest and React Testing Library
- **Backend API Testing**: FastAPI endpoint testing with pytest and async support
- **End-to-End Testing**: Full user journey testing with Playwright
- **Performance Testing**: Load testing, memory usage, and scalability validation
- **Error Handling**: Comprehensive error scenario coverage
- **Accessibility**: Keyboard navigation and screen reader compatibility

## Test Architecture

### Backend Testing
- **Framework**: pytest with asyncio support
- **Database**: PostgreSQL test database with complete isolation
- **Mocking**: Unittest.mock for file system operations and external dependencies
- **Fixtures**: Comprehensive test data generation with various manga formats

### Frontend Testing
- **Unit Tests**: Jest + React Testing Library
- **E2E Tests**: Playwright with cross-browser support
- **Mocking**: MSW (Mock Service Worker) for API mocking in E2E tests

### Test Data
- **Formats Supported**: CBZ, CBR, PDF, folder structures
- **Test Fixtures**: Automated generation of test manga files
- **Edge Cases**: Corrupted files, empty archives, permission issues

## Test Categories

### 1. Unit Tests

#### Backend API Unit Tests
```bash
# Run backend unit tests
cd backend
pytest tests/api/test_reader.py -v

# Run with coverage
pytest tests/api/test_reader.py --cov=kiremisu.api.reader --cov-report=html
```

**Coverage Areas:**
- Chapter info retrieval
- Page streaming from various formats
- Reading progress tracking
- Series chapters listing
- Input validation and error responses

#### Frontend Component Unit Tests
```bash
# Run frontend unit tests
cd frontend
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

**Coverage Areas:**
- Component rendering and state management
- Keyboard navigation handlers
- Image loading and error states
- Progress tracking integration
- UI visibility toggles

### 2. Integration Tests

#### API Integration Tests
```bash
# Run integration tests
pytest tests/api/test_reader.py tests/integration/ -m "not slow"
```

**Focus Areas:**
- Database transaction integrity
- File system interaction
- Concurrent request handling
- Authentication and authorization (when implemented)

### 3. End-to-End Tests

#### Smoke Tests
```bash
# Run E2E smoke tests
cd frontend
npm run test:e2e -- tests/e2e/reader-smoke.spec.ts

# Run in UI mode for debugging
npm run test:e2e:ui
```

**Test Scenarios:**
- Navigate to reader from library
- Load chapter and display first page
- Navigate pages using keyboard and mouse
- Update reading progress
- Handle loading states
- Error scenarios (chapter not found, network issues)

#### Cross-Browser Testing
```bash
# Run on all browsers
npm run test:e2e

# Run specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### 4. Performance Tests

```bash
# Run performance tests
pytest tests/performance/test_reader_performance.py -m slow -v

# Run specific performance test
pytest tests/performance/test_reader_performance.py::TestReaderPerformance::test_concurrent_page_requests_performance -s
```

**Performance Metrics:**
- Page loading time (< 2 seconds per page)
- Concurrent request handling (> 30 req/s)
- Memory usage with large files (< 100MB increase)
- Database query performance (< 1 second for 100 chapters)

### 5. Error Handling Tests

```bash
# Run error handling tests
pytest tests/api/test_reader_error_handling.py -v
```

**Error Scenarios:**
- Corrupted manga files
- Missing files or directories
- Permission denied errors
- Network timeouts
- Database connection failures
- Invalid input validation

## Running Tests

### Prerequisites

#### Backend Testing
```bash
# Install dependencies
cd backend
pip install -e ".[dev]"

# Set up test database
createdb kiremisu_test
export TEST_DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/kiremisu_test"
```

#### Frontend Testing
```bash
# Install dependencies
cd frontend
npm install

# Install Playwright browsers
npx playwright install
```

### Test Commands

#### Run All Tests
```bash
# Backend tests
cd backend && pytest

# Frontend unit tests
cd frontend && npm test

# Frontend E2E tests
cd frontend && npm run test:e2e
```

#### Run Specific Test Categories
```bash
# API tests only
pytest tests/api/ -v

# Reader-specific tests
pytest tests/api/test_reader.py -v

# Performance tests
pytest tests/performance/ -m slow -v

# E2E smoke tests
npm run test:e2e -- tests/e2e/reader-smoke.spec.ts
```

#### Generate Coverage Reports
```bash
# Backend coverage
pytest --cov=kiremisu --cov-report=html --cov-report=term

# Frontend coverage
npm run test:coverage
```

## Test Data and Fixtures

### Using Reader Test Fixtures

```python
from tests.fixtures.reader_fixtures import ReaderTestFixtures

def test_with_fixtures():
    fixtures = ReaderTestFixtures()
    
    # Create test library
    library_path = fixtures.create_test_library()
    
    # Create edge case files
    edge_cases = fixtures.create_edge_case_files(library_path)
    
    # Run tests...
    
    # Automatic cleanup
    fixtures.cleanup()
```

### Creating Custom Test Data

```python
from tests.fixtures.reader_fixtures import create_test_cbz, create_test_pdf_chapter

# Create CBZ with 10 pages
cbz_path = create_test_cbz(pages=10)

# Create PDF with 5 pages
pdf_path = create_test_pdf_chapter(pages=5)
```

## Performance Testing

### Performance Benchmarks

| Operation | Target Performance | Test Method |
|-----------|-------------------|-------------|
| Page Load | < 2 seconds | `test_large_chapter_performance` |
| Concurrent Requests | > 30 req/s | `test_concurrent_page_requests_performance` |
| Progress Updates | > 10 updates/s | `test_progress_update_performance` |
| Memory Usage | < 100MB increase | `test_memory_usage_large_pages` |
| DB Queries | < 1 second for 100 chapters | `test_database_query_performance` |

### Running Performance Tests

```bash
# Run all performance tests
pytest tests/performance/ -m slow -v -s

# Run with profiling
pytest tests/performance/ -m slow --profile

# Generate performance report
pytest tests/performance/ -m slow --benchmark-json=performance_report.json
```

## Accessibility Testing

### Keyboard Navigation Tests

The reader supports comprehensive keyboard navigation:

- **Arrow Keys**: Navigate pages
- **Space**: Next page
- **Home/End**: First/last page
- **F**: Toggle fit mode
- **U**: Toggle UI visibility
- **Escape**: Exit reader

### Testing Accessibility

```typescript
// E2E accessibility test
test('should be accessible via keyboard navigation', async ({ page }) => {
  await page.goto('/reader/test-chapter-1');
  
  // Test focus management
  const backButton = page.getByRole('button', { name: 'Back' });
  await backButton.focus();
  await expect(backButton).toBeFocused();
  
  // Test keyboard navigation
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
});
```

## Error Handling Tests

### Comprehensive Error Coverage

1. **File System Errors**:
   - Missing files
   - Corrupted archives
   - Permission denied
   - Disk space issues

2. **Network Errors**:
   - Connection timeouts
   - Request failures
   - Large file handling

3. **Database Errors**:
   - Connection failures
   - Transaction rollbacks
   - Concurrent modifications

4. **Application Errors**:
   - Invalid parameters
   - Authentication failures
   - Resource limits

### Example Error Test

```python
@pytest.mark.asyncio
async def test_corrupted_file_handling(client, sample_chapter):
    """Test handling of corrupted manga files."""
    with patch('os.path.exists', return_value=True):
        with patch('zipfile.ZipFile', side_effect=zipfile.BadZipFile()):
            response = await client.get(f"/api/reader/chapter/{sample_chapter.id}/page/0")
            
            assert response.status_code == 500
            assert "Failed to extract page" in response.json()["detail"]
```

## CI/CD Integration

### GitHub Actions Configuration

```yaml
name: Reader Tests

on:
  push:
    paths:
      - 'backend/kiremisu/api/reader.py'
      - 'frontend/src/app/**/reader/**'
      - 'tests/**'

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: kiremisu
          POSTGRES_DB: kiremisu_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -e ".[dev]"
      
      - name: Run tests
        run: |
          cd backend
          pytest tests/api/test_reader.py --cov=kiremisu.api.reader
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://postgres:kiremisu@localhost:5432/kiremisu_test

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run unit tests
        run: |
          cd frontend
          npm run test:coverage
      
      - name: Install Playwright
        run: |
          cd frontend
          npx playwright install --with-deps
      
      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
```

## Writing New Tests

### Backend API Test Template

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestNewReaderFeature:
    """Test new reader feature."""
    
    @pytest.mark.asyncio
    async def test_new_feature_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        # Add fixtures as needed
    ):
        """Test successful operation."""
        # Arrange
        # Set up test data
        
        # Act
        response = await client.get("/api/reader/new-endpoint")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
    
    @pytest.mark.asyncio
    async def test_new_feature_error_case(self, client: AsyncClient):
        """Test error handling."""
        response = await client.get("/api/reader/invalid")
        assert response.status_code == 404
```

### Frontend Component Test Template

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import NewReaderComponent from '@/components/NewReaderComponent';

// Mock dependencies
jest.mock('next/navigation');

describe('NewReaderComponent', () => {
  beforeEach(() => {
    // Setup mocks
  });

  it('should render correctly', () => {
    render(<NewReaderComponent />);
    
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });

  it('should handle user interaction', async () => {
    render(<NewReaderComponent />);
    
    const button = screen.getByRole('button', { name: 'Action' });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText('Result')).toBeInTheDocument();
    });
  });
});
```

### E2E Test Template

```typescript
import { test, expect } from '@playwright/test';

test.describe('New Reader Feature', () => {
  test('should work end-to-end', async ({ page }) => {
    // Navigate to reader
    await page.goto('/reader/test-chapter');
    
    // Interact with feature
    await page.getByRole('button', { name: 'New Feature' }).click();
    
    // Verify result
    await expect(page.getByText('Feature Result')).toBeVisible();
  });
});
```

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Realistic Data**: Use fixtures that closely match real manga files and data
3. **Error Coverage**: Test both happy paths and error scenarios
4. **Performance Awareness**: Include performance assertions for critical operations
5. **Accessibility**: Ensure all features work with keyboard navigation and screen readers
6. **Cross-Browser**: Run E2E tests on multiple browsers
7. **Documentation**: Keep test documentation up-to-date with new features

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   ```bash
   export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/kiremisu_test"
   ```

2. **Playwright Browser Issues**:
   ```bash
   npx playwright install --force
   ```

3. **Mock File System Issues**:
   - Ensure proper cleanup in test fixtures
   - Use temporary directories for test files

4. **Async Test Failures**:
   - Use proper async/await patterns
   - Set appropriate timeouts for slow operations

5. **Memory Issues in Performance Tests**:
   - Run performance tests in isolation
   - Monitor system resources during tests

For additional help, check the test logs and ensure all dependencies are properly installed.