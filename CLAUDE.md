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

## Architecture Overview
### Refence documentation
- File found in docs/kiremisu_tech_stack.md

### Tech Stack (Planned)
- **Backend**: FastAPI + Python 3.13+ with async performance
- **Database**: PostgreSQL 16+ + JSONB for flexible metadata and ACID compliance
- **Frontend**: Next.js 22+ + TypeScript with SSR performance
- **UI Framework**: Tailwind CSS + shadcn/ui components
- **State Management**: Zustand for optimal reading app performance
- **File Processing**: PIL + PyMuPDF + rarfile for comprehensive manga format support
- **Background Jobs**: PostgreSQL-based queue (eliminating Redis dependency)
- **Deployment**: Docker + Kubernetes for self-hosted flexibility

### System Architecture
- **Self-Hosted Web Application**: Accessed via browser, avoiding Electron bloat
- **File-Based Storage**: User-designated storage locations as source of truth
- **External API Integration**: Mangadex for metadata enrichment and content discovery
API SPec for Mangadex is at https://api.mangadex.org/docs/swagger.html
- **Flexible Metadata Schema**: JSONB fields enable schema evolution without migrations
- **Background Processing**: Async file processing with thread pool isolation

## §3. Database Schema

### Core Tables

#### Series Table
The `series` table stores manga series metadata and configuration:
- **Primary Key**: UUID for distributed system compatibility
- **Essential Indexes**:
  - `ix_series_title_primary`: Fast title searches
  - `ix_series_author`: Author-based filtering
  - `ix_series_artist`: Artist-based filtering  
  - `ix_series_publication_status`: Status filtering (ongoing, completed, etc.)
- **Key Fields**:
  - `mangadx_id`: External identifier with unique constraint
  - `source_metadata`/`user_metadata`: JSONB for flexible schema evolution
  - `watching_*`: Configuration for automated chapter checking
  - Statistics fields for reading progress tracking

#### Chapters Table
The `chapters` table stores individual chapter information:
- **Primary Key**: UUID with foreign key to series
- **Essential Indexes**:
  - `ix_chapters_series_id`: Fast series-based queries
  - `ix_chapters_series_chapter_volume`: Compound index for unique chapter identification
  - `ix_chapters_series_ordering`: Optimized for chapter ordering within series
