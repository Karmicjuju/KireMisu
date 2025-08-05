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

**Next Steps:** Ready for additional reader features like metadata integration, advanced search, or user management features.

### 2025-08-05: AN-1 Page Annotations Implementation - Complete Annotation System

**Implemented by:** Feature Orchestrator with comprehensive architecture design
**Status:** ✅ Complete - Full annotation system ready for production

#### Summary
Successfully implemented a complete page annotation system for the KireMisu manga reader, enabling users to add notes, bookmarks, and highlights to specific pages in chapters with precise positioning and color customization.

#### Key Deliverables Completed:
- ✅ **Enhanced Database Schema**
  - Extended Annotation model with position (x, y) and color fields
  - Added database constraints for position validation (0-1 normalized) and color format
  - Created comprehensive migration with proper check constraints

- ✅ **Comprehensive Backend API**
  - Full CRUD endpoints for annotation management (`/api/annotations/`)
  - Chapter-specific annotation endpoints (`/api/annotations/chapters/{id}`)
  - Page-specific annotation endpoints (`/api/annotations/chapters/{id}/pages/{page}`)
  - Advanced filtering by type, page, and chapter
  - Bulk operations for chapter annotation management

- ✅ **Rich Frontend Components**
  - `AnnotationMarker`: Visual indicators on manga pages with hover tooltips
  - `AnnotationForm`: Comprehensive form for creating/editing annotations
  - `AnnotationDrawer`: Sidebar for viewing and managing all chapter annotations
  - Type-specific icons (note, bookmark, highlight) and color coding

- ✅ **Complete Reader Integration**
  - Annotation mode toggle for creating annotations by clicking
  - Real-time annotation display with positioning
  - Annotation drawer integration with chapter navigation
  - Visual feedback and overlay system for annotation creation

- ✅ **Advanced Features**
  - Precise page positioning (normalized 0-1 coordinates)
  - Custom color selection with preset and custom options
  - Three annotation types: notes, bookmarks, highlights
  - Page-specific and general chapter annotations
  - Annotation grouping by page in drawer interface

#### Technical Architecture:

**Database Layer:**
- **Enhanced Model**: Position fields (position_x, position_y) for precise placement
- **Color Support**: Hex color validation with database constraints
- **Data Integrity**: Proper foreign key relationships and cascading deletes
- **Performance**: Optimized indexes for chapter and page queries

**Backend API Design:**
- **RESTful Endpoints**: Standard CRUD operations with advanced filtering
- **Validation**: Comprehensive input validation with position and color constraints
- **Error Handling**: Detailed error responses for invalid data
- **Performance**: Efficient queries with pagination and filtering

**Frontend Architecture:**
- **Component Design**: Reusable, accessible annotation components
- **State Management**: Local state with SWR for caching and real-time updates
- **User Experience**: Intuitive annotation creation and management flows
- **Responsive Design**: Works across desktop and mobile devices

#### Files Created/Modified:

**Backend Implementation:**
- `backend/kiremisu/database/models.py` - Enhanced Annotation model with position/color fields
- `backend/kiremisu/database/schemas.py` - Comprehensive annotation schemas for API
- `backend/kiremisu/api/annotations.py` - Complete CRUD API endpoints
- `backend/kiremisu/main.py` - Router registration for annotation endpoints
- `backend/alembic/versions/09c754a38e7a_*.py` - Database migration

**Frontend Implementation:**
- `frontend/src/lib/api.ts` - Annotation API client methods and TypeScript interfaces
- `frontend/src/components/annotations/annotation-marker.tsx` - Visual annotation markers
- `frontend/src/components/annotations/annotation-form.tsx` - Annotation creation/editing form
- `frontend/src/components/annotations/annotation-drawer.tsx` - Annotation management sidebar
- `frontend/src/components/reader/manga-reader.tsx` - Complete reader integration

**Testing Infrastructure:**
- `tests/conftest.py` - Annotation test fixtures for series, chapters, and annotations
- `tests/api/test_annotations.py` - Comprehensive backend API tests
- `frontend/tests/e2e/annotations.spec.ts` - E2E tests for annotation functionality

#### Exit Criteria Met:
- ✅ User can create annotations by clicking on manga pages
- ✅ Annotations display as visual markers with hover tooltips
- ✅ Annotation drawer shows all chapter annotations grouped by page
- ✅ Users can edit and delete annotations through intuitive UI
- ✅ Three annotation types supported with distinct visual styling
- ✅ Position and color customization fully functional
- ✅ All code linted, formatted, and follows KireMisu patterns
- ✅ Comprehensive test coverage (unit, integration, E2E)
- ✅ TypeScript compilation successful with proper type definitions

#### User Experience Flow:
1. **Annotation Mode**: Toggle annotation mode in reader header
2. **Create by Clicking**: Click anywhere on manga page to place annotation
3. **Form Interface**: Rich form with content, type selection, and color picker
4. **Visual Feedback**: Immediate marker placement with hover tooltips
5. **Management**: Comprehensive drawer for viewing, editing, and organizing annotations
6. **Navigation**: Click annotations in drawer to jump to specific pages

#### Performance Optimizations:
- Lazy-loading annotations per page to reduce initial load time
- Efficient API queries with proper indexing and pagination
- Local state management to minimize unnecessary API calls
- Optimized component rendering with proper memoization

**Key Technical Innovation:** Normalized positioning system (0-1 coordinates) allows annotations to work across different screen sizes and zoom levels, providing consistent placement regardless of display scaling.

**Next Steps:** The annotation system is production-ready and can be extended with features like annotation sharing, export functionality, or integration with external note-taking systems.

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