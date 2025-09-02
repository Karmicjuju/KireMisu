# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)
```bash
cd frontend
pnpm install
pnpm dev
```

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests  
cd frontend
pnpm test
```

### Database Access
```bash
psql -h localhost -p 5432 -U kiremisu -d kiremisu
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

## Architecture

KireMisu is a self-hosted manga library management application with the following structure:

### Backend (FastAPI)
- **Framework**: FastAPI with PostgreSQL and SQLAlchemy ORM
- **Structure**: Clean architecture with separated layers:
  - `app/api/v1/endpoints/` - REST API endpoints
  - `app/core/` - Core configuration and utilities
  - `app/models/` - SQLAlchemy database models
  - `app/schemas/` - Pydantic request/response schemas
  - `app/services/` - Business logic layer
  - `app/repositories/` - Data access layer
  - `app/workers/` - Background job workers
  - `app/db/` - Database connection and migrations

### Frontend (Next.js)
- **Framework**: Next.js 15.5+ with TypeScript and Tailwind CSS
- **UI**: shadcn/ui + Radix UI components
- **State Management**: Zustand for client state
- **Features**: Built-in manga reader, library management, watch lists
- **File Support**: CBZ, CBR, ZIP, RAR, PDF, and folder formats

### Development Environment
- **DevContainer**: Full development environment with VS Code integration
- **Database**: PostgreSQL 15 with health checks
- **Package Management**: uv for Python, pnpm for Node.js
- **Code Quality**: Ruff for Python linting/formatting, ESLint/Prettier for TypeScript

## Development Workflow - PETRI Phases

Follow this 5-phase workflow for all development tasks:

### Phase 1: Plan (.claude/prompts/phase-1-plan.md)
Before coding, create a plan:
1. What files will be modified? (max 3)
2. What's the single responsibility?
3. What tests will prove it works?
4. What could be deferred to a future task?

### Phase 2: Execute (.claude/prompts/phase-2-execute.md)
Implement the planned changes:
- Follow existing patterns in the codebase
- Use descriptive variable names
- Add comments only for "why", not "what"
- Stop if scope creeps beyond plan

### Phase 3: Test (.claude/prompts/phase-3-test.md)
Write tests before moving forward:
- Unit tests for new functions
- Integration tests for API changes
- Update existing tests if behavior changed
- Run: tests

### Phase 4: Refactor (.claude/prompts/phase-4-refactor.md)
Review and refactor:
- Remove duplicate code
- Simplify complex conditionals
- Extract magic numbers to constants
- Ensure single responsibility

### Phase 5: Integrate (.claude/prompts/phase-5-integrate.md)
Complete the integration:
1. Run full test suite (not just new tests)
2. Verify no regressions
3. Write conventional commit message
4. Push to feature branch
5. Create PR if applicable
6. Document any breaking changes

# Project Workflow Rules

## Scope Limits
- Maximum 3 files per change
- Maximum 200 lines per commit
- One feature/fix per session

## Required Phases
1. PLAN: Define scope before coding
2. EXECUTE: Implement single responsibility
3. TEST: Write tests before considering complete
4. REFACTOR: Clean up before moving on
5. INTEGRATE: Commit with conventional commits

## Auto-Checks
- [ ] Does this change do ONE thing?
- [ ] Are tests written?
- [ ] Is the diff under 200 lines?
- [ ] Can I explain this change in one sentence?

## Essential Documentation

When working with this codebase, refer to these project-specific documents in `.claude/docs/`:

- **[Product Requirements](.claude/docs/kiremisu_prd.md)** - Complete product vision, features, and requirements
- **[Tech Stack](.claude/docs/kiremisu_tech_stack.md)** - Detailed technology choices and rationale
- **[Architecture Patterns](.claude/docs/kiremisu_architecture_patterns.md)** - Code organization and design patterns
- **[Development Standards](.claude/docs/kiremisu_development_standards.md)** - Coding conventions and best practices  
- **[Project Structure](.claude/docs/kiremisu_project_structure.md)** - File organization and directory layout
- **[Implementation Checklist](.claude/docs/kiremisu_implementation_checklist.md)** - Development workflow and tasks
- **[Quick Reference](.claude/docs/kiremisu_quick_reference.md)** - Common commands and shortcuts
- **[MCP Configuration](.claude/docs/MCP_CONFIGURATION.md)** - Model Context Protocol setup and troubleshooting

## Research Guidelines

When you need information about tools, frameworks, or implementation details:

1. **Use REF MCP first**: Always leverage the `mcp__Ref__ref_search_documentation` tool to search for official documentation and best practices
2. **Check project docs**: Reference the `.claude/docs/` files for project-specific decisions and patterns
3. **Follow established patterns**: Mimic existing code style, use project's chosen libraries, and follow architectural decisions documented in the project files

Example: When implementing authentication, first use REF MCP to research FastAPI security patterns, then check the project's auth implementation in the codebase.

## Key Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `MANGA_LIBRARY_PATH`: Path to manga collection
- `THUMBNAILS_PATH`: Path for generated thumbnails
- `PROCESSED_DATA_PATH`: Path for processed metadata
- `NEXT_PUBLIC_API_URL`: Backend API URL for frontend

## File System Structure
The application manages three main directories:
- `/manga`: Manga library storage (read-write for downloads)
- `/thumbnails`: Generated thumbnail cache
- `/processed`: Processed manga metadata

These paths are configured via environment variables and mounted as volumes in Docker.