- **Key Fields**:
  - `chapter_number`: Float to support fractional chapters (1.5, etc.)
  - `file_path`: Source file location (app doesn't move files)
  - Reading progress tracking fields

#### Supporting Tables
- **Annotations**: Per-chapter user notes with page-level precision
- **Library Paths**: Configured storage locations for scanning
- **Job Queue**: PostgreSQL-based background task management
- **User Lists**: Custom collections and reading lists

### Database Design Decisions

#### Synchronous Migrations
**Decision**: Use synchronous database operations for Alembic migrations while keeping the main application async.
**Rationale**: 
- Avoids complex dependencies like `greenlet` for self-hosted deployments
- Simplifies build process and reduces image size
- Improves reliability across different architectures (ARM/x86)
- Migration operations are inherently sequential and don't benefit from async

**Implementation**: 
- Main app uses `asyncpg` for async PostgreSQL operations
- Migrations use `psycopg2-binary` for reliable, synchronous operations
- Database URL automatically converted from async to sync format in Alembic env

#### JSONB for Metadata
- Enables schema evolution without migrations
- Supports rich metadata from external sources (MangaDx)
- Allows user customization and annotation storage
- Indexed queries on JSON fields when needed

#### UUID Primary Keys
- Enables distributed system patterns if needed
- Avoids integer key conflicts during imports
- Better for API exposure and security

## Core Features

### Media Management
- Local/network storage integration with configurable library paths
- Manual and scheduled library synchronization
- Multi-format support (.cbz, .cbr, folders, PDFs)
- Safe storage management (app acts as index, doesn't move files by default)

### Metadata Management
- Automated metadata enrichment from MangaDx API
- User-editable metadata fields with override capabilities
- Custom tags and annotations system
- Cover art management with thumbnail caching
- Bulk metadata operations for library maintenance

### Advanced Organization
- Custom naming schemes using metadata variables
- Bulk renaming tool with dry-run preview and safety checks
- File organization and restructuring capabilities
- Integration with metadata for dynamic naming

### User Collections & Discovery
- User-created reading lists and collections
- Advanced filtering by metadata, tags, genres, status
- Search functionality across local library
- Multiple view modes (grid/list) with sorting options

### MangaDex Integration & Watching
- Search and add series from MangaDex database
- Watching system for tracking new releases with configurable polling
- Intelligent scheduling and rate limiting for API calls
- Reading progress sync between KireMisu and MangaDx accounts
- Batch download capabilities for new chapters

### Reading Experience
- Chapter annotation and note-taking system
- Per-chapter notes with context in reading interface
- Annotation management and export capabilities
- Rich reading interface with multiple view modes

### API & Automation
- RESTful API for all core functionalities
- Secure authentication with API key management
- Automation support for external scripts and integrations
- Rate limiting and performance considerations

## Development Guidelines

### Current State
This repository currently contains:
- **Documentation**: Comprehensive PRD and tech stack specifications
- **UI Mockup**: React component demonstrating the planned interface design
- **No Implementation Yet**: This is a planning/design phase repository

### When Implementation Begins

#### Python Backend Development
- Use FastAPI with async patterns for I/O operations
- Implement CPU-bound file processing with ThreadPoolExecutor
- Follow the PostgreSQL + JSONB schema patterns from tech stack docs
- Use structured logging with contextual information for operations
- Implement proper error handling and graceful degradation

#### Frontend Development
- Use Next.js App Router with Server/Client component patterns
- Implement Zustand stores for reading state management
- Follow the component patterns shown in the UI mockup
- Ensure responsive design principles for self-hosted access

#### File Processing
- Implement unified interfaces for different manga formats
- Use the abstraction patterns shown in tech stack for easy migration to Rust
- Handle large file operations with background processing
- Implement proper error handling for corrupted or missing files

#### API Integration
- Respect MangaDex API rate limits with intelligent caching
- Implement exponential backoff for failed requests
- Cache metadata and search results appropriately
- Design watching system with configurable polling intervals

### Deployment & Infrastructure
- Design for containerized deployment from the start
- Use environment variables for all configuration
- Support both simple Docker Compose and Kubernetes deployments
- Externalize all persistent data to volumes/databases

### Testing Strategy
- Unit tests for core logic (metadata parsing, file processing, API endpoints)
- Integration tests for workflows (adding series, syncing metadata, watching)
- Use mock data for external API dependencies
- Test file processing with various manga formats

## Key Design Principles

1. **Self-Hosted First**: All features must work in isolated, self-hosted environments
2. **File System as Source of Truth**: Never modify user files without explicit permission
3. **Graceful Degradation**: Core features work even if external APIs are unavailable
4. **Performance for Large Libraries**: Design for thousands of series and chapters
5. **User Control**: Extensive customization without complexity for casual users
6. **Future Migration Path**: Architecture supports evolution from Python to Rust for performance-critical components

## Feature Roadmap

| Chunk ID                                      | Entry prerequisite      | Deliverables (all must meet DoD)                                                                                                                                            | Exit / Next                            |
| --------------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **LL-1**<br>*Create Series & Chapter schema*  | Phase 0 complete        | • Migration defining Series + Chapter + essential indexes<br>• SQL-level docs added in CLAUDE.md §3<br>• Green migration test in CI                                         | Database ready for importing files     |
| **LL-2**<br>*Library-path CRUD*               | LL-1                    | • DB structures for paths + scan interval<br>• API endpoints (list, create, update, delete)<br>• Settings UI with directory picker & interval dropdown<br>• Unit + UI tests | User can store a path in the app       |
| **LL-3**<br>*Filesystem parser utility*       | LL-2                    | • Pure-Python parser that returns structured series/chapter info<br>• Fixture test covering CBZ & folder input<br>• Docs link added to CLAUDE.md §1                         | Parser usable by importer              |
| **LL-4**<br>*Importer & manual scan endpoint* | LL-3                    | • Importer writes/updates rows idempotently<br>• POST `/library/scan` enqueues/imports scan<br>• Settings “Scan Now” button + toast<br>• Tests validating counts returned   | Real series appear in Library grid     |
| **LL-5**<br>*Automatic path scan via jobs*    | LL-4, BQ-1              | • Scan jobs scheduled per path interval<br>• UI shows last-run time<br>• CI integration test: job runs in worker                                                            | Library stays up-to-date automatically |
| **R-1**<br>*Page streaming + basic reader*    | LL-4                    | • Endpoint streams page images<br>• Simple reader component (keys/swipe)<br>• Smoke test opens first page                                                                   | User can read a chapter                |
| **R-2**<br>*Mark-read & progress bars*        | R-1                     | • API toggles read state; triggers aggregate update<br>• Progress bar & dashboard stats update in UI<br>• Unit + E2E tests                                                  | Reading progress visible               |
| **TL-1**<br>*Tagging system*                  | LL-4                    | • Tag + junction schema<br>• Tag CRUD endpoints<br>• Chip editor in series detail<br>• Filtered Library view                                                                | User organizes series via tags         |
| **MD-1**<br>*Search & import metadata*        | LL-4                    | • MangaDex search proxy endpoint<br>• Search modal lists results<br>• Import API creates series<br>• Success toast<br>• Tests hitting mocked MD API                         | External series can be added           |
| **MD-2**<br>*Download jobs + downloads UI*    | MD-1, BQ-1              | • Download job schema + enqueuer<br>• Worker downloads sample chapter<br>• Downloads page shows progress<br>• Happy-path tests                                              | User sees download progress            |
| **W-1**<br>*Watching & notification skeleton* | MD-1                    | • Watch flag stored per series<br>• Check-for-updates job enqueued<br>• Notification API returns “new chapters”<br>• Header bell shows badge                                | User alerted to new chapters           |
| **AN-1**<br>*Page annotations*                | R-1                     | • Annotation schema + endpoints<br>• Reader drawer to view/add notes<br>• Basic unit test                                                                                   | User can annotate pages                |
| **FM-1**<br>*Safe rename/delete*              | LL-4                    | • Backend endpoints for rename/delete with validations<br>• Confirm dialog in UI<br>• Test: rename idempotent<br>• Docs update about file safety                            | User can manage files safely           |
| **NT-1**<br>*Web-push notifications*          | W-1                     | • Service worker + push subscription endpoint<br>• Push message sent for new chapter event<br>• User opt-in UI flow<br>• Manual push test script                            | Push notifications operational         |
| **D-1**<br>*Production release package*       | All feature chunks done | • Slim prod images published<br>• Compose & Helm manifests committed<br>• Install docs + CHANGELOG<br>• Release tag created                                                 | App is shippable to end users          |

Every chunk above must satisfy:

All deliverables implemented and demonstrable in PR description.

Tests (unit ± integration ± E2E) added or updated; CI green.

Lint/format clean (Ruff, ESLint/Prettier).

Docs:

Relevant section of CLAUDE.md updated (architecture, data model, “Completed Features”, etc.).

Public API changes surfaced in autogenerated OpenAPI.

Accessibility & usability: interactive UI elements keyboard-navigable and labelled.

No TODO/FIXME left within the scope.

Session hand-off note appended to CLAUDE.md under “Recently Completed Sessions”.

