# Testing Strategy & Commands

## Quick Test Commands
```bash
# Run all tests (use this for CI/CD)
./scripts/test-all.sh

# Development workflow
cd backend && uv run pytest tests/api/test_reader.py -v --cov
cd frontend && npm run test:watch  # For TDD
cd frontend && npm run test:e2e:ui  # Visual debugging

# Performance benchmarks
cd backend && uv run pytest tests/performance/ -m slow -v -s
```

## Test Categories & Performance Targets

### Unit Tests
- **Backend API**: 90%+ coverage, all endpoints tested
- **Frontend Components**: 85%+ coverage, all interactions tested
- **File Processing**: 100% coverage, all formats supported

### Performance Benchmarks
| Operation | Target | Test Command |
|-----------|--------|--------------|
| Page Load | < 2 seconds | `test_large_chapter_performance` |
| Concurrent Requests | > 30 req/s | `test_concurrent_page_requests_performance` |
| Memory Usage | < 100MB increase | `test_memory_usage_large_pages` |

### End-to-End Tests
```bash
# Smoke tests (fast)
npm run test:e2e -- tests/e2e/reader-smoke.spec.ts

# Full E2E suite
npm run test:e2e

# Cross-browser testing
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Writing New Tests

### Backend Test Template
```python
import pytest
from httpx import AsyncClient

class TestNewFeature:
    @pytest.mark.asyncio
    async def test_success_case(self, client: AsyncClient):
        response = await client.get("/api/new-endpoint")
        assert response.status_code == 200
        
    @pytest.mark.asyncio 
    async def test_error_case(self, client: AsyncClient):
        response = await client.get("/api/invalid")
        assert response.status_code == 404
```

### Frontend Test Template
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import NewComponent from '@/components/NewComponent';

describe('NewComponent', () => {
  it('should handle user interaction', async () => {
    render(<NewComponent />);
    fireEvent.click(screen.getByRole('button', { name: 'Action' }));
    expect(screen.getByText('Result')).toBeInTheDocument();
  });
});
```

### E2E Test Template
```typescript
import { test, expect } from '@playwright/test';

test('should work end-to-end', async ({ page }) => {
  await page.goto('/reader/test-chapter');
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByText('Page 2')).toBeVisible();
});
```

## Test Data & Fixtures
```python
# Use built-in fixtures
from tests.fixtures.reader_fixtures import ReaderTestFixtures

def test_with_fixtures():
    fixtures = ReaderTestFixtures()
    library_path = fixtures.create_test_library()
    # Test with realistic data
    fixtures.cleanup()  # Automatic cleanup
```

For comprehensive testing documentation, see the original TESTING_READER.md in backup.
