# Development Rules for KireMisu

## Code Quality Standards

### Python Backend Development
- Use Python 3.13+ with type hints for all functions and methods
- Follow FastAPI patterns with async/await for I/O operations
- Use Pydantic models for all API request/response schemas
- Implement proper dependency injection for database sessions and services
- Use structured logging with contextual information for all operations
- Handle exceptions gracefully with appropriate HTTP status codes

### Frontend Development
- Use TypeScript with strict mode enabled
- Follow Next.js App Router patterns (Server Components by default, Client Components when needed)
- Use Zustand for state management, avoid React Context for performance-critical reading state
- Implement proper error boundaries and loading states
- Use the shadcn/ui component library consistently
- Follow responsive design principles for mobile/tablet access

### Database Design
- Use PostgreSQL with JSONB for flexible metadata storage
- Always use UUIDs for primary keys to avoid conflicts
- Create proper indexes for JSONB queries and foreign key relationships
- Use database migrations for all schema changes
- Never store binary data directly in the database (use file paths/references)

## Architecture Patterns

### File Processing
```python
# Always use this pattern for CPU-bound file operations
class FileProcessor:
    def __init__(self):
        self.cpu_pool = ThreadPoolExecutor(max_workers=2)
        
    async def process_chapter(self, file_path: str) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.cpu_pool, 
            self._process_blocking, 
            file_path
        )
```

### API Client Pattern
```python
# Use this pattern for external API integration
class MangaDxClient:
    def __init__(self):
        self.rate_limiter = AsyncRateLimiter(max_requests=5, time_window=1)
    
    async def search_manga(self, query: str):
        await self.rate_limiter.acquire()
        # Implementation with proper error handling
```

### Database Access
```python
# Always use dependency injection for database access
async def get_series(
    series_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> Series:
    # Implementation
```

## Security Requirements

### API Security
- All API endpoints must require authentication except health checks
- Use API keys with configurable expiration
- Implement rate limiting on all endpoints
- Validate and sanitize all user inputs
- Use HTTPS in production deployments

### File Handling
- Never execute user-uploaded files
- Validate file types and sizes before processing
- Sandbox file processing operations
- Use secure temporary directories for file operations
- Clean up temporary files after processing

## Performance Guidelines

### Backend Performance
- Use async I/O for all network operations
- Implement proper connection pooling for database and HTTP clients
- Cache frequently accessed metadata in Redis or in-memory cache
- Use database indexes for all query patterns
- Implement pagination for large result sets

### Frontend Performance
- Use Server Components for initial page loads
- Implement image optimization for manga covers and pages
- Use React.memo() for expensive component renders
- Implement virtual scrolling for large lists
- Cache API responses with appropriate TTLs

## Error Handling

### Backend Errors
- Use structured exceptions with proper HTTP status codes
- Log all errors with contextual information
- Implement graceful degradation for external API failures
- Provide meaningful error messages to users
- Never expose internal error details in production

### Frontend Errors
- Implement error boundaries for component errors
- Show user-friendly error messages
- Provide retry mechanisms for failed operations
- Log client-side errors for debugging
- Handle offline scenarios gracefully

## Documentation Standards

### Code Documentation
- Document all public APIs with examples
- Include type hints and docstrings for all functions
- Document configuration options and environment variables
- Provide setup instructions for development environment
- Document deployment procedures and requirements

### User Documentation
- Create user guides for all major features
- Provide troubleshooting guides for common issues
- Document API endpoints with OpenAPI/Swagger
- Include migration guides for updates
- Provide example configurations for common scenarios

## Git Workflow

### Commit Standards
- Use conventional commit messages (feat:, fix:, docs:, etc.)
- Include tests with feature implementations
- Update documentation with code changes
- Use proper branch naming conventions

### Branch Management
- Use feature branches for all development
- Require PR reviews for main branch changes
- Run all tests before merging
- Use semantic versioning for releases
- Tag releases with detailed changelogs

