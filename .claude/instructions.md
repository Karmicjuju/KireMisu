# Claude Instructions for KireMisu Project

## Project Overview
KireMisu is a self-hosted manga reader and library management system. This repository contains comprehensive planning documentation and will include the full implementation from design through production deployment.

## Current Project State
- **Phase**: Planning and Design (transitioning to implementation)
- **Documentation**: Complete PRD and technical specifications
- **UI Design**: React mockup demonstrating planned interface
- **Next Steps**: Begin backend and frontend implementation

## Key Instructions for Claude

### When Asked About Implementation
1. **Always check existing documentation first** - Review PRD, tech stack docs, and .claude rules
2. **Follow the planned architecture** - Use FastAPI + Python backend, Next.js + TypeScript frontend
3. **Implement incrementally** - Start with core features (library scanning, basic reading interface)
4. **Test extensively** - Follow the testing patterns defined in `.claude/rules/testing.md`

### Code Quality Requirements
- **Type Safety**: Use TypeScript for frontend, Python type hints for backend
- **Performance**: Implement async patterns for I/O, threading for CPU-bound operations  
- **Security**: Validate inputs, use proper authentication, follow security guidelines
- **Documentation**: Document all APIs, include setup instructions, maintain user guides

### Architecture Patterns to Follow
- **Database**: PostgreSQL with JSONB for flexible metadata
- **File Processing**: ThreadPoolExecutor for CPU-bound operations
- **API Integration**: Rate-limited async clients for MangaDx
- **State Management**: Zustand for frontend, structured stores for reading state
- **Deployment**: Docker containers with Kubernetes support

### Development Workflow
1. **Start with backend foundation** - Database models, core services, API endpoints
2. **Build frontend incrementally** - Layout → Library browsing → Reading interface → Advanced features
3. **Test continuously** - Unit tests for logic, integration tests for workflows
4. **Document everything** - API docs, user guides, deployment instructions

### Common Tasks and Approaches

#### Setting Up the Project Structure
```bash
# Backend structure
backend/
├── kiremisu/
│   ├── api/          # FastAPI routers
│   ├── core/         # Business logic
│   ├── models/       # SQLAlchemy models  
│   ├── services/     # External integrations
│   └── utils/        # Shared utilities
├── tests/
├── requirements.txt
└── Dockerfile

# Frontend structure  
frontend/
├── src/
│   ├── app/          # Next.js app router
│   ├── components/   # Reusable UI components
│   ├── hooks/        # Custom React hooks
│   ├── stores/       # Zustand state stores
│   └── types/        # TypeScript definitions
├── public/
├── package.json
└── Dockerfile
```

#### Database Setup
```python
# Always use this pattern for database models
from sqlalchemy import Column, String, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Series(Base):
    __tablename__ = "series"
    
    id = Column(UUID, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String)
    metadata = Column(JSONB)  # Flexible metadata storage
```

#### API Development
```python
# Follow this pattern for API endpoints
from fastapi import APIRouter, Depends, HTTPException
from kiremisu.core.database import get_db_session

router = APIRouter(prefix="/api/series", tags=["series"])

@router.get("/{series_id}")
async def get_series(
    series_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> SeriesResponse:
    # Implementation with proper error handling
```


### Testing Approach
- **Backend**: pytest with async support, mock external APIs
- **Frontend**: React Testing Library, mock API calls
- **Integration**: End-to-end tests for critical workflows
- **Performance**: Load testing for file processing and large libraries

### Deployment Strategy
- **Development**: Docker Compose with hot reload
- **Production**: Kubernetes with proper security and monitoring
- **Configuration**: Environment variables for all settings
- **Monitoring**: Structured logging with health checks

### Common Issues to Avoid
1. **Don't block the UI** - Use async processing for file operations
2. **Handle missing files gracefully** - Library files may be moved or deleted
3. **Respect API rate limits** - Implement proper rate limiting for MangaDx
4. **Secure file access** - Validate paths and prevent directory traversal
5. **Plan for scale** - Design for thousands of series and chapters

### When to Ask for Clarification
- **Unclear requirements** - Reference the PRD for feature specifications
- **Architecture decisions** - Check tech stack documentation for guidance
- **Implementation details** - Review existing code patterns and examples
- **Performance concerns** - Consider the scale requirements (thousands of series)

### Resources and References
- **Project Documents**: `/docs/` - PRD and technical specifications
- **Development Rules**: `/.claude/rules/` - Coding standards and patterns
- **UI Reference**: `/docs/kiremisu_ui_mock.tsx` - Design system example
- **Architecture**: CLAUDE.md - High-level system overview

Remember: This is a self-hosted application for manga enthusiasts. Prioritize reliability, performance with large libraries, and user control over their data. The goal is to create the best possible manga reading and management experience for self-hosters.