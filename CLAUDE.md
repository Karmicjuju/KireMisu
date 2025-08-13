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
- **Security:** Path traversal protection, input validation, MIME type checking, JWT authentication, bcrypt password hashing


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

## Session 2025-08-13: System Initialization & Development Environment Setup

**Objective**: Fix shell environment issues, properly initialize backend system with database migrations and admin user, and establish working development workflow.

### Key Achievements

**1. Shell Environment Resolution**
- ✅ **Fixed zsh/zoxide configuration issue** preventing basic `cd` commands from working
- ✅ **Resolved tool environment compatibility** by removing problematic `cd` alias
- ✅ **Validated Docker workflow** - all containers running and responsive

**2. Backend System Initialization**
- ✅ **Updated startup script** (`backend/scripts/startup.sh`) with proper database initialization
- ✅ **Database migrations completed** - All 14 tables created (users, series, chapters, job_queue, etc.)
- ✅ **Admin user created** - Working authentication with JWT (`admin` / `KireMisu2025!`)
- ✅ **Library path configured** - `/manga-storage` mounted and accessible with test manga data

**3. Testing Framework Validation**
- ✅ **E2E testing operational** - Playwright successfully running against containerized app
- ✅ **API authentication working** - Backend endpoints secured and accessible
- ⚠️ **Unit testing issues identified** - Jest configuration needs JSX/MSW resolution
- ⚠️ **Code quality issues noted** - Multiple TypeScript and linting warnings exist

### Current System Status

**Infrastructure**: ✅ Fully Operational
- Frontend: localhost:3000 (Next.js)
- Backend: localhost:8000 (FastAPI with JWT auth)
- Database: PostgreSQL with all tables migrated
- Test Data: Manga files mounted (Naruto, Dragon Ball Z, One Piece, Test Series)

**Authentication**: ✅ Working
- Admin user: `admin` / `KireMisu2025!`
- JWT tokens functional
- Protected endpoints accessible

**Data**: 🔄 Partially Ready
- Database structure: ✅ Complete
- Library path: ✅ Configured
- Manga scanning: ⚠️ Attempted but found 0 series (requires investigation)

### Next Session Priorities

**Immediate Tasks**:
1. **Investigate manga scanning logic** - Files are mounted correctly but not being detected/imported
2. **Fix Jest configuration** - Resolve JSX parsing and MSW import issues for unit tests
3. **Debug missing helper functions** - E2E tests failing due to `clickNotificationBell` not found

**Development Workflow Ready**:
- Docker containers rebuilt and restarted successfully
- Database properly initialized with admin access
- Testing framework operational for development
- Code quality tools available (ESLint, TypeScript, Playwright)

**File Structure**:
- Test manga data: `/manga-storage/` (mounted in backend container)
- Backend startup: `backend/scripts/startup.sh` (enhanced with proper initialization)
- Testing framework: `frontend/tests/` (E2E working, unit tests need fixes)

## Security Requirements for Future Development

### 🚨 CRITICAL SECURITY STANDARDS

**Authentication & Authorization**:
- ❌ **NEVER** hardcode credentials, tokens, or secrets in code
- ✅ **ALWAYS** use environment variables for sensitive configuration
- ✅ **ALWAYS** require JWT authentication for user data endpoints
- ✅ **ALWAYS** use bcrypt for password hashing (cost factor 12+)
- ✅ **ALWAYS** implement rate limiting for authentication endpoints
- ✅ **ALWAYS** validate JWT tokens and handle expired/invalid tokens

**Input Validation & Sanitization**:
- ✅ **ALWAYS** validate and sanitize ALL user inputs
- ✅ **ALWAYS** use parameterized queries to prevent SQL injection
- ✅ **ALWAYS** sanitize HTML content to prevent XSS attacks
- ✅ **ALWAYS** validate URLs and enforce HTTPS (except localhost)
- ✅ **ALWAYS** implement input length limits and pattern validation
- ✅ **ALWAYS** escape special characters in user-generated content

**API Security**:
- ✅ **ALWAYS** require authentication for endpoints handling user data
- ✅ **ALWAYS** implement user-scoped data access (no cross-user access)
- ✅ **ALWAYS** validate API parameters and request bodies
- ✅ **ALWAYS** implement proper error handling without information leakage
- ✅ **ALWAYS** use HTTPS in production environments
- ✅ **ALWAYS** implement CORS policies appropriate for deployment

**File & Path Security**:
- ✅ **ALWAYS** validate file paths to prevent directory traversal
- ✅ **ALWAYS** validate MIME types for file uploads
- ✅ **ALWAYS** sanitize filenames and paths
- ✅ **ALWAYS** implement file size limits and type restrictions
- ✅ **ALWAYS** store uploaded files outside web root

**Configuration Security**:
- ❌ **NEVER** commit secrets, keys, or passwords to git
- ✅ **ALWAYS** use environment variables for configuration
- ✅ **ALWAYS** implement secure defaults for production
- ✅ **ALWAYS** validate environment variable presence and format
- ✅ **ALWAYS** use separate configurations for dev/staging/production

**Testing Security**:
- ✅ **ALWAYS** include security test coverage for new features
- ✅ **ALWAYS** test authentication and authorization paths
- ✅ **ALWAYS** test input validation with malicious inputs
- ✅ **ALWAYS** verify Docker environment functionality
- ✅ **ALWAYS** run security linting and static analysis

### Security Checklist for Pull Requests

Before submitting any PR, verify:
- [ ] No hardcoded credentials, secrets, or sensitive data
- [ ] All user data endpoints require authentication
- [ ] Comprehensive input validation implemented
- [ ] User-scoped authorization prevents cross-user access
- [ ] Security tests written and passing
- [ ] Docker build and deployment tested
- [ ] Environment variables used for all configuration
- [ ] Error messages don't leak sensitive information
- [ ] File operations validate paths and permissions
- [ ] HTTPS enforced in production configurations

### Security Incident Response
If security vulnerabilities are identified:
1. **Immediate**: Create private security issue (not public)
2. **Assessment**: Evaluate severity and impact
3. **Fix**: Implement comprehensive fix following these standards
4. **Test**: Verify fix with security test suite
5. **Deploy**: Deploy to all environments immediately
6. **Document**: Update security requirements if needed

# Documentation Standards for Future Development

**CRITICAL**: Prevent accumulation of temporary documentation files:

- ❌ **NEVER create session summary files** (`*_SUMMARY.md`, `*_IMPLEMENTATION_SUMMARY.md`, `*_TEST_COVERAGE*.md`)
- ❌ **NEVER create API contract documentation** (`*_API_CONTRACT.md`) 
- ❌ **NEVER create quick test files** (`QUICK_TEST.md`)
- ✅ **Implementation details belong in git commit messages**, not separate documentation files
- ✅ **Session notes should be archived to git history**, not accumulated in CLAUDE.md
- ✅ **Temporary documentation must follow .gitignore patterns** to prevent accidental commits
- ✅ **Only create documentation files when explicitly requested by the user**

The .gitignore has been updated to catch these patterns automatically.
