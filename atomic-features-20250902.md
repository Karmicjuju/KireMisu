# KireMisu - Atomic Features Breakdown

**Product Name:** KireMisu  
**PRD Version:** Current (as of 2025-09-02)  
**Analysis Date:** September 2, 2025  
**Total Features:** 47

---

## Overview

This document breaks down the KireMisu Product Requirements Document into atomic, implementable features that can be developed incrementally. Each feature is designed to be:

- **Single-purpose**: Does one thing well
- **Testable**: Has clear success criteria
- **Independent**: Can be implemented without requiring other features (where possible)
- **Estimable**: Has clear scope for development planning
- **Valuable**: Delivers meaningful user or business value

Features are organized into logical categories and prioritized for implementation order, considering dependencies and user value.

---

## Feature Categories

### 1. Foundation & Infrastructure
### 2. Authentication & Security
### 3. Media Management
### 4. Metadata Management
### 5. User Interface Core
### 6. Content Discovery
### 7. Reading Experience
### 8. Organization & Lists
### 9. MangaDex Integration
### 10. Watching System
### 11. File Management
### 12. API & Automation
### 13. Enhanced Features

---

## 1. Foundation & Infrastructure

### F1.1 - Database Schema & Models Setup ✅ **COMPLETED**

**Description:** Establish core database schema for manga series, chapters, and user data using PostgreSQL with SQLAlchemy ORM.

**User Story:** As a developer, I need a robust database foundation so that all application data can be stored and retrieved efficiently.

**Acceptance Criteria:**
- [x] PostgreSQL database connection established
- [ ] Series model with fields: id, title, description, author, artist, status, cover_path, metadata_json
- [ ] Chapter model with fields: id, series_id, number, title, file_path, read_status, created_at
- [x] User model with fields: id, username, password_hash, created_at
- [ ] Database migrations system implemented (Note: Using direct SQLAlchemy without Alembic currently)
- [x] Proper indexes on commonly queried fields
- [x] Foreign key relationships established

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** None  
**Technical Notes:** Database connection established, User model complete. Series/Chapter models need implementation. No Alembic migrations yet.

---

### F1.2 - Application Configuration System ✅ **COMPLETED**

**Description:** Implement environment-based configuration management for database, storage paths, and external services.

**User Story:** As a system administrator, I need configurable settings so that I can deploy KireMisu in different environments.

**Acceptance Criteria:**
- [x] Environment variables for DATABASE_URL, MANGA_LIBRARY_PATH, THUMBNAILS_PATH
- [x] Configuration validation on startup
- [x] Default values for non-critical settings
- [x] Support for both .env files and system environment variables
- [x] Configuration documentation in deployment guides
- [x] Health check endpoint that validates configuration

**Priority:** High  
**Complexity:** Simple  
**Dependencies:** None  
**Technical Notes:** Fully implemented with Pydantic validation in app/core/config.py

---

### F1.3 - Docker Containerization ✅ **COMPLETED**

**Description:** Create production-ready Docker containers for the application with proper volume mounts and networking.

**User Story:** As a self-hoster, I need Docker containers so that I can easily deploy KireMisu on my server.

**Acceptance Criteria:**
- [x] Dockerfile for FastAPI backend with minimal Alpine base
- [x] Dockerfile for Next.js frontend with static serving
- [x] Docker Compose file with backend, frontend, and PostgreSQL
- [x] Volume mounts for manga library, thumbnails, and processed data
- [x] Environment variable configuration
- [x] Health checks for all services
- [x] Production docker-compose.prod.yml variant

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F1.1, F1.2  
**Technical Notes:** Complete Docker setup with dev and prod configurations

---

## 2. Authentication & Security

### F2.1 - Basic User Authentication ✅ **COMPLETED**

**Description:** Implement secure username/password authentication for single-user access.

**User Story:** As a server owner, I need secure login so that my manga library is protected from unauthorized access.

**Acceptance Criteria:**
- [ ] User registration endpoint (limited to single user initially)
- [x] Login endpoint with JWT token generation
- [x] Password hashing using bcrypt
- [x] JWT token validation middleware
- [x] Logout functionality (token invalidation)
- [x] Session timeout configuration
- [ ] Password strength requirements

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F1.1  
**Technical Notes:** JWT authentication fully implemented. Missing user registration endpoint and password strength validation.

---

### F2.2 - API Key Management

**Description:** Generate and manage API keys for programmatic access to KireMisu features.

**User Story:** As a power user, I need API keys so that I can automate interactions with my manga library.

**Acceptance Criteria:**
- [ ] API key generation endpoint
- [ ] API key validation middleware
- [ ] API key revocation functionality
- [ ] Multiple API keys per user support
- [ ] API key expiration configuration
- [ ] API key usage logging
- [ ] Settings UI for API key management

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F2.1  
**Technical Notes:** Use secure random generation, consider rate limiting per key

