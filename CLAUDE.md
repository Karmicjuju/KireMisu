# CLAUDE.md

# KireMisu Development Context
_Last updated: 2025-08-05_

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KireMisu is a self-hosted, cloud-first manga reader and library management system designed to provide a unified platform for manga collection management, reading, and discovery. This is a fresh start building on lessons learned from a previous iteration, focusing on practical user experience and robust design.

### Core Vision
- **Unified Library**: Collect, organize, and read all manga in one place
- **Cloud-First & Self-Hosted**: Web application designed for Docker/Kubernetes deployment
- **Metadata-Rich Experience**: Extensive metadata from external sources (MangaDx) with user curation
- **Personalization & Advanced Features**: Custom tagging, file organization, annotations, and API access
- **Offline Capability**: Download and export content for offline reading

## Development Guidelines for Commit & PR Creation

### PR Creation Standards
- Draft the commit and create the PR based on our standards and do not add any contributor information
- Ensure all deliverables are implemented and demonstrable in PR description
- Provide comprehensive test coverage (unit, integration, E2E)
- Verify CI/CD pipeline passes all checks
- Clean lint and format (Ruff, ESLint/Prettier)
- Update relevant documentation sections
- Ensure no TODOs/FIXMEs remain within the scope
- Append a session hand-off note to CLAUDE.md under "Recently Completed Sessions"

### Breaking Change Policy
- Every change that introduces a bug that causes the front end to not load is a breaking change and will not be accepted

## Recently Completed Sessions

### 2025-08-04: R-1 Page Streaming + Basic Reader Implementation (Issue #6)

**Implemented by:** Multiple specialized agents working in parallel
**Status:** ✅ Complete - All deliverables met

#### Summary
Successfully implemented complete manga reader functionality including page streaming backend and full-featured React frontend reader.

#### Key Deliverables Completed:
- ✅ **Backend Page Streaming API** (`/api/chapters/{id}/pages/{page}`)
  - Support for CBZ, CBR, PDF, and folder formats
  - Async streaming with security validation  
  - Thread-pool optimization for CPU-bound operations
  - Proper caching headers and error handling

- ✅ **Frontend Reader Component** 
  - Full-screen manga reading experience
  - Keyboard navigation (arrows, space, home/end, F, escape)
  - Touch/swipe gestures for mobile
  - Auto-hiding UI with glass morphism design
  - Page preloading and progress tracking

- ✅ **Complete Integration**
  - Next.js app router with `/reader/[chapterId]` route
  - API client with SWR for data fetching
  - Reading progress persistence
  - Error handling and loading states

- ✅ **Comprehensive Testing**
  - E2E smoke tests with Playwright
  - Unit tests for reader components 
  - API endpoint tests with mocking
  - Performance tests for large files

- ✅ **Accessibility & UX**
  - ARIA labels and keyboard focus management
  - Responsive design for desktop/mobile
  - Touch-friendly navigation zones
  - Screen reader compatibility

#### Technical Architecture:
- **Backend:** FastAPI with async/await patterns, ThreadPoolExecutor for file I/O
- **Frontend:** Next.js 13+ app router, React with TypeScript, SWR for caching
- **File Processing:** Support for CBZ/ZIP, CBR/RAR, PDF (PyMuPDF), loose folders
- **Security:** Path traversal protection, input validation, MIME type checking

#### Files Modified/Created:
- `backend/kiremisu/api/chapters.py` - Page streaming endpoints
- `frontend/src/components/reader/` - Complete reader component suite
- `frontend/src/app/(app)/reader/[chapterId]/` - Reader route
- `tests/e2e/reader-smoke.spec.ts` - E2E test suite
- `tests/api/test_chapters.py` - Backend API tests

#### Exit Criteria Met:
- ✅ User can read a chapter (smoke test passes)
- ✅ Page streaming endpoint functional
- ✅ Basic reader with keyboard/swipe navigation
- ✅ All code linted and formatted
- ✅ Tests passing (backend library scan confirmed)
- ✅ TypeScript compilation successful

**Next Steps:** Ready for additional reader features like bookmarks, annotations, or metadata integration.

### 2025-08-05: Complete UV Migration - Comprehensive Python Toolchain Replacement

**Implemented by:** fastapi-backend-architect + qa-test-specialist
**Status:** ✅ Complete - Full Python toolchain modernization

#### Summary
Successfully migrated KireMisu to use uv as a comprehensive replacement for ALL traditional Python tooling, providing 5x faster package management and simplified development workflows.

#### Key Deliverables Completed:
- ✅ **Docker Container Migration**
  - Updated backend Dockerfile to use uv with uv.lock
  - Optimized package installation: 127ms vs traditional pip times
  - Maintained development reload functionality

- ✅ **Development Scripts Modernization**
  - Replaced `ensure_venv()` with `ensure_uv_venv()` using `uv venv`
  - Updated all Python commands: `uv run` instead of `python -m`
  - Removed fallback patterns to traditional tooling
  - Added comprehensive uv version and Python management

