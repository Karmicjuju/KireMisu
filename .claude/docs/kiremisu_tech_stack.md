# KireMisu Tech Stack - Complete Architecture

## High-Level Technology Choices

| Component | Technology | Version | Primary Rationale |
|-----------|------------|---------|-------------------|
| **Backend API** | FastAPI | 0.115+ | Async performance, auto-generated docs, type safety |
| **Python Runtime** | Python | 3.12+ | Modern async features, performance improvements |
| **Database** | PostgreSQL + JSONB | 15+ | ACID compliance with flexible metadata support |
| **ORM** | SQLAlchemy | 2.0+ | Mature, flexible, excellent PostgreSQL support |
| **Frontend Framework** | Next.js | 15.5+ | SSR performance, App Router, React Server Components |
| **UI Library** | React + TypeScript | 19+ / 5.6+ | Component model, type safety, ecosystem |
| **UI Components** | shadcn/ui + Radix UI | Latest | Accessible, customizable, well-designed |
| **CSS Framework** | Tailwind CSS | 3.4+ | Utility-first, excellent DX, consistent styling |
| **State Management** | Zustand | 5.0+ | Minimal API, excellent performance for reading apps |
| **HTTP Client (Backend)** | HTTPX | 0.27+ | Async support, connection pooling, HTTP/2 |
| **API Client (Frontend)** | Axios | 1.7+ | Interceptors, request cancellation, TypeScript support |
| **File Processing** | PIL + PyMuPDF + rarfile | Latest | Comprehensive manga format support |
| **Background Jobs** | PostgreSQL-based queue | - | Eliminates Redis dependency, simpler deployment |
| **Package Manager (Python)** | uv | Latest | 10-100x faster than pip, built-in venv management |
| **Package Manager (JS)** | pnpm | 9.0+ | Efficient disk usage, fast installs, workspace support |
| **Python Linting** | Ruff | 0.8+ | 10-100x faster than traditional tools, comprehensive |
| **JS/TS Linting** | ESLint + Prettier | 9.0+ / 3.0+ | Industry standard, TypeScript support |
| **Testing (Backend)** | pytest + pytest-asyncio | 8.0+ | Powerful fixtures, async support, extensive plugins |
| **Testing (Frontend)** | Vitest | 2.0+ | Fast, Vite-powered, Jest-compatible |
| **E2E Testing** | Playwright | 1.49+ | Cross-browser, reliable, great debugging |
| **Pre-commit Hooks** | pre-commit | 4.0+ | Automated code quality checks |
| **Logging** | Structlog | 24.0+ | Structured logging, context preservation |
| **Monitoring** | Prometheus + Grafana | Latest | Self-hosted metrics and visualization |
| **Containerization** | Docker | 24.0+ | Standard containerization, multi-stage builds |
| **Orchestration** | Docker Compose | 2.0+ | Simple multi-container deployment |
| **CI/CD** | GitHub Actions | - | Native GitHub integration, free for public repos |

---

## Backend Architecture

### FastAPI + Python 3.12+
**Why:** FastAPI provides async performance critical for file processing workloads while generating OpenAPI documentation essential for future AI agent integration. Python's rich ecosystem handles manga file formats effectively.

**Key Implementation Pattern:**
```python
# Thread pool isolation for CPU-bound work
class FileProcessor:
    def __init__(self):
        self.cpu_pool = ThreadPoolExecutor(max_workers=2)  # Conservative
        self.io_pool = ThreadPoolExecutor(max_workers=4)   # More aggressive
    
    async def process_chapter(self, file_path: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.cpu_pool, 
            self._process_blocking, 
            file_path
        )
```

**Trade-offs:**
- ✅ Rapid development with extensive libraries
- ✅ Excellent async I/O for API operations  
- ✅ Easy migration path to Rust for performance-critical components
- ❌ CPU-bound file processing requires careful threading
- ❌ GIL limitations for parallel image processing