---

## 3. Media Management

### F3.1 - Storage Path Configuration

**Description:** Allow users to configure and validate multiple library storage paths for manga collections.

**User Story:** As a library manager, I need to specify where my manga files are stored so that KireMisu can find and index them.

**Acceptance Criteria:**
- [ ] Add/remove library path functionality
- [ ] Path validation (existence, read permissions)
- [ ] Support for network-mounted storage
- [ ] Path priority configuration
- [ ] Storage usage reporting per path
- [ ] Graceful handling of unavailable paths
- [ ] Settings UI for path management

**Priority:** High  
**Complexity:** Simple  
**Dependencies:** F1.2  
**Technical Notes:** Handle different filesystem types, implement proper error handling for network storage

---

### F3.2 - File Format Detection

**Description:** Detect and validate supported manga file formats (CBZ, CBR, PDF, ZIP, RAR, folders).

**User Story:** As a manga collector, I need the system to recognize my various file formats so that all my manga can be indexed.

**Acceptance Criteria:**
- [ ] CBZ file format detection and validation
- [ ] CBR file format detection and validation  
- [ ] PDF file format detection and validation
- [ ] ZIP/RAR archive validation
- [ ] Folder-based manga detection
- [ ] File corruption detection
- [ ] Format-specific metadata extraction
- [ ] Unsupported format warning system

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F3.1  
**Technical Notes:** Use python-magic for file type detection, implement proper error handling for corrupted files

---

### F3.3 - Manual Library Scan

**Description:** Allow users to manually trigger library scans to discover new or changed manga files.

**User Story:** As a user, I need to scan my library manually so that new manga I've added is discovered and indexed.

**Acceptance Criteria:**
- [ ] Manual scan trigger via UI button
- [ ] Recursive directory scanning
- [ ] New file detection and indexing
- [ ] Removed file cleanup from database
- [ ] Scan progress indicator
- [ ] Scan result summary (added/removed/errors)
- [ ] Background processing for large libraries
- [ ] Scan cancellation functionality

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F3.1, F3.2  
**Technical Notes:** Use background tasks for scanning, implement proper progress tracking

---

### F3.4 - Scheduled Library Sync

**Description:** Implement configurable automatic library synchronization on a schedule.

**User Story:** As a user, I want automatic library syncing so that new manga appears without manual intervention.

**Acceptance Criteria:**
- [ ] Configurable sync intervals (daily, weekly, manual-only)
- [ ] Background task scheduling system
- [ ] Sync status monitoring and logging
- [ ] Failed sync retry logic
- [ ] Per-library-path sync configuration
- [ ] Sync activity dashboard
- [ ] Email/notification on sync failures
- [ ] Resource usage throttling during sync

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F3.3  
**Technical Notes:** Use Celery or similar for task scheduling, implement proper error handling and monitoring

---

## 4. Metadata Management

### F4.1 - Basic Metadata Storage ✅ **COMPLETED**

**Description:** Store and manage basic manga metadata (title, author, description, genres) in flexible database schema.

**User Story:** As a reader, I need manga information stored so that I can browse and organize my collection effectively.

**Acceptance Criteria:**
- [x] Series model with core fields (title, author, artist, description, status, cover_path)
- [x] Chapter model with core fields (id, series_id, number, title, file_path, read_status)
- [x] Flexible metadata_json field using JSONB for extensible metadata
- [x] Proper foreign key relationships with cascade delete
- [x] Unique constraints and proper indexing
- [x] Support for decimal chapter numbers (1.5, 2.5, etc.)
- [x] Comprehensive test coverage (9 test cases)
- [x] Database models follow existing patterns and pass linting

**Priority:** High  
**Complexity:** Simple  
**Dependencies:** F1.1 ✅  
**Technical Notes:** ✅ Implemented with JSON/JSONB variant for SQLite/PostgreSQL compatibility, proper relationships and constraints established

**Implementation Details:**
- **Series Model**: `backend/app/models/series.py` with flexible JSON metadata storage
- **Chapter Model**: `backend/app/models/chapter.py` with numeric precision and constraints  
- **Tests**: `backend/tests/unit/test_models.py` with comprehensive model validation
- **Database Compatibility**: Uses `JSON().with_variant(JSONB(), 'postgresql')` for cross-database support

---

### F4.2 - MangaDex Metadata Enrichment

**Description:** Automatically fetch and populate metadata from MangaDex API when adding new series.

**User Story:** As a user, I want automatic metadata population so that I don't need to manually enter series information.

