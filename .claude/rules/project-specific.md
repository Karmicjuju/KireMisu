# KireMisu Project-Specific Instructions

## Project Context and Goals

### Primary Objectives
KireMisu is a self-hosted manga reader and library management system designed to replace and improve upon existing solutions like Kavita, Readarr, and Houdoku. The focus is on creating a unified, metadata-rich platform that works seamlessly in self-hosted environments.

### Target Users
- **Self-hosting enthusiasts** who run their own servers
- **Manga collectors** who need advanced organization features
- **Power users** who want automation and customization
- **Casual readers** who want a simple, unified reading experience

### Key Differentiators
- **MangaDx Integration**: Seamless search, metadata, and watching system
- **Rich Metadata**: Extensive tagging, annotations, and customization
- **File Organization**: Bulk renaming and restructuring capabilities
- **API-First**: Full automation support for power users
- **Cloud-Native**: Designed for Docker/Kubernetes from day one

## Development Phases

### Phase 1: Foundation (MVP)
**Goal**: Create a working manga library system with core features

**Backend Requirements**:
- FastAPI application with async architecture
- PostgreSQL database with JSONB metadata storage
- File processing system for .cbz, .cbr, folders, and PDFs
- Basic REST API for library management
- MangaDx API integration for metadata enrichment

**Frontend Requirements**:
- Next.js application with Server/Client component architecture
- Library browsing with grid/list views and filtering
- Series detail pages with chapter management
- Basic manga reader interface
- Settings management for library paths

**Key Features to Implement**:
1. Library scanning and file indexing
2. Metadata fetching from MangaDx
3. Basic reading interface with page navigation
4. User-defined tags and lists
5. Search and filtering system

### Phase 2: Advanced Features
**Goal**: Add power-user features and automation

**New Features**:
1. MangaDx watching system with notifications
2. Chapter annotation and note-taking
3. Bulk file renaming and organization
4. Advanced filtering and smart lists
5. Reading progress tracking and sync
6. API authentication and external automation support

### Phase 3: Polish and Scale
**Goal**: Optimize performance and add advanced features

**Enhancements**:
1. Multi-user support with role-based access
2. Performance optimization for large libraries
3. Mobile app or enhanced responsive design
4. Additional content source integrations
5. Community features and sharing

## Architecture Decisions

### Database Schema Strategy
```sql
-- Core entity relationships
Series (id, title, author, status, metadata_json)
├── Chapters (id, series_id, number, title, file_path, read_status)
├── Tags (id, series_id, tag_name, tag_type)
└── UserLists (id, user_id, series_id, list_name)

-- Flexible metadata storage
Series.metadata_json = {
  "mangadx_id": "uuid",
  "genres": ["action", "adventure"],
  "cover_url": "https://...",
  "description": "...",
  "user_tags": ["currently-reading", "favorite"],
  "reading_progress": {...},
  "custom_fields": {...}
}
```

### File Processing Strategy
- **Source of Truth**: File system remains authoritative
- **Non-Destructive**: Never modify original files without explicit user action
- **Format Support**: CBZ, CBR, PDF, folder-based manga
- **Async Processing**: Use ThreadPoolExecutor for CPU-bound operations
- **Error Handling**: Graceful degradation for corrupted or missing files

### API Design Principles
- **RESTful Design**: Standard HTTP methods and status codes
- **Consistent Responses**: Standardized error and success formats
- **Pagination**: Cursor-based pagination for large datasets
- **Filtering**: Query parameter-based filtering and sorting
- **Versioning**: API versioning strategy for future compatibility

## Implementation Guidelines

### Backend Implementation Order
1. **Database Models**: Define SQLAlchemy models with JSONB fields
2. **File Processing**: Implement format-specific processors (CBZ, CBR, PDF)
3. **Core Services**: Library scanning, metadata management, search
4. **API Endpoints**: CRUD operations for series, chapters, lists
5. **MangaDx Integration**: Search, metadata fetching, watching system
6. **Background Jobs**: Async processing for file operations

### Frontend Implementation Order
1. **Component Library**: Set up shadcn/ui and design system
2. **Layout Structure**: Navigation, header, responsive layout
3. **Library Views**: Grid/list browsing with filtering
4. **Series Management**: Detail pages, chapter lists, metadata editing
5. **Reading Interface**: Page navigation, zoom, reading modes
6. **Settings & Admin**: Library configuration, API settings

### Key Integration Points
- **File Watching**: Monitor library directories for changes
- **Metadata Sync**: Periodic updates from MangaDx API
- **Progress Tracking**: Reading state management across devices
- **Error Handling**: Graceful handling of missing files or API failures

## Feature-Specific Requirements

