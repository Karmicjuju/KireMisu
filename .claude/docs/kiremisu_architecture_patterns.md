# KireMisu Architecture Patterns

This document defines reusable patterns and conventions for consistent development across the KireMisu codebase.

## API Design Patterns

### RESTful Conventions

All API endpoints follow REST principles with consistent naming and behavior:

```
GET    /api/v1/series          # List all series
GET    /api/v1/series/{id}     # Get single series
POST   /api/v1/series          # Create new series
PUT    /api/v1/series/{id}     # Update entire series
PATCH  /api/v1/series/{id}     # Partial update
DELETE /api/v1/series/{id}     # Delete series
```

### Endpoint Structure

```python
# backend/app/api/v1/endpoints/series.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.series import SeriesCreate, SeriesResponse, SeriesUpdate
from app.services.series import SeriesService

router = APIRouter(prefix="/series", tags=["series"])

@router.get("/", response_model=list[SeriesResponse])
async def list_series(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    service: SeriesService = Depends()
):
    """List all series with pagination."""
    return await service.list(db, skip=skip, limit=limit)

@router.post("/", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    series: SeriesCreate,
    db: AsyncSession = Depends(get_db),
    service: SeriesService = Depends()
):
    """Create a new series."""
    return await service.create(db, series)
```

### Error Handling

Consistent error responses across all endpoints:

```python
# backend/app/core/exceptions.py
from fastapi import HTTPException, status

class NotFoundError(HTTPException):
    def __init__(self, resource: str, id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id {id} not found"
        )

class ValidationError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": message}
        )

# Usage in endpoint
@router.get("/{series_id}")
async def get_series(series_id: UUID):
    series = await service.get(db, series_id)
    if not series:
        raise NotFoundError("Series", series_id)
    return series
```

### Response Format

All API responses follow a consistent structure:

```python
# Success response
{
    "data": {...},  # or [...] for lists
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 100
    }
}

# Error response
{
    "error": {
        "code": "validation_error",
        "message": "Invalid input",
        "details": {...}
    }
}
```

## Database Patterns

### Repository Pattern

Separate data access logic from business logic:

```python
# backend/app/repositories/base.py
from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: UUID) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def list(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

# backend/app/repositories/series.py
from app.models.series import Series
from app.repositories.base import BaseRepository

class SeriesRepository(BaseRepository[Series]):
    def __init__(self):
        super().__init__(Series)
    
    async def find_by_title(self, db: AsyncSession, title: str):
        result = await db.execute(
            select(Series).where(Series.title.ilike(f"%{title}%"))
        )
        return result.scalars().all()
```

### Service Layer Pattern

Business logic separated from data access:

```python
# backend/app/services/series.py
from app.repositories.series import SeriesRepository
from app.schemas.series import SeriesCreate

class SeriesService:
    def __init__(self):
        self.repository = SeriesRepository()
    
    async def create(self, db: AsyncSession, series_data: SeriesCreate):
        # Business logic validation
        existing = await self.repository.find_by_title(db, series_data.title)
        if existing:
            raise ValidationError("Series with this title already exists")
        
        # Create with enriched data
        series_dict = series_data.model_dump()
        series_dict["created_at"] = datetime.utcnow()
        
        return await self.repository.create(db, **series_dict)
    
    async def get_with_chapters(self, db: AsyncSession, series_id: UUID):
        series = await self.repository.get(db, series_id)
        if series:
            # Load related data
            await db.refresh(series, ["chapters"])
        return series
```

### JSONB Usage for Flexible Metadata

```python
# backend/app/models/series.py
from sqlalchemy import Column, String, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Series(Base):
    __tablename__ = "series"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False, index=True)
    
    # Flexible metadata storage
    metadata = Column(JSONB, default={})
    user_preferences = Column(JSONB, default={})
    external_ids = Column(JSONB, default={})  # {"mangadex": "...", "anilist": "..."}
    
    # Indexed JSONB queries
    __table_args__ = (
        Index("idx_series_metadata", metadata, postgresql_using="gin"),
    )

# Query example
async def find_by_genre(db: AsyncSession, genre: str):
    result = await db.execute(
        select(Series).where(
            Series.metadata["genres"].contains([genre])
        )
    )
    return result.scalars().all()
```

### Transaction Handling

```python
# backend/app/services/library.py
async def import_series_with_chapters(self, db: AsyncSession, import_data):
    async with db.begin():  # Automatic commit/rollback
        try:
            # Create series
            series = await self.series_repo.create(db, **import_data.series)
            
            # Create chapters
            for chapter_data in import_data.chapters:
                chapter_data["series_id"] = series.id
                await self.chapter_repo.create(db, **chapter_data)
            
            # Update metadata
            await self.metadata_service.enrich(db, series.id)
            
            return series
        except Exception as e:
            # Transaction automatically rolled back
            logger.error(f"Import failed: {e}")
            raise
```

## Frontend Patterns

### Component Structure