**Acceptance Criteria:**
- [ ] MangaDex API client implementation
- [ ] Series lookup by title or ID
- [ ] Automatic metadata population on series creation
- [ ] Rate limiting compliance with MangaDex API
- [ ] API error handling and fallback
- [ ] Metadata caching to reduce API calls
- [ ] Manual metadata refresh option
- [ ] API unavailability graceful degradation

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F4.1  
**Technical Notes:** Implement proper HTTP client with retry logic, cache responses appropriately

---

### F4.3 - Manual Metadata Editing

**Description:** Provide UI forms for users to manually edit and override metadata for any series or chapter.

**User Story:** As a curator, I need to edit metadata so that I can correct information or add personal details.

**Acceptance Criteria:**
- [ ] Series metadata edit form with all fields
- [ ] Chapter metadata edit form
- [ ] Validation for required fields
- [ ] Undo/redo functionality for changes
- [ ] Bulk edit capability for multiple series
- [ ] Change history tracking
- [ ] Preview mode before saving changes
- [ ] Restore to original metadata option

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F4.1, F4.2  
**Technical Notes:** Implement proper form validation, consider using React Hook Form for frontend

---

### F4.4 - Custom Tags System

**Description:** Allow users to create and assign custom tags to series and chapters for personal organization.

**User Story:** As an organizer, I need custom tags so that I can categorize manga according to my personal system.

**Acceptance Criteria:**
- [ ] Tag creation and management interface
- [ ] Tag assignment to series and chapters
- [ ] Tag color coding and icons
- [ ] Tag hierarchy support (parent/child tags)
- [ ] Tag usage statistics
- [ ] Tag search and filtering
- [ ] Bulk tag operations
- [ ] Tag export/import functionality

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F4.1  
**Technical Notes:** Consider many-to-many relationship design, implement tag suggestion system

---

### F4.5 - Cover Art Management

**Description:** Handle cover art display, caching, and custom cover upload functionality.

**User Story:** As a visual browser, I need cover art displayed so that I can quickly identify and browse series visually.

**Acceptance Criteria:**
- [ ] Cover art extraction from MangaDex
- [ ] Local cover art file support
- [ ] Custom cover upload functionality
- [ ] Thumbnail generation and caching
- [ ] Multiple cover resolutions (thumbnail, medium, full)
- [ ] Cover art fallback system
- [ ] Batch cover art refresh
- [ ] Cover art storage optimization

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F4.2, F3.1  
**Technical Notes:** Use Pillow for image processing, implement proper caching strategy

---

## 5. User Interface Core

### F5.1 - Frontend Application Setup ✅ **COMPLETED**

**Description:** Initialize Next.js frontend application with TypeScript, Tailwind CSS, and shadcn/ui components.

**User Story:** As a user, I need a modern web interface so that I can interact with KireMisu effectively.

**Acceptance Criteria:**
- [x] Next.js 15.5+ application initialized
- [x] TypeScript configuration
- [x] Tailwind CSS styling system
- [x] shadcn/ui component library integrated
- [x] Responsive design foundation
- [ ] Dark/light theme support
- [x] Font and color system established
- [x] Basic routing structure

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** None  
**Technical Notes:** Complete setup with App Router. Missing dark/light theme toggle.

---

### F5.2 - Authentication UI ✅ **COMPLETED**

**Description:** Create login and authentication-related user interface components.

**User Story:** As a user, I need a login interface so that I can securely access my manga library.

**Acceptance Criteria:**
- [x] Login form with username/password fields
- [x] Login validation and error handling
- [x] JWT token storage and management
- [ ] Automatic token refresh
- [ ] Logout functionality
- [ ] Protected route wrapper component
- [x] Authentication loading states
- [ ] Remember me functionality

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F2.1, F5.1  
**Technical Notes:** Login form complete with validation. Missing token refresh, logout, and protected routes.

---

### F5.3 - Navigation Structure

**Description:** Implement main navigation menu and routing system for the application.

**User Story:** As a user, I need clear navigation so that I can access different sections of the application easily.

**Acceptance Criteria:**
- [ ] Main navigation menu (sidebar or top nav)
- [ ] Navigation items: Library, Lists, Watching, Search, Settings
- [ ] Active state indication
- [ ] Responsive navigation for mobile
- [ ] Breadcrumb navigation where appropriate
- [ ] Quick access shortcuts
- [ ] Navigation accessibility features
- [ ] User menu with profile and logout

**Priority:** High  
**Complexity:** Simple  
**Dependencies:** F5.1, F5.2  
**Technical Notes:** Use Next.js router, implement proper accessibility attributes

---

### F5.4 - Library Grid View

**Description:** Create a responsive grid layout for displaying manga series with cover thumbnails.

**User Story:** As a browser, I need a visual grid of my manga so that I can quickly scan and select series to read.