### PostgreSQL + JSONB
**Why:** Provides ACID guarantees for critical manga library data while JSONB fields enable flexible metadata schemas that evolve with new manga sources and user customization needs.

**Key Schema Pattern:**
```sql
-- Hybrid relational + document approach
CREATE TABLE series (
    id UUID PRIMARY KEY,
    title_primary TEXT NOT NULL,
    genres TEXT[] NOT NULL,
    watching_config JSONB,     -- Flexible per-source configuration
    user_metadata JSONB,       -- User customization
    source_metadata JSONB      -- External API responses
);

-- GIN indexes for fast JSONB queries
CREATE INDEX idx_series_watching ON series USING GIN (watching_config);
```

**Trade-offs:**
- ✅ ACID compliance prevents data corruption
- ✅ JSONB enables schema evolution without migrations
- ✅ Excellent query performance with proper indexing
- ✅ Battle-tested reliability for self-hosted deployments
- ❌ More complex than document-only databases
- ❌ Requires careful index management for JSONB performance

---

## Frontend Architecture

### Next.js 15.4+ + React 19+ + TypeScript
**Why:** Server-side rendering improves initial load performance for large manga libraries. TypeScript prevents runtime errors critical in file management applications. App Router provides modern React patterns.

**Key Architecture Pattern:**
```typescript
// Server Components for initial data loading
async function LibraryPage() {
  const series = await getSeriesData(); // Server-side fetch
  return <LibraryGrid series={series} />;
}

// Client Components for interactive features
'use client'
function MangaReader({ chapterId }: { chapterId: string }) {
  const [currentPage, setCurrentPage] = useState(1);
  // Interactive reading logic
}
```

**Trade-offs:**
- ✅ Fast initial page loads with SSR
- ✅ Type safety prevents UI bugs
- ✅ Excellent developer experience
- ✅ Strong ecosystem for component libraries
- ❌ Build complexity higher than vanilla React
- ❌ Server/client boundary requires careful planning

### Zustand State Management
**Why:** Manga readers require high-frequency state updates (page navigation) without performance penalties. Zustand's minimal API reduces cognitive overhead for non-UI developers.

**Key Implementation:**
```typescript
// Optimized for reading performance
const useReaderStore = create<ReaderState>((set, get) => ({
  currentPage: 1,
  // High-frequency updates without re-renders
  setPage: (page) => set({ currentPage: page }),
  // Batch operations for efficiency
  loadChapter: async (chapterId) => {
    const chapter = await fetchChapter(chapterId);
    set({ pages: chapter.pages, currentPage: 1 });
  }
}));
```

**Trade-offs:**
- ✅ Excellent performance for high-frequency updates
- ✅ Simple mental model for backend developers
- ✅ Built-in persistence support
- ✅ Minimal bundle size impact
- ❌ Less structured than Redux for complex state
- ❌ Smaller ecosystem than Redux

---

## File Processing

### Multi-Format Support (PIL + PyMuPDF + rarfile)
**Why:** Manga exists in diverse formats (.cbz, .cbr, folders, PDFs). Supporting all formats reduces user friction when importing existing collections.

**Key Architecture:**
```python
# Unified interface for different storage types
class ChapterProcessor:
    @staticmethod
    async def process_chapter(file_path: str) -> dict:
        storage_type = detect_storage_type(file_path)
        
        if storage_type == "archive":
            return await process_archive(file_path)
        elif storage_type == "folder":
            return await process_folder(file_path) 
        elif storage_type == "pdf":
            return await process_pdf(file_path)
```

**Trade-offs:**
- ✅ Comprehensive format support reduces import friction
- ✅ Abstracted interface enables easy format additions
- ✅ Proven libraries with good error handling
- ❌ Multiple dependencies increase complexity
- ❌ CPU-intensive processing requires threading consideration

---

## External Integration

### HTTPX Client Library
**Why:** MangaDx integration requires robust HTTP handling with rate limiting. HTTPX provides unified async/sync interface essential for testing while supporting HTTP/2 for better performance.

