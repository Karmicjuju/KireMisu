# KireMisu Data Model - Comprehensive Schema

## Overview

This data model supports KireMisu's core requirements:
- **Flexible metadata** with user customization and external source integration
- **Watching system** with polling state management
- **File system integration** across multiple storage types
- **Reading progress** and user annotations
- **Custom lists** and advanced filtering capabilities

## Entity Relationship Overview

```
LibraryPath (1) ←→ (N) Series (1) ←→ (N) Volume (1) ←→ (N) Chapter (1) ←→ (N) Page
     ↓                    ↓                                      ↓
WatchedSeries         ReadingListItem                    ChapterAnnotation
     ↓                    ↓
ChapterUpdate        ReadingList
```

---

## Core Entities

### Series
Central entity representing a manga series with hybrid relational/document structure.

```sql
CREATE TABLE series (
    -- Core identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),                    -- MangaDx ID or other source
    source VARCHAR(50) NOT NULL DEFAULT 'local', -- 'local', 'mangadx', etc.
    
    -- Multi-language title support (optimized for search)
    title_primary VARCHAR(500) NOT NULL,
    title_english VARCHAR(500),
    title_romaji VARCHAR(500), 
    title_original VARCHAR(500),                 -- Japanese/Chinese original
    alternative_titles TEXT[],                   -- All other known titles
    
    -- Core searchable metadata
    author VARCHAR(255),
    artist VARCHAR(255),
    authors TEXT[],                              -- All contributors for search
    description TEXT,
    
    -- Publication metadata
    publication_year INTEGER,
    release_date DATE,
    last_chapter_date DATE,                      -- Most recent chapter release
    
    -- Status fields (standardized enums)
    publication_status VARCHAR(50) NOT NULL DEFAULT 'unknown', 
    -- 'ongoing', 'completed', 'hiatus', 'cancelled', 'unknown'
    scanlation_status VARCHAR(50) NOT NULL DEFAULT 'unknown',
    -- 'ongoing', 'completed', 'dropped', 'licensed', 'unknown'
    
    -- Genre and classification (optimized for filtering)
    genres TEXT[] NOT NULL DEFAULT '{}',         -- GIN indexed
    themes TEXT[] NOT NULL DEFAULT '{}',         -- GIN indexed  
    demographic VARCHAR(50),                     -- 'shounen', 'seinen', etc.
    content_rating VARCHAR(50),                  -- 'safe', 'suggestive', etc.
    
    -- User customization
    custom_tags TEXT[] NOT NULL DEFAULT '{}',   -- User-defined tags
    user_rating DECIMAL(3,1),                   -- 1.0-10.0 scale
    user_status VARCHAR(50),                    -- 'reading', 'completed', etc.
    user_notes TEXT,
    
    -- Computed/cached fields for performance
    total_chapters INTEGER NOT NULL DEFAULT 0,
    available_chapters INTEGER NOT NULL DEFAULT 0,
    chapter_count INTEGER NOT NULL DEFAULT 0,   -- Excluding extras
    volume_count INTEGER NOT NULL DEFAULT 0,
    
    -- File system integration
    library_path_id UUID NOT NULL REFERENCES library_path(id),
    series_folder VARCHAR(1000) NOT NULL,       -- Relative path within library
    
    -- Cover and display
    cover_image_path VARCHAR(1000),
    cover_image_url VARCHAR(1000),              -- External cover URL
    thumbnail_path VARCHAR(1000),               -- Cached local thumbnail
    
    -- Flexible metadata (JSONB for schema evolution)
    source_metadata JSONB NOT NULL DEFAULT '{}', -- Original external API data
    user_metadata JSONB NOT NULL DEFAULT '{}',   -- User custom fields
    
    -- Watching system (embedded approach)
    is_watched BOOLEAN NOT NULL DEFAULT FALSE,
    watching_config JSONB NOT NULL DEFAULT '{}', -- Per-source watching config
    
    -- Metadata management
    metadata_source VARCHAR(100) NOT NULL DEFAULT 'manual',
    metadata_last_updated TIMESTAMP WITH TIME ZONE,
    user_metadata_locked BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_scanned TIMESTAMP WITH TIME ZONE
);
```

### Volume
Optional grouping level between series and chapters.

```sql
CREATE TABLE volume (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    
    -- Volume identification
    volume_number INTEGER NOT NULL,
    title VARCHAR(500),
    
    -- Metadata
    cover_image_path VARCHAR(1000),
    description TEXT,
    release_date DATE,
    
    -- File system (if volume is a single file/folder)
    folder_path VARCHAR(1000),
    
    -- Computed fields (updated by triggers)
    chapter_count INTEGER NOT NULL DEFAULT 0,
    total_pages INTEGER NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(series_id, volume_number)
);
```

### Chapter
Individual chapters with flexible storage type support.