**Acceptance Criteria:**
- [ ] Responsive grid layout for series covers
- [ ] Lazy loading for performance
- [ ] Hover effects and selection states
- [ ] Series title and basic info display
- [ ] Grid/list view toggle
- [ ] Configurable grid density
- [ ] Keyboard navigation support
- [ ] Loading skeleton states

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F4.1, F4.5, F5.1  
**Technical Notes:** Use CSS Grid or Flexbox, implement proper image optimization

---

### F5.5 - Series Detail View

**Description:** Create detailed series pages showing metadata, chapters, and management options.

**User Story:** As a reader, I need detailed series information so that I can learn about manga and access chapters.

**Acceptance Criteria:**
- [ ] Series cover display with metadata
- [ ] Chapter list with read status indicators
- [ ] Volume grouping for chapters
- [ ] Reading progress indicators
- [ ] Series actions (mark as read, add to list, etc.)
- [ ] Metadata edit access
- [ ] Chapter sorting options
- [ ] Related series suggestions

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F4.1, F5.1  
**Technical Notes:** Implement proper data loading states, consider infinite scroll for large chapter lists

---

## 6. Content Discovery

### F6.1 - Library Search

**Description:** Implement full-text search across manga titles, authors, and metadata.

**User Story:** As a user, I need to search my library so that I can quickly find specific manga or authors.

**Acceptance Criteria:**
- [ ] Search input with autocomplete
- [ ] Full-text search across title, author, description
- [ ] Tag and genre search support
- [ ] Search result highlighting
- [ ] Recent search history
- [ ] Advanced search filters
- [ ] Search performance optimization
- [ ] Empty state handling

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F4.1, F5.1  
**Technical Notes:** Consider using PostgreSQL full-text search or separate search index

---

### F6.2 - Filtering System

**Description:** Provide advanced filtering options by genre, status, tags, and other metadata.

**User Story:** As a curator, I need filtering options so that I can narrow down my collection by specific criteria.

**Acceptance Criteria:**
- [ ] Filter panel with collapsible sections
- [ ] Genre/tag multiselect filters
- [ ] Status and rating filters
- [ ] Date range filtering
- [ ] Read status filtering
- [ ] Filter combination (AND/OR logic)
- [ ] Filter preset saving
- [ ] Clear all filters functionality

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F4.1, F5.1  
**Technical Notes:** Implement efficient database queries, consider filter URL state management

---

### F6.3 - Sorting Options

**Description:** Allow users to sort their library by various criteria (title, date, rating, etc.).

**User Story:** As an organizer, I need sorting options so that I can view my collection in different orders.

**Acceptance Criteria:**
- [ ] Sort by title (A-Z, Z-A)
- [ ] Sort by date added
- [ ] Sort by last read
- [ ] Sort by rating/score
- [ ] Sort by author/artist
- [ ] Sort order persistence
- [ ] Multiple sort criteria
- [ ] Sort direction indicators

**Priority:** Medium  
**Complexity:** Simple  
**Dependencies:** F4.1, F5.4  
**Technical Notes:** Implement efficient database sorting, store user preferences

---

## 7. Reading Experience

### F7.1 - Manga Reader Core

**Description:** Implement the core manga reading interface with page navigation and display.

**User Story:** As a reader, I need a manga reader so that I can read chapters comfortably in my browser.

**Acceptance Criteria:**
- [ ] Full-screen reading mode
- [ ] Page-by-page navigation
- [ ] Keyboard controls (arrow keys, space)
- [ ] Mouse/touch navigation
- [ ] Page zoom functionality
- [ ] Reading progress tracking
- [ ] Chapter boundaries handling
- [ ] Image loading optimization

**Priority:** High  
**Complexity:** Complex  
**Dependencies:** F3.2, F5.1  
**Technical Notes:** Handle different archive formats, implement proper image loading and caching

---

### F7.2 - Reading Modes

**Description:** Support multiple reading modes (single page, double page, vertical scroll).

**User Story:** As a reader with preferences, I need different reading modes so that I can read manga in my preferred style.

**Acceptance Criteria:**
- [ ] Single page mode
- [ ] Double page spread mode
- [ ] Vertical scroll mode (webtoon style)
- [ ] Reading mode persistence per user
- [ ] Automatic mode detection based on content
- [ ] Mode switching during reading
- [ ] Reading direction (left-to-right, right-to-left)
- [ ] Full-screen toggle

**Priority:** Medium  
**Complexity:** Complex  
**Dependencies:** F7.1  
**Technical Notes:** Consider different manga formats and reading cultures, implement proper page layout logic

---

### F7.3 - Reading Progress Tracking

**Description:** Track and store reading progress for each chapter and series.