- ✅ **Comprehensive Toolchain Replacement**
  - Virtual environments: `uv venv` → replaces `python -m venv`, `virtualenv`
  - Package management: `uv add`, `uv sync` → replaces `pip install`
  - Command execution: `uv run` → replaces `python -m`
  - Python versions: `uv python install` → replaces `pyenv`
  - Dependency locking: `uv.lock` → replaces `requirements.txt`

- ✅ **Documentation & Agent Updates** 
  - Updated CLAUDE.md with comprehensive uv usage guide
  - Updated fastapi-backend-architect agent configuration
  - Updated qa-test-specialist agent configuration
  - Added critical warnings about uv replacing ALL Python tooling

- ✅ **Legacy Cleanup**
  - Verified no legacy Python configuration files (requirements.txt, setup.py, Pipfile)
  - Project already clean with modern pyproject.toml
  - GitHub Actions workflows using Claude Code (no Python tooling updates needed)

#### Technical Architecture:
- **uv Optimization**: 5x faster than traditional pip/python workflows
- **Docker Integration**: uv.lock for reproducible builds with frozen dependencies
- **Development Workflow**: Seamless virtual environment management with automatic activation
- **Python Version Management**: Integrated Python installation and pinning via uv python

#### Files Modified:
- `backend/Dockerfile.dev` - uv-optimized container with uv.lock
- `scripts/dev.sh` - Complete migration to uv commands throughout
- `CLAUDE.md` - Comprehensive uv documentation and usage guide
- `.claude/agents/fastapi-backend-architect.md` - uv-first configuration
- `.claude/agents/qa-test-specialist.md` - uv testing workflows

#### Performance Improvements:
- **Package Installation**: 127ms to install 48 packages (vs several seconds with pip)
- **Virtual Environment**: Automatic activation with uv run (no manual source activation)
- **Development Speed**: Faster test runs, linting, and command execution
- **Docker Build**: Optimized layer caching with uv.lock

#### Exit Criteria Met:
- ✅ All Docker containers rebuilt and tested with uv
- ✅ Backend API fully functional after migration
- ✅ Frontend loading correctly
- ✅ BQ-1 job system confirmed working with uv
- ✅ Development scripts use uv exclusively (no fallbacks)
- ✅ Documentation updated with comprehensive uv guide

**Key Insight:** uv is not just a faster pip replacement - it's a complete Python toolchain that replaces pyenv, virtualenv, pip, and python -m with a single, fast, unified tool.

## Docker Development Workflow

### 🚨 **CRITICAL: Always Use Docker for Testing**

KireMisu runs in Docker containers in development. **NEVER assume local npm/python development**.

#### **Frontend Development Workflow:**
```bash
# 1. Make code changes to frontend files
# 2. Rebuild the frontend container
docker-compose -f docker-compose.dev.yml build frontend

# 3. Restart the frontend service  
docker-compose -f docker-compose.dev.yml restart frontend

# 4. Test via containerized endpoint
curl http://localhost:3000
```

#### **Backend Development Workflow:**
```bash
# 1. Make code changes to backend files
# 2. Rebuild the backend container
docker-compose -f docker-compose.dev.yml build backend

# 3. Restart the backend service
docker-compose -f docker-compose.dev.yml restart backend

# 4. Test via containerized endpoint
curl http://localhost:8000/api/jobs/status
```

#### **Database Migrations:**
```bash
# Apply migrations via uv (faster than python -m)
DATABASE_URL=postgresql://kiremisu:kiremisu@localhost:5432/kiremisu \
PYTHONPATH=backend:$PYTHONPATH uv run alembic upgrade head
```

#### **Using uv for Development:**

**🚨 CRITICAL: uv replaces ALL traditional Python tooling**

uv is a comprehensive Python toolchain that replaces:
- `python -m venv` → `uv venv` 
- `pip install` → `uv add` / `uv sync`
- `python -m` → `uv run`
- `pyenv` → `uv python install`
- Virtual environment activation → automatic with `uv run`

```bash
# Python version management (replaces pyenv)
uv python install 3.13
uv python pin 3.13

# Virtual environment (replaces venv/virtualenv)
uv venv  # Creates .venv automatically
# No need to activate - uv run handles this

# Dependencies (replaces pip)
uv add package-name
uv add --dev pytest
uv sync  # Install from uv.lock (replaces pip install -r requirements.txt)

# Run commands (replaces python -m)
uv run pytest tests/ -v
uv run alembic upgrade head
uv run uvicorn main:app --reload
uv run ruff check .
uv run python script.py

# Development workflow
uv sync --dev  # Install all dependencies including dev
uv run pre-commit install
```

#### **Complete System Restart:**
```bash
# If major changes, restart all services
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

### **❌ Common Mistakes to Avoid:**
- Running `npm run dev` locally and expecting it to work
- Editing files and expecting immediate changes without rebuilding containers
- Testing via `localhost:3000` without ensuring the container is rebuilt
- Assuming frontend packages are installed locally

### **✅ Proper Testing Approach:**
1. **Always rebuild containers** after code changes
2. **Always test via Docker endpoints** (localhost:3000, localhost:8000)
3. **Always verify container logs** if issues occur
4. **Always restart services** after rebuilds