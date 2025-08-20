# API Development Patterns

## FastAPI + Async Patterns

### Thread Pool Isolation for File Processing
```python
# CPU-bound work isolation
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

### Database Patterns
```python
# Hybrid relational + document approach
CREATE TABLE series (
    id UUID PRIMARY KEY,
    title_primary TEXT NOT NULL,
    watching_config JSONB,     -- Flexible configuration
    user_metadata JSONB,       -- User customization
    source_metadata JSONB      -- External API responses
);

# GIN indexes for JSONB performance
CREATE INDEX idx_series_watching ON series USING GIN (watching_config);
```

### Error Handling Patterns
```python
from kiremisu.exceptions import MangaNotFoundError, FileProcessingError

@router.get("/chapter/{chapter_id}")
async def get_chapter(chapter_id: UUID):
    try:
        chapter = await chapter_service.get_by_id(chapter_id)
        return chapter
    except MangaNotFoundError:
        raise HTTPException(status_code=404, detail="Chapter not found")
    except FileProcessingError as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
```

## Authentication Patterns

### JWT Implementation
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)) -> User:
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await user_service.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Route Protection
```python
@router.get("/api/series/{series_id}")
async def get_series(
    series_id: UUID,
    current_user: User = Depends(get_current_user)
):
    # User-scoped data access
    series = await series_service.get_user_series(series_id, current_user.id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    return series
```

## File Processing Patterns

### Multi-Format Support
```python
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

### Secure File Handling
```python
def validate_file_path(base_path: str, file_path: str) -> str:
    """Validate file path to prevent directory traversal."""
    base = Path(base_path).resolve()
    target = (base / file_path).resolve()
    
    if not target.is_relative_to(base):
        raise ValueError("Invalid file path: directory traversal detected")
    
    return str(target)
```

## External API Integration

### MangaDx Client Pattern
```python
class MangaDxClient:
    def __init__(self):
        self.base_url = "https://api.mangadx.org"
        self.rate_limiter = AsyncLimiter(max_rate=5, time_period=1)  # 5 req/sec
    
    async def search_manga(self, query: str) -> List[dict]:
        await self.rate_limiter.acquire()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/manga",
                params={"title": query}
            )
            response.raise_for_status()
            return response.json()["data"]
    
    async def get_chapter_list(self, manga_id: str) -> List[dict]:
        await self.rate_limiter.acquire()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/manga/{manga_id}/feed"
            )
            response.raise_for_status()
            return response.json()["data"]
```

## Background Job Patterns

### PostgreSQL-Based Job Queue
```python
class JobQueue:
    @staticmethod
    async def enqueue_job(job_type: str, payload: dict, priority: int = 0):
        async with get_db_session() as session:
            job = Job(
                job_type=job_type,
                payload=payload,
                priority=priority,
                status="pending"
            )
            session.add(job)
            await session.commit()
    
    @staticmethod
    async def get_next_job() -> Optional[Job]:
        async with get_db_session() as session:
            result = await session.execute(
                select(Job)
                .where(Job.status == "pending")
                .order_by(Job.priority.desc(), Job.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            return result.scalar_one_or_none()
```

## Response Patterns

### Consistent API Responses
```python
from pydantic import BaseModel
from typing import Optional, List, Any

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

@router.get("/api/series", response_model=PaginatedResponse)
async def list_series(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * per_page
    
    series_list, total = await series_service.list_paginated(
        user_id=current_user.id,
        offset=offset,
        limit=per_page
    )
    
    return PaginatedResponse(
        items=series_list,
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
        has_prev=page > 1
    )
```

## Validation Patterns

### Input Validation with Pydantic
```python
from pydantic import BaseModel, Field, validator
import html

class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    genres: List[str] = Field(default_factory=list, max_items=20)
    
    @validator('title', 'author')
    def sanitize_text(cls, v):
        return html.escape(v.strip()) if v else v
    
    @validator('genres')
    def validate_genres(cls, v):
        if not isinstance(v, list):
            raise ValueError('Genres must be a list')
        return [html.escape(genre.strip()) for genre in v if genre.strip()]
```

## Testing Patterns

### API Test Helpers
```python
@pytest.fixture
async def authenticated_client(client: AsyncClient, test_user: User):
    token = create_access_token(data={"sub": str(test_user.id)})
    client.headers = {"Authorization": f"Bearer {token}"}
    return client

@pytest.mark.asyncio
async def test_series_crud(authenticated_client: AsyncClient):
    # Create
    series_data = {
        "title": "Test Manga",
        "author": "Test Author"
    }
    response = await authenticated_client.post("/api/series", json=series_data)
    assert response.status_code == 201
    series = response.json()
    
    # Read
    response = await authenticated_client.get(f"/api/series/{series['id']}")
    assert response.status_code == 200
    
    # Update
    update_data = {"title": "Updated Title"}
    response = await authenticated_client.put(f"/api/series/{series['id']}", json=update_data)
    assert response.status_code == 200
    
    # Delete
    response = await authenticated_client.delete(f"/api/series/{series['id']}")
    assert response.status_code == 204
```

For complete implementation examples, see the codebase and existing API endpoints.