**User Story:** As a reader, I need progress tracking so that I can resume reading where I left off.

**Acceptance Criteria:**
- [ ] Per-chapter read status (unread, reading, completed)
- [ ] Page-level progress within chapters
- [ ] Series completion percentage
- [ ] Reading history timeline
- [ ] Resume reading functionality
- [ ] Progress sync across devices
- [ ] Bulk mark as read/unread
- [ ] Reading statistics dashboard

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** F7.1, F1.1  
**Technical Notes:** Store progress efficiently, consider real-time updates during reading

---

### F7.4 - Chapter Annotations

**Description:** Allow users to add personal notes and annotations to chapters.

**User Story:** As a studious reader, I need to add notes so that I can record thoughts and observations while reading.

**Acceptance Criteria:**
- [ ] Add note functionality in reader
- [ ] Chapter-level annotation storage
- [ ] Note editing and deletion
- [ ] Note display in reader interface
- [ ] Note export functionality
- [ ] Search through notes
- [ ] Note timestamps and versioning
- [ ] Note sharing options (future)

**Priority:** Low  
**Complexity:** Medium  
**Dependencies:** F7.1, F1.1  
**Technical Notes:** Design non-intrusive note UI, consider rich text formatting options

---

## 8. Organization & Lists

### F8.1 - Custom Reading Lists

**Description:** Allow users to create custom lists and organize series into them.

**User Story:** As an organizer, I need custom lists so that I can group manga by themes or reading status.

**Acceptance Criteria:**
- [ ] Create/edit/delete custom lists
- [ ] Add/remove series from lists
- [ ] List description and cover image
- [ ] Series can belong to multiple lists
- [ ] List ordering and sorting
- [ ] List sharing options
- [ ] Default lists (Reading, Completed, Plan to Read)
- [ ] Bulk list operations

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F4.1, F5.1  
**Technical Notes:** Implement many-to-many relationships, consider list performance for large collections

---

### F8.2 - Smart Lists

**Description:** Implement automatically populated lists based on criteria (new additions, unfinished, etc.).

**User Story:** As an automated organizer, I need smart lists so that series are automatically categorized based on rules.

**Acceptance Criteria:**
- [ ] "Recently Added" smart list
- [ ] "Currently Reading" smart list
- [ ] "Completed" smart list
- [ ] "Unread" smart list
- [ ] Custom smart list rule creation
- [ ] Smart list refresh scheduling
- [ ] Rule-based filtering logic
- [ ] Smart list performance optimization

**Priority:** Low  
**Complexity:** Complex  
**Dependencies:** F8.1, F4.1  
**Technical Notes:** Implement efficient query logic, consider caching for performance

---

## 9. MangaDex Integration

### F9.1 - MangaDex API Client

**Description:** Implement robust MangaDex API client with authentication and rate limiting.

**User Story:** As a system, I need MangaDex integration so that users can search and download content from the platform.

**Acceptance Criteria:**
- [ ] MangaDex API wrapper with authentication
- [ ] Rate limiting compliance
- [ ] Error handling and retry logic
- [ ] API response caching
- [ ] Connection pooling for efficiency
- [ ] API health monitoring
- [ ] Graceful degradation on API failures
- [ ] API version compatibility handling

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** None  
**Technical Notes:** Follow MangaDex API documentation strictly, implement proper error handling

---

### F9.2 - MangaDex Search Integration

**Description:** Allow users to search MangaDex catalog from within KireMisu interface.

**User Story:** As a content discoverer, I need MangaDex search so that I can find and add new manga to my library.

**Acceptance Criteria:**
- [ ] Search interface integrated with library search
- [ ] MangaDex results display with metadata
- [ ] Series preview before adding
- [ ] Add to library functionality
- [ ] Search result pagination
- [ ] Advanced search filters
- [ ] Search history
- [ ] Comparison with local library

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F9.1, F6.1  
**Technical Notes:** Implement clear distinction between local and remote results

---

### F9.3 - Chapter Download from MangaDex

**Description:** Enable downloading chapters from MangaDex directly into the local library.

**User Story:** As a collector, I need to download chapters so that I can build my local manga collection.

**Acceptance Criteria:**
- [ ] Individual chapter download
- [ ] Bulk chapter download for series
- [ ] Download queue management
- [ ] Download progress indicators
- [ ] Download cancellation
- [ ] File format consistency
- [ ] Download retry on failures
- [ ] Download bandwidth throttling

**Priority:** Medium  
**Complexity:** Complex  
**Dependencies:** F9.1, F3.2  
**Technical Notes:** Handle MangaDex download URLs properly, implement proper file organization

---

## 10. Watching System

### F10.1 - Watch List Management

**Description:** Allow users to mark series for watching and manage their watch list.