**Key Pattern:**
```python
# Production: Async with rate limiting
class MangaDxClient:
    async def search_manga(self, query: str):
        await self.rate_limiter.acquire()
        async with httpx.AsyncClient() as client:
            return await client.get(f"/search?q={query}")

# Testing: Sync interface  
def test_search():
    with httpx.Client() as client:
        response = client.get("/search?q=test")
        assert response.status_code == 200
```

**Trade-offs:**
- ✅ Same interface for production and testing
- ✅ HTTP/2 support improves API performance
- ✅ Excellent async integration with FastAPI
- ❌ Newer than requests (less battle-tested)
- ❌ Larger dependency than pure requests

---

## Background Processing

### PostgreSQL-Based Job Queue
**Why:** Eliminates Redis dependency while providing job persistence and ACID guarantees. Simplifies deployment and reduces operational complexity for self-hosted users.

**Key Implementation:**
```python
# Simple job queue using existing database
class JobQueue(Base):
    __tablename__ = "job_queue"
    id = Column(UUID, primary_key=True)
    job_type = Column(String, index=True)
    payload = Column(JSONB)
    status = Column(String, default="pending", index=True)
    scheduled_at = Column(DateTime, default=datetime.utcnow, index=True)

# Worker process
async def process_jobs():
    while True:
        job = await get_next_pending_job()
        if job:
            await execute_job(job)
        else:
            await asyncio.sleep(5)
```

**Trade-offs:**
- ✅ No additional infrastructure dependencies
- ✅ ACID guarantees for job persistence
- ✅ Easier backup and recovery (single database)
- ✅ Simpler deployment for self-hosted users
- ❌ Less optimized than dedicated queue systems
- ❌ May not scale to extremely high job volumes

---

## Development Tooling

### Ruff + UV + Pre-commit
**Why:** Development velocity crucial for MVP delivery. Ruff provides 10x faster linting than traditional tools. UV eliminates slow pip operations. Pre-commit prevents quality regressions.

**Key Configuration:**
```toml
# Single tool replaces black + isort + flake8
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "B", "UP"]  # Essential rules only
target-version = "py311"

# Fast package management
[tool.uv]
dev-dependencies = ["ruff", "mypy", "pytest"]
```

**Trade-offs:**
- ✅ 10-100x faster development cycles
- ✅ Single configuration file reduces complexity
- ✅ Modern tooling with active development
- ❌ Newer tools with smaller community
- ❌ Fallback to traditional tools requires reconfiguration

---

## Observability

### Structlog + Prometheus
**Why:** Self-hosted deployments require excellent observability without external service dependencies. Structured JSON logs enable efficient debugging. Prometheus provides standard metrics without cloud lock-in.

**Key Pattern:**
```python
# Automatic context binding for operations
logger = structlog.get_logger(__name__)

async def process_chapter(file_path: str):
    operation_logger = logger.bind(
        operation_type="file_processing",
        file_path=file_path
    )
    
    operation_logger.info("Processing started")
    try:
        result = await do_processing()
        operation_logger.info("Processing completed", 
                            duration=duration, 
                            pages=result.page_count)
    except Exception as e:
        operation_logger.error("Processing failed", error=str(e))
```

**Trade-offs:**
- ✅ Machine-readable logs enable efficient debugging
- ✅ No external service dependencies
- ✅ Standard Prometheus metrics work with existing monitoring
- ✅ WebSocket streaming provides real-time log viewing
- ❌ More complex than simple print statements
- ❌ JSON logs harder to read manually

---

## Deployment Strategy

### Docker
**Why:** Self-hosted users need deployment flexibility from simple Docker Compose. Containerization ensures consistent environments across development and production.

**Key Architecture:**
```yaml
# Simple deployment (Docker Compose)
services:
  backend:
    image: kiremisu/backend
    volumes:
      - ${MANGA_LIBRARY}:/manga:ro
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

```

