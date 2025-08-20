# KireMisu Development Context
_Last updated: 2025-08-16_

## Current Sprint Focus
- ✅ Completed: Core data model design and tech stack selection
- 🔄 Active: Backend API development with FastAPI + PostgreSQL
- 📋 Next: Frontend reader component implementation
- 📋 Planned: MangaDx integration and watching system

## Architecture Quick Reference
- **Backend**: FastAPI + Python 3.13 + PostgreSQL + uv toolchain
- **Frontend**: Next.js 15.4 + React 19 + TypeScript + Tailwind + shadcn/ui
- **Database**: PostgreSQL + JSONB for flexible metadata
- **Deployment**: Docker (dev) → Kubernetes (prod)
- **File Processing**: PIL + PyMuPDF + rarfile for manga formats

## Critical Development Rules
⚠️ **NEVER** develop locally - Always use Docker containers  
⚠️ **ALWAYS** use uv instead of pip/python -m/venv/pyenv  
⚠️ **ALWAYS** write tests for new features (see `/docs/TESTING.md`)  
⚠️ **ALWAYS** run security checklist before commits (see `/docs/SECURITY.md`)  
⚠️ **BREAKING CHANGES** forbidden - Frontend must always load  

## Docker Development Workflow
```bash
# Frontend changes
docker-compose -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.dev.yml restart frontend
curl http://localhost:3000  # Test

# Backend changes  
docker-compose -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.dev.yml restart backend
curl http://localhost:8000/api/jobs/status  # Test

# Database migrations
DATABASE_URL=postgresql://kiremisu:kiremisu@localhost:5432/kiremisu \
PYTHONPATH=backend:$PYTHONPATH uv run alembic upgrade head

# Complete restart (for major changes)
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

## uv Python Toolchain (Replaces Everything)
```bash
# Python version management (replaces pyenv)
uv python install 3.13
uv python pin 3.13

# Virtual environment (replaces venv/virtualenv)
uv venv  # Creates .venv automatically

# Dependencies (replaces pip)
uv add package-name
uv add --dev pytest
uv sync  # Install from uv.lock

# Run commands (replaces python -m)
uv run pytest tests/ -v
uv run alembic upgrade head
uv run uvicorn main:app --reload
uv run ruff check .
```

## Testing Quick Commands
```bash
# All tests
./scripts/test-all.sh

# Backend development
cd backend && uv run pytest tests/api/ -v --cov

# Frontend development  
cd frontend && npm run test:watch  # TDD mode
cd frontend && npm run test:e2e:ui  # Visual debugging
```

## Key Architecture Decisions
- ✅ **PostgreSQL + JSONB**: ACID compliance + flexible metadata schemas
- ✅ **FastAPI ThreadPoolExecutor**: Async API with CPU-bound file processing isolation
- ✅ **Watching System**: Embedded config in series table for performance
- ✅ **Next.js App Router**: SSR for large library performance
- ✅ **Zustand State**: Minimal overhead for high-frequency reader updates

## Files to Include for Specific Tasks

### API Development
- `kiremisu_data_model.md` (database schemas)
- `/docs/API_PATTERNS.md` (FastAPI + async patterns)
- `/docs/SECURITY.md` (authentication & validation)
- `/docs/TESTING.md` (API testing patterns)

### UI Development  
- `/docs/UI_SYSTEM.md` (design system & components)
- `/docs/TESTING.md` (React testing patterns)
- `/docs/examples/ui-mock.tsx` (reference implementation)

### Database Changes
- `kiremisu_data_model.md` (comprehensive schema)
- `/docs/MIGRATIONS.md` (Alembic patterns)
- `/docs/TESTING.md` (database testing)

### Deployment & Infrastructure
- `/docs/DEPLOYMENT.md` (Docker + Kubernetes)
- `/docs/MONITORING.md` (observability setup)
- `kiremisu_tech_stack.md` (deployment architecture)

### Integration Work
- `kiremisu_prd.md` (MangaDx watching system requirements)
- `/docs/API_PATTERNS.md` (external API integration)
- `/docs/TESTING.md` (integration test patterns)

## Recent Implementation Sessions
See git commit history for detailed session notes. Key recent work:
- Data model finalization with watching system integration
- Docker development workflow establishment  
- Security requirements documentation
- Testing strategy establishment

## Documentation Maintenance
- Keep this file under 50 lines of essential information
- Move detailed patterns to specialized docs
- Update Current Sprint Focus weekly
- Archive session details to git commits only