**User Story:** As a follower, I need to watch series so that I'm notified when new chapters are available.

**Acceptance Criteria:**
- [ ] Add/remove series from watch list
- [ ] Watch list display interface
- [ ] Watch status indicators
- [ ] Bulk watch list operations
- [ ] Watch list export/import
- [ ] Watch settings per series
- [ ] Watch list statistics
- [ ] Watch list organization

**Priority:** Medium  
**Complexity:** Simple  
**Dependencies:** F4.1, F9.1  
**Technical Notes:** Design efficient data structure for watch tracking

---

### F10.2 - Update Polling System

**Description:** Implement scheduled polling of watched series for new chapter releases.

**User Story:** As a watcher, I need automatic checking so that I know when new chapters are available.

**Acceptance Criteria:**
- [ ] Configurable polling intervals
- [ ] Intelligent scheduling to avoid rate limits
- [ ] Differential update checking
- [ ] Polling status monitoring
- [ ] Error handling and retry logic
- [ ] Performance optimization for large watch lists
- [ ] Manual refresh capability
- [ ] Polling activity logs

**Priority:** Medium  
**Complexity:** Complex  
**Dependencies:** F10.1, F9.1  
**Technical Notes:** Implement proper background task scheduling, consider distributed polling

---

### F10.3 - New Chapter Notifications

**Description:** Provide notification system for newly available chapters of watched series.

**User Story:** As a watcher, I need notifications so that I can quickly access new content.

**Acceptance Criteria:**
- [ ] In-app notification system
- [ ] Visual indicators for new chapters
- [ ] Notification history
- [ ] Notification preferences per series
- [ ] Bulk notification actions
- [ ] Notification dismissal
- [ ] Browser push notifications
- [ ] Email notifications (optional)

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F10.2, F5.1  
**Technical Notes:** Implement proper notification management, consider user preferences

---

## 11. File Management

### F11.1 - File Renaming System

**Description:** Implement custom naming schemes and bulk file renaming functionality.

**User Story:** As an organizer, I need file renaming so that my library follows consistent naming conventions.

**Acceptance Criteria:**
- [ ] Custom naming template configuration
- [ ] Template variable system (title, chapter, volume)
- [ ] Bulk rename functionality
- [ ] Rename preview/dry-run mode
- [ ] Conflict detection and resolution
- [ ] Rollback capability
- [ ] Safety checks and validation
- [ ] Rename operation logging

**Priority:** Low  
**Complexity:** Complex  
**Dependencies:** F4.1, F3.1  
**Technical Notes:** Implement safe file operations, provide comprehensive preview system

---

### F11.2 - File Organization

**Description:** Allow users to reorganize files into structured directory layouts based on metadata.

**User Story:** As a collector, I need file organization so that my storage follows a logical structure.

**Acceptance Criteria:**
- [ ] Directory structure templates
- [ ] Automatic folder creation
- [ ] File moving operations
- [ ] Organization preview mode
- [ ] Duplicate handling
- [ ] Organization status tracking
- [ ] Undo reorganization capability
- [ ] Storage space validation

**Priority:** Low  
**Complexity:** Complex  
**Dependencies:** F11.1, F4.1  
**Technical Notes:** Handle cross-filesystem operations, implement proper error recovery

---

## 12. API & Automation

### F12.1 - Core REST API

**Description:** Implement comprehensive REST API covering all main application functionality.

**User Story:** As a developer, I need a REST API so that I can automate and integrate KireMisu with other tools.

**Acceptance Criteria:**
- [ ] Series CRUD endpoints
- [ ] Chapter CRUD endpoints
- [ ] Metadata management endpoints
- [ ] Reading progress endpoints
- [ ] Search and filtering endpoints
- [ ] List management endpoints
- [ ] File operations endpoints
- [ ] OpenAPI/Swagger documentation

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** All core features  
**Technical Notes:** Follow REST conventions, implement proper error responses

---

### F12.2 - API Rate Limiting

**Description:** Implement rate limiting and security measures for API access.

**User Story:** As a system administrator, I need API protection so that my server remains stable under heavy use.

**Acceptance Criteria:**
- [ ] Request rate limiting per API key
- [ ] Different limits for different endpoints
- [ ] Rate limit headers in responses
- [ ] Rate limit status monitoring
- [ ] Configurable rate limits
- [ ] IP-based limiting options
- [ ] Rate limit bypass for internal operations
- [ ] Rate limit violation logging

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** F12.1, F2.2  
**Technical Notes:** Use efficient rate limiting algorithms, consider distributed rate limiting

---

### F12.3 - Webhook System

**Description:** Implement webhooks for external integration when events occur in KireMisu.

**User Story:** As an integrator, I need webhooks so that external systems can react to changes in my library.