```sql
CREATE TABLE chapter (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    volume_id UUID REFERENCES volume(id) ON DELETE SET NULL,
    
    -- Chapter identification
    chapter_number DECIMAL(10,2),               -- Supports 1.5, 2.1, etc.
    title VARCHAR(500),
    chapter_title VARCHAR(500),                 -- Sometimes different from title
    
    -- External source info
    external_id VARCHAR(255),                   -- MangaDx chapter ID
    source_url VARCHAR(1000),
    
    -- File system structure (supports multiple storage types)
    storage_type VARCHAR(50) NOT NULL,          -- 'compressed', 'folder', 'single_file'
    base_path VARCHAR(1000) NOT NULL,           -- Path to chapter folder or file
    file_format VARCHAR(50),                    -- 'cbz', 'cbr', 'zip', 'folder', 'pdf'
    
    -- Content metadata
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    release_date DATE,
    scanlator VARCHAR(255),
    page_count INTEGER NOT NULL DEFAULT 0,
    
    -- File info
    total_size BIGINT NOT NULL DEFAULT 0,       -- Total size in bytes
    is_available BOOLEAN NOT NULL DEFAULT TRUE, -- All files exist on disk
    
    -- Download tracking (for external sources)
    is_downloaded BOOLEAN NOT NULL DEFAULT FALSE,
    download_status VARCHAR(50) NOT NULL DEFAULT 'none',
    -- 'none', 'pending', 'downloading', 'completed', 'failed'
    download_progress DECIMAL(5,2) NOT NULL DEFAULT 0.0, -- 0.0-100.0
    
    -- User interaction
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    current_page INTEGER NOT NULL DEFAULT 1,    -- Last page user was on
    reading_progress DECIMAL(5,2) NOT NULL DEFAULT 0.0, -- Calculated percentage
    last_read_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(series_id, chapter_number, language)
);
```

### Page
Individual pages/images within chapters.

```sql
CREATE TABLE page (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapter(id) ON DELETE CASCADE,
    
    -- Page identification
    page_number INTEGER NOT NULL,               -- 1-indexed
    filename VARCHAR(500) NOT NULL,
    
    -- File details
    file_path VARCHAR(1000) NOT NULL,           -- Full path to image file
    file_size BIGINT NOT NULL DEFAULT 0,
    image_format VARCHAR(20) NOT NULL,          -- 'jpg', 'png', 'webp', etc.
    
    -- Image metadata
    width INTEGER,
    height INTEGER,
    aspect_ratio DECIMAL(10,4),                 -- width/height
    
    -- Processing state
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    thumbnail_path VARCHAR(1000),               -- Cached thumbnail
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- User interaction
    is_bookmarked BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(chapter_id, page_number)
);
```

### LibraryPath
Storage locations configuration.

```sql
CREATE TABLE library_path (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,                 -- User-friendly name
    path VARCHAR(1000) NOT NULL UNIQUE,         -- Absolute filesystem path
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Scan configuration
    scan_interval VARCHAR(50) NOT NULL DEFAULT 'manual', -- 'manual', 'daily', 'weekly'
    last_scan TIMESTAMP WITH TIME ZONE,
    scan_status VARCHAR(50) NOT NULL DEFAULT 'idle', -- 'idle', 'scanning', 'error'
    scan_error TEXT,
    
    -- Settings
    auto_import BOOLEAN NOT NULL DEFAULT TRUE,  -- Auto-create series from folders
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

## Watching System

### ChapterUpdate
Track discovered updates from external sources.

```sql
CREATE TABLE chapter_update (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    
    -- Update details
    chapter_number DECIMAL(10,2) NOT NULL,
    chapter_title VARCHAR(500),
    external_chapter_id VARCHAR(255) NOT NULL,
    release_date DATE,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    
    -- Notification state
    status VARCHAR(50) NOT NULL DEFAULT 'new',  -- 'new', 'seen', 'downloaded', 'dismissed'
    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    notified_at TIMESTAMP WITH TIME ZONE,
    downloaded_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(series_id, external_chapter_id)
);
```

---

## User Content Organization

### ReadingList
User-created collections.

```sql
CREATE TABLE reading_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,                               -- For future multi-user support
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(20),                          -- Hex color for UI
    emoji VARCHAR(10),                          -- Display emoji
    
    -- List settings
    is_public BOOLEAN NOT NULL DEFAULT FALSE,   -- For future sharing
    sort_order VARCHAR(50) NOT NULL DEFAULT 'manual', -- 'manual', 'title', 'date_added'
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### ReadingListItem
Many-to-many relationship between lists and series.

```sql
CREATE TABLE reading_list_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reading_list_id UUID NOT NULL REFERENCES reading_list(id) ON DELETE CASCADE,
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    
    -- List-specific metadata
    position INTEGER NOT NULL DEFAULT 0,        -- For manual ordering
    notes TEXT,                                 -- User notes about inclusion
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(reading_list_id, series_id)
);
```

### ChapterAnnotation
User notes and annotations.

