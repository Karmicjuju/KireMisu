# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Always delete old containers before deploying new ones when there is a port conflict on 3000, 8000, or 5432

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
- always clean up existing containers and redeploy if you make any changes, never use alternative ports. If you run into a port is already being used then you should assume you need to clean up old containers

## Iterative Feature Implementation Process

KireMisu follows a structured approach for implementing atomic features from `atomic-features-20250902.md`:

### Implementation Workflow

For each atomic feature, follow this process strictly:

1. **Plan & Context**: Use specialized sub-agents with current project state and specific feature details
2. **Implement**: Follow acceptance criteria exactly as defined in the atomic features document
3. **Security Review**: Use security-auditor agent to identify critical/high security issues
4. **Fix Security Issues**: Address all critical and high severity vulnerabilities before proceeding
5. **Deploy & Test**: 
   - Clean and prune old containers
   - Build and deploy updated containers
   - Run full test suite (must achieve >80% pass rate)
6. **Complete**: Update atomic-features-20250902.md with completion status and commit changes
7. **Next Iteration**: Move to next prioritized feature

### Quality Gates

A feature is only considered complete when:
- ✅ All acceptance criteria met
- ✅ No critical or high security vulnerabilities
- ✅ Old containers pruned and new ones deployed successfully  
- ✅ Test suite passes with >80% success rate
- ✅ Feature marked complete in atomic-features-20250902.md
- ✅ Changes committed to repository

### Agent Usage Strategy

- **Use specialized agents** for complex implementations to manage context better
- **Pass current state** of the atomic features document to each agent
- **Provide specific feature details** and acceptance criteria
- **Use REF MCP** for any documentation research needs
- **Use security-auditor agent** for mandatory security reviews after implementation

### Alignment

All implementations must align with `.claude/docs/kiremisu_prd.md` and follow the established architecture patterns.