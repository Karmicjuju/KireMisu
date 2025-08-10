# CLAUDE.md

# KireMisu Development Context
_Last updated: 2025-08-10_

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

#### Technical Architecture:
- **Backend:** FastAPI with async/await patterns, ThreadPoolExecutor for file I/O
- **Frontend:** Next.js 13+ app router, React with TypeScript, SWR for caching
- **File Processing:** Support for CBZ/ZIP, CBR/RAR, PDF (PyMuPDF), loose folders
- **Security:** Path traversal protection, input validation, MIME type checking


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

# Recently Completed Sessions

## NT-1: Web Push Notifications System (2025-08-10)
**Status**: ✅ Complete - Ready for PR
**GitHub Issue**: #14 - NT-1: Web-push notifications

### Implementation Summary
Successfully implemented a comprehensive web push notifications system that integrates with the existing W-1 watching system:

**Backend Components**:
- Push subscription management API (`/api/push/*`)  
- VAPID key configuration and handling
- Push notification sending infrastructure with WebPush protocol
- Database model and migration for push subscriptions
- Integration with existing notification service for automatic chapter alerts
- Manual push test script for development/debugging

**Frontend Components**:
- Service worker for handling push notifications (`/public/service-worker.js`)
- React hook for push notification management (`use-push-notifications.ts`)
- User opt-in UI component with browser compatibility detection
- Integration with existing notification dropdown
- PWA manifest for app-like experience

**Key Features**:
- Browser support detection with graceful degradation
- Test notification functionality for user verification  
- Automatic new chapter push notifications
- Subscription management (subscribe/unsubscribe)
- Error handling for expired subscriptions
- Background sync for offline notification queuing

**Testing & Quality**:
- Comprehensive unit tests for API endpoints
- Integration tests with notification system
- Frontend E2E tests for user workflows
- Database tests for subscription model
- Code formatting and linting completed

**Configuration Required**:
Users must set VAPID keys in environment:
```
VAPID_PUBLIC_KEY=<generated_public_key>
VAPID_PRIVATE_KEY=<generated_private_key>
VAPID_CLAIMS={"sub": "mailto:admin@kiremisu.local"}
```

**Next Steps**: Create PR, test in production environment, add PWA icons