```sql
CREATE TABLE chapter_annotation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapter(id) ON DELETE CASCADE,
    user_id UUID,                               -- For future multi-user support
    
    -- Annotation content
    annotation_type VARCHAR(50) NOT NULL DEFAULT 'note', -- 'note', 'bookmark', 'highlight'
    content TEXT NOT NULL,
    page_number INTEGER,                        -- Specific page if applicable
    
    -- Position data (for future image annotations)
    x_coordinate DECIMAL(8,6),                  -- Relative position 0.0-1.0
    y_coordinate DECIMAL(8,6),
    
    -- Metadata
    is_private BOOLEAN NOT NULL DEFAULT TRUE,
    color VARCHAR(20),                          -- For UI display
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

## Background Processing

### JobQueue
PostgreSQL-based background job system.

```sql
CREATE TABLE job_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,             -- 'file_sync', 'metadata_poll', etc.
    payload JSONB NOT NULL,
    
    -- Execution control
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    priority INTEGER NOT NULL DEFAULT 0,        -- Higher = more important
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_count INTEGER NOT NULL DEFAULT 0,
    
    -- Scheduling
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    INDEX(status, scheduled_at),                -- For job worker queries
    INDEX(job_type, status)                     -- For monitoring
);
```

---

## Database Indexes

### Performance-Critical Indexes

```sql
-- Series search and filtering
CREATE INDEX idx_series_title_search ON series 
USING GIN (to_tsvector('english', 
    COALESCE(title_primary, '') || ' ' || 
    COALESCE(title_english, '') || ' ' || 
    COALESCE(title_romaji, '') || ' ' || 
    COALESCE(title_original, '') || ' ' ||
    COALESCE(array_to_string(alternative_titles, ' '), '')
));

CREATE INDEX idx_series_genres ON series USING GIN (genres);
CREATE INDEX idx_series_themes ON series USING GIN (themes);
CREATE INDEX idx_series_custom_tags ON series USING GIN (custom_tags);
CREATE INDEX idx_series_authors ON series USING GIN (authors);

-- Status and metadata filtering
CREATE INDEX idx_series_publication_status ON series (publication_status);
CREATE INDEX idx_series_user_status ON series (user_status);
CREATE INDEX idx_series_demographic ON series (demographic);
CREATE INDEX idx_series_content_rating ON series (content_rating);

-- Watching system queries
CREATE INDEX idx_series_watching ON series (is_watched) WHERE is_watched = TRUE;
CREATE INDEX idx_series_watching_config ON series USING GIN (watching_config) 
WHERE is_watched = TRUE;

-- Reading progress and library management
CREATE INDEX idx_chapter_series_number ON chapter (series_id, chapter_number);
CREATE INDEX idx_chapter_reading_progress ON chapter (series_id, is_read, last_read_at);
CREATE INDEX idx_page_chapter_number ON page (chapter_id, page_number);

-- File system operations
CREATE INDEX idx_series_library_path ON series (library_path_id, series_folder);
CREATE INDEX idx_chapter_availability ON chapter (is_available, storage_type);

-- Background jobs
CREATE INDEX idx_job_queue_worker ON job_queue (status, scheduled_at, priority DESC);
CREATE INDEX idx_job_queue_monitoring ON job_queue (job_type, status, created_at);

-- Chapter updates and notifications
CREATE INDEX idx_chapter_update_status ON chapter_update (status, discovered_at DESC);
CREATE INDEX idx_chapter_update_series ON chapter_update (series_id, status);

-- Composite indexes for common query patterns
CREATE INDEX idx_series_status_genre ON series (publication_status, genres);
CREATE INDEX idx_series_updated_recent ON series (updated_at DESC) 
WHERE updated_at > NOW() - INTERVAL '30 days';
```

### JSONB-Specific Indexes

```sql
-- Watching configuration paths
CREATE INDEX idx_watching_mangadx_next_check ON series 
((watching_config->'mangadx'->>'next_check')::timestamp)
WHERE is_watched = TRUE AND watching_config ? 'mangadx';

CREATE INDEX idx_watching_mangadx_active ON series 
((watching_config->'mangadx'->>'is_active')::boolean)
WHERE is_watched = TRUE AND watching_config ? 'mangadx';

-- User metadata search
CREATE INDEX idx_series_user_metadata ON series USING GIN (user_metadata);
CREATE INDEX idx_series_source_metadata ON series USING GIN (source_metadata);
```

---

## Key Design Principles

### 1. Hybrid Schema Approach
- **Relational core** for structured data requiring ACID compliance
- **JSONB fields** for flexible metadata that evolves over time
- **Array types** for multi-value fields with GIN indexing

### 2. Watching System Integration
- **Embedded watching config** in series table for performance
- **Separate update tracking** for notification management
- **Flexible per-source configuration** supports multiple APIs

### 3. File System Abstraction
- **Multiple storage types** supported through unified interface
- **Path-based organization** while maintaining database integrity
- **Availability tracking** handles temporary file system issues

### 4. Performance Optimization
- **Strategic indexing** for common query patterns
- **Computed fields** to avoid expensive aggregations
- **JSONB indexing** for flexible metadata queries

### 5. Future Extensibility
- **UUID primary keys** for distributed system compatibility
- **Flexible metadata schemas** accommodate new sources
- **User-centric design** ready for multi-user expansion

This data model provides a robust foundation for KireMisu's core functionality while maintaining flexibility for future enhancements and performance optimization.