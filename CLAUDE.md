# CLAUDE.md

# KireMisu Development Context
_Last updated: 2025-08-02_

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