```typescript
// frontend/src/components/series/SeriesCard.tsx
import { FC } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Series } from '@/types/series'

interface SeriesCardProps {
  series: Series
  onSelect?: (series: Series) => void
}

export const SeriesCard: FC<SeriesCardProps> = ({ series, onSelect }) => {
  return (
    <Card 
      className="cursor-pointer hover:shadow-lg transition-shadow"
      onClick={() => onSelect?.(series)}
    >
      <CardHeader>
        <img 
          src={series.coverUrl} 
          alt={series.title}
          className="w-full h-64 object-cover rounded"
        />
      </CardHeader>
      <CardContent>
        <h3 className="font-bold text-lg">{series.title}</h3>
        <p className="text-sm text-gray-600">{series.author}</p>
      </CardContent>
    </Card>
  )
}
```

### State Management with Zustand

```typescript
// frontend/src/stores/library.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Series } from '@/types/series'

interface LibraryState {
  series: Series[]
  loading: boolean
  error: string | null
  
  // Actions
  fetchSeries: () => Promise<void>
  addSeries: (series: Series) => void
  updateSeries: (id: string, updates: Partial<Series>) => void
  deleteSeries: (id: string) => void
}

export const useLibraryStore = create<LibraryState>()(
  persist(
    (set, get) => ({
      series: [],
      loading: false,
      error: null,
      
      fetchSeries: async () => {
        set({ loading: true, error: null })
        try {
          const response = await api.get('/series')
          set({ series: response.data, loading: false })
        } catch (error) {
          set({ error: error.message, loading: false })
        }
      },
      
      addSeries: (series) => {
        set((state) => ({ 
          series: [...state.series, series] 
        }))
      },
      
      updateSeries: (id, updates) => {
        set((state) => ({
          series: state.series.map(s => 
            s.id === id ? { ...s, ...updates } : s
          )
        }))
      },
      
      deleteSeries: (id) => {
        set((state) => ({
          series: state.series.filter(s => s.id !== id)
        }))
      }
    }),
    {
      name: 'library-storage',
      partialize: (state) => ({ series: state.series })  // Only persist series
    }
  )
)
```

### API Client Pattern

```typescript
// frontend/src/lib/api/client.ts
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// frontend/src/lib/api/series.ts
import { apiClient } from './client'
import { Series, SeriesCreate } from '@/types/series'

export const seriesApi = {
  list: () => apiClient.get<Series[]>('/series'),
  get: (id: string) => apiClient.get<Series>(`/series/${id}`),
  create: (data: SeriesCreate) => apiClient.post<Series>('/series', data),
  update: (id: string, data: Partial<Series>) => 
    apiClient.patch<Series>(`/series/${id}`, data),
  delete: (id: string) => apiClient.delete(`/series/${id}`)
}
```

### Custom Hooks Pattern

```typescript
// frontend/src/hooks/useSeries.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { seriesApi } from '@/lib/api/series'

export function useSeries(id: string) {
  return useQuery({
    queryKey: ['series', id],
    queryFn: () => seriesApi.get(id),
    enabled: !!id
  })
}

export function useSeriesList() {
  return useQuery({
    queryKey: ['series'],
    queryFn: seriesApi.list
  })
}

export function useCreateSeries() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: seriesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series'] })
    }
  })
}
```

## Testing Patterns

### Backend Test Fixtures

```python
# backend/tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test")
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def sample_series(db_session):
    """Create a sample series for testing."""
    series = Series(
        title="Test Series",
        author="Test Author",
        metadata={"genres": ["action", "adventure"]}
    )
    db_session.add(series)
    await db_session.commit()
    return series
```

### Frontend Test Patterns

```typescript
// frontend/tests/setup.ts
import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)

afterEach(() => {
  cleanup()
})

// frontend/tests/utils.tsx
import { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

export function renderWithProviders(
  ui: ReactElement,
  options?: RenderOptions
) {
  return render(ui, { wrapper: AllTheProviders, ...options })
}
```

## File Organization Patterns

### Feature-Based Structure

```
backend/app/
├── features/
│   ├── series/
│   │   ├── models.py      # Database models
│   │   ├── schemas.py     # Pydantic schemas
│   │   ├── repository.py  # Data access
│   │   ├── service.py     # Business logic
│   │   ├── endpoints.py   # API routes
│   │   └── tests/         # Feature tests
│   └── chapters/
│       └── ...

frontend/src/
├── features/
│   ├── library/
│   │   ├── components/    # Feature components
│   │   ├── hooks/         # Feature hooks
│   │   ├── api/           # API calls
│   │   ├── stores/        # State management
│   │   └── types/         # TypeScript types
│   └── reader/
│       └── ...
```

### Naming Conventions

- **Files**: `kebab-case` for TypeScript/React, `snake_case` for Python
- **Components**: `PascalCase` for React components
- **Functions/Variables**: `camelCase` for TypeScript, `snake_case` for Python
- **Constants**: `SCREAMING_SNAKE_CASE` for both
- **Types/Interfaces**: `PascalCase` with `I` prefix for interfaces optional

## Summary

These patterns provide:
- **Consistency**: Same patterns across all features
- **Maintainability**: Clear separation of concerns
- **Testability**: Easy to mock and test in isolation
- **Scalability**: Patterns that work for small and large codebases
- **Developer Experience**: Predictable structure reduces cognitive load