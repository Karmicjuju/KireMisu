# Testing Guidelines for KireMisu

## Testing Philosophy

### Test-Driven Development
- Write tests before implementing features when possible
- Use tests to validate requirements and design decisions
- Maintain test coverage above 90% for backend business logic
- Write tests that document expected behavior and edge cases

### Testing Pyramid
- **Unit Tests (70%)**: Fast, isolated tests for individual functions and classes
- **Integration Tests (25%)**: Tests for component interactions and workflows
- **End-to-End Tests (5%)**: Full user journey tests for critical paths

## Backend Testing Patterns

### Unit Testing with pytest
```python
# Example test structure for manga file processing
import pytest
from unittest.mock import Mock, patch
from kiremisu.core.file_processor import FileProcessor

class TestFileProcessor:
    @pytest.fixture
    def file_processor(self):
        return FileProcessor()
    
    @pytest.fixture
    def sample_cbz_path(self, tmp_path):
        # Create sample CBZ file for testing
        cbz_path = tmp_path / "test_chapter.cbz"
        # Implementation to create test file
        return str(cbz_path)
    
    async def test_process_cbz_file_success(self, file_processor, sample_cbz_path):
        result = await file_processor.process_chapter(sample_cbz_path)
        
        assert result["format"] == "cbz"
        assert result["page_count"] > 0
        assert "pages" in result
        assert len(result["pages"]) == result["page_count"]
    
    async def test_process_corrupted_file_raises_error(self, file_processor, tmp_path):
        corrupted_file = tmp_path / "corrupted.cbz"
        corrupted_file.write_bytes(b"not a valid zip file")
        
        with pytest.raises(FileProcessingError):
            await file_processor.process_chapter(str(corrupted_file))
```

### API Testing with FastAPI TestClient
```python
# Example API integration tests
from fastapi.testclient import TestClient
from kiremisu.main import app
from kiremisu.core.database import get_db_session

@pytest.fixture
def test_db():
    # Setup test database
    pass

@pytest.fixture
def client(test_db):
    app.dependency_overrides[get_db_session] = lambda: test_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def test_create_series_endpoint(client, test_db):
    series_data = {
        "title": "Test Manga",
        "author": "Test Author",
        "description": "Test description"
    }
    
    response = client.post("/api/series", json=series_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == series_data["title"]
    assert "id" in data
```

### Database Testing Patterns
```python
# Example database layer testing
from sqlalchemy.ext.asyncio import AsyncSession
from kiremisu.core.repositories import SeriesRepository

@pytest.fixture
async def db_session():
    # Create test database session
    pass

@pytest.fixture
def series_repo(db_session):
    return SeriesRepository(db_session)

async def test_series_repository_create(series_repo):
    series_data = SeriesCreate(
        title="Test Series",
        author="Test Author"
    )
    
    series = await series_repo.create(series_data)
    
    assert series.id is not None
    assert series.title == series_data.title
    assert series.created_at is not None

async def test_series_repository_find_by_title(series_repo):
    # Create test data
    await series_repo.create(SeriesCreate(title="Unique Title"))
    
    found_series = await series_repo.find_by_title("Unique Title")
    
    assert found_series is not None
    assert found_series.title == "Unique Title"
```

### External API Testing with Mocks
```python
# Example testing external API integration
@pytest.fixture
def mock_mangadx_client():
    with patch('kiremisu.integrations.mangadx.MangaDxClient') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance

async def test_search_manga_success(mock_mangadx_client):
    # Setup mock response
    mock_mangadx_client.search_manga.return_value = {
        "data": [
            {
                "id": "test-id",
                "attributes": {
                    "title": {"en": "Test Manga"},
                    "description": {"en": "Test description"}
                }
            }
        ]
    }
    
    service = MangaSearchService(mock_mangadx_client)
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "Test Manga"
    mock_mangadx_client.search_manga.assert_called_once_with("test query")
```

## Frontend Testing Patterns

### Component Testing with React Testing Library
```typescript
// Example component tests
import { render, screen, fireEvent } from '@testing-library/react'
import { SeriesCard } from '@/components/SeriesCard'

const mockSeries = {
  id: '1',
  title: 'Test Manga',
  author: 'Test Author',
  cover: '/test-cover.jpg',
  readChapters: 5,
  totalChapters: 10
}

describe('SeriesCard', () => {
  it('renders series information correctly', () => {
    render(<SeriesCard series={mockSeries} />)
    
    expect(screen.getByText('Test Manga')).toBeInTheDocument()
    expect(screen.getByText('Test Author')).toBeInTheDocument()
    expect(screen.getByText('5/10')).toBeInTheDocument()
  })
  
  it('calls onClick when card is clicked', () => {
    const mockOnClick = jest.fn()
    render(<SeriesCard series={mockSeries} onClick={mockOnClick} />)
    
    fireEvent.click(screen.getByRole('button'))
    
    expect(mockOnClick).toHaveBeenCalledWith(mockSeries)
  })
})
```