### MangaDx Integration
```python
# Rate limiting is critical for API stability
class MangaDxClient:
    def __init__(self):
        self.rate_limiter = AsyncRateLimiter(
            max_requests=5,  # Conservative rate limiting
            time_window=1.0,
            burst_size=10
        )
    
    async def search_manga(self, query: str, limit: int = 20):
        await self.rate_limiter.acquire()
        # Implementation with retry logic and caching
```

### File Processing Requirements
- **Memory Efficiency**: Stream large files, don't load entirely into memory
- **Thumbnail Generation**: Create cached thumbnails for covers and pages
- **Format Detection**: Automatic detection of manga file formats
- **Error Recovery**: Handle corrupted archives gracefully

### Reading Interface Requirements
- **Performance**: Smooth page navigation with preloading
- **Reading Modes**: Single page, two-page spread, vertical scroll
- **Accessibility**: Keyboard navigation and screen reader support
- **Responsive**: Touch-friendly interface for tablets/mobile

### Annotation System Requirements
- **Chapter-Level Notes**: Rich text annotations per chapter
- **Page Bookmarks**: Mark specific pages for reference
- **Export/Import**: Backup and restore user annotations
- **Search**: Full-text search across all user notes

## Quality Standards

### Performance Targets
- **Library Scanning**: Handle 10,000+ chapters without blocking UI
- **Search Response**: Sub-200ms response for local library searches
- **Reader Loading**: Page transitions under 100ms
- **API Response**: 95th percentile under 500ms for database queries

### Security Requirements
- **Input Validation**: Sanitize all user inputs including file paths
- **File Access**: Restrict file operations to configured library paths
- **API Security**: Rate limiting and authentication for all endpoints
- **Error Disclosure**: Never expose internal paths or system details

### Compatibility Requirements
- **Browser Support**: Modern browsers (Chrome 100+, Firefox 100+, Safari 15+)
- **Container Support**: Docker and Kubernetes deployment
- **Database Support**: PostgreSQL 13+ with JSONB features
- **Python Version**: Python 3.11+ for performance and type improvements

## Testing Strategy

### Critical Test Scenarios
1. **Large Library Performance**: Test with 1000+ series, 50,000+ chapters
2. **File Format Compatibility**: Test all supported manga formats
3. **API Rate Limiting**: Verify MangaDx integration respects limits
4. **Concurrent Access**: Multiple users accessing library simultaneously
5. **Error Recovery**: Handling missing files, corrupted data, API failures

### Mock Data Requirements
- **Realistic File Structures**: Sample manga in various formats
- **MangaDx API Responses**: Cached responses for consistent testing
- **Large Dataset Simulation**: Generate test data for performance testing
- **Error Scenarios**: Corrupted files, network failures, invalid data

## Deployment Considerations

### Container Strategy
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as backend-build
# Build backend dependencies

FROM node:18-alpine as frontend-build  
# Build Next.js application

FROM python:3.11-slim as runtime
# Combine built artifacts for production
```

### Environment Configuration
```yaml
# Essential environment variables
DATABASE_URL: postgresql+asyncpg://user:pass@db:5432/kiremisu
LIBRARY_PATHS: /manga:/light-novels:/comics
MANGADX_API_URL: https://api.mangadex.org
REDIS_URL: redis://redis:6379/0  # For caching and background jobs
SECRET_KEY: # Required for API authentication
```

### Volume Management
- **Library Storage**: Read-only mount for manga files
- **Database Storage**: Persistent volume for PostgreSQL data
- **Cache Storage**: Temporary volume for thumbnails and processed files
- **Backup Storage**: External volume for database backups

## Monitoring and Observability

### Essential Metrics
- **Library Stats**: Series count, chapter count, total file size
- **Performance Metrics**: Response times, error rates, processing times
- **Usage Patterns**: Most read series, search queries, API usage
- **System Health**: Database connections, file system access, memory usage

### Logging Strategy
```python
# Structured logging with context
logger = structlog.get_logger(__name__)

async def process_chapter(chapter_id: str):
    log = logger.bind(
        operation="process_chapter",
        chapter_id=chapter_id
    )
    
    log.info("Processing started")
    try:
        result = await do_processing()
        log.info("Processing completed", duration=result.duration)
    except Exception as e:
        log.error("Processing failed", error=str(e))
```

### Health Checks
- **Database Connectivity**: Verify PostgreSQL connection and query performance
- **File System Access**: Confirm library paths are accessible
- **External APIs**: Check MangaDx API availability and response times
- **Background Jobs**: Monitor queue health and processing rates

This document should guide all development decisions and ensure consistency across the project's evolution from planning through production deployment.