**Trade-offs:**
- ✅ Deployment flexibility from simple to sophisticated
- ✅ Consistent environments reduce deployment issues
- ✅ Easy backup and migration strategies
- ✅ Cloud-native patterns enable future scaling
- ❌ Additional complexity compared to bare metal
- ❌ Resource overhead for containerization

---

## Migration Strategy

### Python → Rust Evolution Path
**Why:** Start with Python for rapid MVP development, then migrate performance-critical file processing to Rust when justified by user scale and performance requirements.

**Interface Abstraction:**
```python
# Common interface enables seamless migration
class FileProcessorProtocol(Protocol):
    async def process_chapter(self, file_path: str) -> dict: ...

# MVP: Python implementation
class PythonFileProcessor: ...

# Future: Rust implementation  
class RustFileProcessor: ...

# Factory pattern enables runtime selection
processor = FileProcessorFactory.create(config.processor_type)
```

**Migration Benefits:**
- ✅ Deliver MVP quickly with Python
- ✅ Identify real performance bottlenecks with user data
- ✅ Migrate only performance-critical components
- ✅ Interface abstraction makes migration invisible to users

---

## Development Environment Setup

### Python Environment (Backend)
```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Run development server
uv run fastapi dev app/main.py
```

### Node Environment (Frontend)
```bash
# Install pnpm
npm install -g pnpm

# Install dependencies
pnpm install

# Run development server
pnpm dev
```

### Database Setup
```bash
# Start PostgreSQL with Docker
docker run -d \
  --name kiremisu-postgres \
  -e POSTGRES_DB=kiremisu \
  -e POSTGRES_USER=kiremisu \
  -e POSTGRES_PASSWORD=development \
  -p 5432:5432 \
  postgres:15-alpine
```

---

## Configuration Management

### Environment Variables
All configuration via environment variables for 12-factor app compliance:

```bash
# Backend (.env)
DATABASE_URL=postgresql://kiremisu:password@localhost/kiremisu
SECRET_KEY=your-secret-key-here
MANGADEX_API_URL=https://api.mangadex.org
STORAGE_PATH=/data/manga
LOG_LEVEL=INFO

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=KireMisu
```

### Configuration Files

#### Backend (pyproject.toml)
```toml
[project]
name = "kiremisu"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "sqlalchemy>=2.0.0",
    "httpx>=0.27.0",
    "structlog>=24.0.0",
    # ... other dependencies
]

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "B", "UP", "N", "S"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
```

#### Frontend (package.json)
```json
{
  "name": "kiremisu-frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "test": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint . --fix",
    "format": "prettier --write ."
  }
}
```

---

## Testing Strategy Overview

### Test Pyramid
1. **Unit Tests** (70%) - Fast, isolated component tests
2. **Integration Tests** (20%) - API endpoints, database operations
3. **E2E Tests** (10%) - Critical user journeys only

### Backend Testing
```python
# tests/test_api/test_series.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_series(client: AsyncClient):
    response = await client.get("/api/v1/series")
    assert response.status_code == 200
```

### Frontend Testing
```typescript
// tests/components/SeriesCard.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SeriesCard } from '@/components/SeriesCard'

describe('SeriesCard', () => {
  it('renders series title', () => {
    render(<SeriesCard title="Naruto" />)
    expect(screen.getByText('Naruto')).toBeInTheDocument()
  })
})
```

### E2E Testing
```typescript
// tests/e2e/library.spec.ts
import { test, expect } from '@playwright/test'

test('user can browse library', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible()
})
```

---

## Summary

This tech stack prioritizes:
- **Developer Velocity**: Fast tools (uv, pnpm, Ruff) for rapid iteration
- **Type Safety**: TypeScript frontend, Pydantic backend for runtime validation
- **Self-Hosted Simplicity**: Single PostgreSQL database, Docker Compose deployment
- **Testing Confidence**: Comprehensive test coverage across all layers
- **Maintainability**: Consistent tooling, automated formatting, clear patterns

The architecture supports evolution from simple Docker deployment for individual users to Kubernetes orchestration for advanced deployments, with file processing performance scaling from Python to Rust based on actual usage patterns.