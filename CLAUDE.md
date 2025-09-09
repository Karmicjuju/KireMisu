# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- Always delete old containers before deploying new ones when there is a port conflict on 3000, 8000, or 5432
- Always use uv instead of pip
- Always use and activate venv at root of the project
- Never hardcode sensitive data
- Always use pnpm over npm
- Always validate ui flows with Playwright mcp

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
## Essential Documentation
All implementations must align with `.claude/docs/kiremisu_prd.md` and follow the established architecture patterns.
When working with this codebase, refer to these project-specific documents in `.claude/docs/`:

- **[Product Requirements](.claude/docs/kiremisu_prd.md)** - Complete product vision, features, and requirements
- **[Tech Stack](.claude/docs/kiremisu_tech_stack.md)** - Detailed technology choices and rationale
- **[Architecture Patterns](.claude/docs/kiremisu_architecture_patterns.md)** - Code organization and design patterns
- **[Development Standards](.claude/docs/kiremisu_development_standards.md)** - Coding conventions and best practices  
- **[Project Structure](.claude/docs/kiremisu_project_structure.md)** - File organization and directory layout
- **[Implementation Checklist](.claude/docs/kiremisu_implementation_checklist.md)** - Development workflow and tasks
- **[Quick Reference](.claude/docs/kiremisu_quick_reference.md)** - Common commands and shortcuts
- **[MCP Configuration](.claude/docs/MCP_CONFIGURATION.md)** - Model Context Protocol setup and troubleshooting

## Required Phases
1. PLAN: Define scope before coding
2. EXECUTE: Implement single responsibility
3. TEST: Write tests before considering complete
4. REFACTOR: Clean up before moving on
5. INTEGRATE: Commit with conventional commits


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
- **Use fastapi-python-dev agent** for backend modifications to the fastapi codebase
- **Use the prd-feature-analyzer agent** for determining if the feature aligns with the prd