### State Management Testing
```typescript
// Example Zustand store testing
import { act, renderHook } from '@testing-library/react'
import { useReaderStore } from '@/stores/readerStore'

describe('useReaderStore', () => {
  beforeEach(() => {
    useReaderStore.getState().reset()
  })
  
  it('loads chapter correctly', async () => {
    const { result } = renderHook(() => useReaderStore())
    
    await act(async () => {
      await result.current.loadChapter('test-chapter-id')
    })
    
    expect(result.current.currentChapter).toBeDefined()
    expect(result.current.currentPage).toBe(1)
    expect(result.current.isLoading).toBe(false)
  })
})
```

### API Integration Testing
```typescript
// Example API hook testing
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSeries } from '@/hooks/useSeries'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useSeries', () => {
  it('fetches series data successfully', async () => {
    const { result } = renderHook(() => useSeries('test-id'), {
      wrapper: createWrapper()
    })
    
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    
    expect(result.current.data).toBeDefined()
    expect(result.current.data.id).toBe('test-id')
  })
})
```

## Test Data Management

### Fixtures and Factories
```python
# Example test data factories
import factory
from kiremisu.core.models import Series, Chapter

class SeriesFactory(factory.Factory):
    class Meta:
        model = Series
    
    title = factory.Sequence(lambda n: f"Test Series {n}")
    author = "Test Author"
    description = "Test description"
    status = "ongoing"
    
class ChapterFactory(factory.Factory):
    class Meta:
        model = Chapter
    
    number = factory.Sequence(lambda n: n)
    title = factory.LazyAttribute(lambda obj: f"Chapter {obj.number}")
    series = factory.SubFactory(SeriesFactory)
```

### Test Database Management
```python
# Example test database setup
@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    async with AsyncSession(test_engine) as session:
        yield session
        await session.rollback()
```

## Performance Testing

### Load Testing Examples
```python
# Example performance tests for file processing
import time
import asyncio
from concurrent.futures import as_completed

async def test_file_processing_performance():
    processor = FileProcessor()
    large_files = [f"test_file_{i}.cbz" for i in range(100)]
    
    start_time = time.time()
    
    tasks = [processor.process_chapter(file) for file in large_files]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    assert processing_time < 60  # Should process 100 files in under 60 seconds
    assert len(results) == 100
    assert all(result["status"] == "success" for result in results)
```

### Frontend Performance Testing
```typescript
// Example performance testing for reading interface
import { render, screen } from '@testing-library/react'
import { MangaReader } from '@/components/MangaReader'

describe('MangaReader Performance', () => {
  it('renders large chapter without performance issues', () => {
    const largeChapter = {
      id: 'test',
      pages: Array.from({ length: 200 }, (_, i) => ({
        id: i,
        url: `/page-${i}.jpg`
      }))
    }
    
    const startTime = performance.now()
    render(<MangaReader chapter={largeChapter} />)
    const endTime = performance.now()
    
    expect(endTime - startTime).toBeLessThan(1000) // Under 1 second
    expect(screen.getByTestId('manga-reader')).toBeInTheDocument()
  })
})
```

## Test Environment Setup

### Backend Test Configuration
```python
# pytest.ini configuration
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=kiremisu
    --cov-report=html
    --cov-report=term-missing
    --asyncio-mode=auto
asyncio_mode = auto
```

### Frontend Test Configuration
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
}
```

## Continuous Integration Testing

### GitHub Actions Workflow
```yaml
# Example CI testing workflow
name: Test Suite
on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
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
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          pytest --cov=kiremisu --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test -- --coverage --watchAll=false
```

## Testing Best Practices

### Test Organization
- Group related tests in classes or describe blocks
- Use descriptive test names that explain the scenario
- Follow Arrange-Act-Assert pattern consistently
- Keep tests independent and isolated
- Clean up test data after each test

### Mock Strategy
- Mock external dependencies (APIs, file system, databases)
- Use real implementations for internal components when possible
- Verify mock interactions when behavior is important
- Reset mocks between tests to avoid interference

### Test Data Strategy
- Use factories for creating test data
- Keep test data minimal but realistic
- Use fixtures for shared test setup
- Avoid hardcoded values in favor of generated data