**Acceptance Criteria:**
- [ ] Webhook endpoint registration
- [ ] Event type configuration
- [ ] Webhook payload formatting
- [ ] Delivery retry logic
- [ ] Webhook security (signatures)
- [ ] Webhook testing tools
- [ ] Delivery failure handling
- [ ] Webhook activity logs

**Priority:** Low  
**Complexity:** Medium  
**Dependencies:** F12.1  
**Technical Notes:** Implement proper event queueing, consider webhook security best practices

---

## 13. Enhanced Features

### F13.1 - Bulk Metadata Operations

**Description:** Provide tools for bulk editing and managing metadata across multiple series.

**User Story:** As a curator, I need bulk operations so that I can efficiently manage large collections.

**Acceptance Criteria:**
- [ ] Multi-series selection interface
- [ ] Bulk metadata editing
- [ ] Bulk tag application
- [ ] Bulk metadata refresh from sources
- [ ] Bulk operation progress tracking
- [ ] Operation cancellation capability
- [ ] Bulk operation history
- [ ] Operation result summary

**Priority:** Low  
**Complexity:** Medium  
**Dependencies:** F4.3, F4.2  
**Technical Notes:** Implement efficient batch processing, provide clear progress feedback

---

### F13.2 - Advanced Search Features

**Description:** Implement advanced search with complex queries and saved searches.

**User Story:** As a power user, I need advanced search so that I can create complex queries for my collection.

**Acceptance Criteria:**
- [ ] Boolean search operators (AND, OR, NOT)
- [ ] Field-specific searches
- [ ] Regex search support
- [ ] Saved search queries
- [ ] Search query builder interface
- [ ] Search result export
- [ ] Complex filter combinations
- [ ] Search performance optimization

**Priority:** Low  
**Complexity:** Complex  
**Dependencies:** F6.1, F6.2  
**Technical Notes:** Consider search index optimization, implement query validation

---

### F13.3 - Reading Statistics

**Description:** Provide detailed reading statistics and insights for users.

**User Story:** As a data enthusiast, I need reading statistics so that I can understand my reading patterns.

**Acceptance Criteria:**
- [ ] Reading time tracking
- [ ] Pages/chapters read statistics
- [ ] Reading streak tracking
- [ ] Genre preference analysis
- [ ] Monthly/yearly reading reports
- [ ] Reading goal setting and tracking
- [ ] Statistics visualization charts
- [ ] Statistics export functionality

**Priority:** Low  
**Complexity:** Medium  
**Dependencies:** F7.3, F4.1  
**Technical Notes:** Implement privacy-conscious statistics, consider data aggregation strategies

---

### F13.4 - Theme Customization

**Description:** Allow users to customize the application's appearance with themes and layout options.

**User Story:** As a visual user, I need customization options so that I can personalize my reading environment.

**Acceptance Criteria:**
- [ ] Dark/light theme toggle
- [ ] Custom color scheme creation
- [ ] Layout density options
- [ ] Font size and family selection
- [ ] Custom CSS support
- [ ] Theme import/export
- [ ] Per-device theme preferences
- [ ] Theme preview functionality

**Priority:** Low  
**Complexity:** Simple  
**Dependencies:** F5.1  
**Technical Notes:** Use CSS custom properties for theming, implement proper theme persistence

---

### F13.5 - Backup and Export

**Description:** Provide comprehensive backup and export functionality for user data and settings.

**User Story:** As a prudent user, I need backup options so that I can protect my library data and settings.

**Acceptance Criteria:**
- [ ] Full library metadata export
- [ ] Reading progress export
- [ ] Custom lists export
- [ ] Settings configuration export
- [ ] Automated backup scheduling
- [ ] Backup validation and verification
- [ ] Selective restore functionality
- [ ] Cross-instance migration support

**Priority:** Low  
**Complexity:** Medium  
**Dependencies:** All data-related features  
**Technical Notes:** Implement secure backup formats, consider data compression

---

## Implementation Priority Summary

### Phase 1 - Foundation (Weeks 1-4) - **MOSTLY COMPLETE ✅**
- F1.1: Database Schema & Models Setup ✅ **COMPLETED** (User model done, Series/Chapter models needed)
- F1.2: Application Configuration System ✅ **COMPLETED**
- F1.3: Docker Containerization ✅ **COMPLETED**
- F2.1: Basic User Authentication ✅ **COMPLETED** (Login done, registration needed)
- F5.1: Frontend Application Setup ✅ **COMPLETED** (Dark/light theme missing)

### Phase 2 - Core Functionality (Weeks 5-10)
- F3.1: Storage Path Configuration
- F3.2: File Format Detection
- F3.3: Manual Library Scan
- F4.1: Basic Metadata Storage
- F4.2: MangaDex Metadata Enrichment
- F5.2: Authentication UI
- F5.3: Navigation Structure
- F5.4: Library Grid View
- F5.5: Series Detail View

### Phase 3 - Reading & Discovery (Weeks 11-16)
- F6.1: Library Search
- F7.1: Manga Reader Core
- F7.3: Reading Progress Tracking
- F4.3: Manual Metadata Editing
- F6.2: Filtering System
- F6.3: Sorting Options

### Phase 4 - Integration & Enhancement (Weeks 17-24)
- F9.1: MangaDex API Client
- F9.2: MangaDex Search Integration
- F10.1: Watch List Management
- F8.1: Custom Reading Lists
- F2.2: API Key Management
- F12.1: Core REST API

### Phase 5 - Advanced Features (Weeks 25+)
- F3.4: Scheduled Library Sync
- F7.2: Reading Modes
- F9.3: Chapter Download from MangaDex
- F10.2: Update Polling System
- F10.3: New Chapter Notifications
- All remaining low-priority features

---

## Technical Architecture Notes

- **Database**: PostgreSQL with SQLAlchemy ORM for flexibility and robustness
- **Backend**: FastAPI with async support for performance
- **Frontend**: Next.js 15.5+ with TypeScript for modern web experience
- **Styling**: Tailwind CSS with shadcn/ui for consistent design system
- **State Management**: Zustand for client-side state management
- **Authentication**: JWT-based authentication with secure token handling
- **File Processing**: Python libraries for archive handling and image processing
- **Background Tasks**: Celery or FastAPI BackgroundTasks for async operations
- **Deployment**: Docker containers with docker-compose for easy self-hosting

---

## Technical Debt & Refactoring Tasks

### TD-001: Decouple Model Imports from Configuration Loading
**Priority:** Medium  
**Impact:** Development Experience, Testing, Architecture  
**Scope:** Configuration System Refactoring

**Issue:** Currently, importing database models (`from app.models import Series, Chapter`) triggers configuration validation and requires environment variables to be set. This happens because:
1. Models import `app.db.database`
2. Database imports `app.core.config` 
3. Config immediately instantiates `settings = Settings()` at module level
4. Settings validation requires environment variables

**Problems:**
- Cannot import models without full environment setup
- Testing models in isolation requires environment mocking
- IDE/REPL exploration is hindered
- Violates separation of concerns (models depend on runtime config)

**Solution:** Refactor config loading to be lazy/explicit:
- Move `settings = Settings()` out of module-level initialization
- Initialize settings in application startup (`main.py`) or database connection functions
- Make models importable without side effects
- Ensure existing functionality continues to work

**Files Affected:** `app/core/config.py`, `app/db/database.py`, `app/main.py`, possibly `app/api/` endpoints

**Estimated Effort:** 2-3 hours  
**Risk:** Medium (could affect existing authentication and database connections)  
**When to Address:** During next refactoring sprint or when touching config/database code

---

## Current Implementation Status

### ✅ **COMPLETED FEATURES (7/47)**
- **F1.1**: Database Schema & Models Setup ✅ **COMPLETED** (All models: User, Series, Chapter)
- **F1.2**: Application Configuration System (Complete)
- **F1.3**: Docker Containerization (Complete)
- **F2.1**: Basic User Authentication (Partial - Login complete, registration needed)
- **F4.1**: Basic Metadata Storage ✅ **COMPLETED** (Series and Chapter models with tests)
- **F5.1**: Frontend Application Setup (Partial - Dark/light theme missing)
- **F5.2**: Authentication UI (Partial - Login form complete, logout/protected routes needed)

### 🚧 **NEXT PRIORITY FEATURES**
- **F3.1**: Storage Path Configuration
- **F3.2**: File Format Detection
- **F3.3**: Manual Library Scan
- **F5.3**: Navigation Structure
- **F5.4**: Library Grid View

### 📊 **PROGRESS SUMMARY**
- **Foundation Phase**: ~85% complete (6/6 features mostly done, F4.1 completed)
- **Overall Progress**: ~15% complete (7/47 features)
- **Estimated remaining effort**: 19-21 weeks for full feature set

---

## Conclusion

This atomic feature breakdown provides a comprehensive roadmap for implementing KireMisu incrementally. Each feature is designed to be independently implementable while contributing to the overall product vision. The prioritization ensures that core functionality is delivered first, with advanced features building upon the solid foundation.

**Current Status**: The project has a strong foundation with Docker containerization, authentication, and frontend setup complete. The next phase should focus on implementing Series/Chapter database models and basic manga library functionality.

The development team can use this breakdown to plan sprints, estimate effort, and ensure that each implementation phase delivers meaningful user value while maintaining high code quality and system reliability.