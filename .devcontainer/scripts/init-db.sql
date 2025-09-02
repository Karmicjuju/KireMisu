-- KireMisu Database Initialization Script
-- This script sets up the initial database schema for development

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create basic tables based on the KireMisu schema
-- These are minimal tables for development setup

-- Series table
CREATE TABLE IF NOT EXISTS series (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title_primary TEXT NOT NULL,
    title_alt TEXT[],
    description TEXT,
    status TEXT DEFAULT 'ongoing',
    genres TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Flexible metadata storage
    watching_config JSONB DEFAULT '{}',
    user_metadata JSONB DEFAULT '{}',
    source_metadata JSONB DEFAULT '{}',
    
    -- Tracking
    chapter_count INTEGER DEFAULT 0,
    last_chapter_read UUID,
    reading_status TEXT DEFAULT 'plan_to_read',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_read_at TIMESTAMP WITH TIME ZONE
);

-- Chapters table (metadata only, files stored in mounted volumes)
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    
    -- Chapter identification
    chapter_number DECIMAL(10,2) NOT NULL,
    title TEXT,
    volume_number INTEGER,
    
    -- File path information (relative to manga library root)
    relative_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_extension TEXT,
    
    -- Computed metadata (from file scanning)
    page_count INTEGER DEFAULT 0,
    file_size BIGINT,
    file_modified_at TIMESTAMP WITH TIME ZONE,
    
    -- Processing status
    scan_status TEXT DEFAULT 'pending', -- pending, scanned, error
    scan_error TEXT,
    last_scanned_at TIMESTAMP WITH TIME ZONE,
    
    -- Chapter metadata
    source_metadata JSONB DEFAULT '{}',
    
    -- Reading progress
    is_read BOOLEAN DEFAULT false,
    last_page_read INTEGER DEFAULT 0,
    reading_progress DECIMAL(3,2) DEFAULT 0.0, -- 0.0 to 1.0
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(series_id, chapter_number)
);

-- Watch list table
CREATE TABLE IF NOT EXISTS watch_list (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    
    -- Watch configuration
    watch_for_new_chapters BOOLEAN DEFAULT true,
    auto_download BOOLEAN DEFAULT false,
    notification_enabled BOOLEAN DEFAULT true,
    
    -- Metadata
    user_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(series_id)
);

-- Job queue table for background processing
CREATE TABLE IF NOT EXISTS job_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    
    -- Processing information
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    
    -- Timestamps
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_series_title ON series USING GIN (title_primary gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_series_genres ON series USING GIN (genres);
CREATE INDEX IF NOT EXISTS idx_series_status ON series (status);
CREATE INDEX IF NOT EXISTS idx_series_reading_status ON series (reading_status);
CREATE INDEX IF NOT EXISTS idx_series_watching_config ON series USING GIN (watching_config);

CREATE INDEX IF NOT EXISTS idx_chapters_series_id ON chapters (series_id);
CREATE INDEX IF NOT EXISTS idx_chapters_number ON chapters (series_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_chapters_scan_status ON chapters (scan_status);
CREATE INDEX IF NOT EXISTS idx_chapters_relative_path ON chapters (relative_path);
CREATE INDEX IF NOT EXISTS idx_chapters_is_read ON chapters (is_read);

CREATE INDEX IF NOT EXISTS idx_watch_list_series_id ON watch_list (series_id);

CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue (status);
CREATE INDEX IF NOT EXISTS idx_job_queue_type ON job_queue (job_type);
CREATE INDEX IF NOT EXISTS idx_job_queue_scheduled ON job_queue (scheduled_at);

-- Create trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_series_updated_at BEFORE UPDATE ON series
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chapters_updated_at BEFORE UPDATE ON chapters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_watch_list_updated_at BEFORE UPDATE ON watch_list
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development (metadata only)
-- Note: Actual manga files should be placed in the mounted manga library directory
INSERT INTO series (title_primary, description, genres, status) VALUES
('One Piece', 'The story follows the adventures of Monkey D. Luffy, a boy whose body gained the properties of rubber after unintentionally eating a Devil Fruit.', '{"Adventure", "Comedy", "Drama", "Shounen"}', 'ongoing'),
('Naruto', 'The story follows Naruto Uzumaki, a young ninja who seeks recognition from his peers and dreams of becoming the Hokage.', '{"Action", "Adventure", "Martial Arts", "Shounen"}', 'completed'),
('Attack on Titan', 'Humanity fights for survival against giant humanoid Titans.', '{"Action", "Drama", "Horror", "Shounen"}', 'completed')
ON CONFLICT DO NOTHING;

-- Sample chapter metadata (assuming files exist in mounted library)
-- These would typically be created by scanning the manga library directory
INSERT INTO chapters (series_id, chapter_number, title, relative_path, file_name, file_extension, scan_status) 
SELECT 
    s.id,
    1,
    'Romance Dawn',
    'One Piece/Chapter 001 - Romance Dawn.cbz',
    'Chapter 001 - Romance Dawn.cbz',
    'cbz',
    'pending'
FROM series s WHERE s.title_primary = 'One Piece'
ON CONFLICT DO NOTHING;

INSERT INTO chapters (series_id, chapter_number, title, relative_path, file_name, file_extension, scan_status)
SELECT 
    s.id,
    1,
    'Uzumaki Naruto!!',
    'Naruto/Chapter 001 - Uzumaki Naruto!!.cbz',
    'Chapter 001 - Uzumaki Naruto!!.cbz', 
    'cbz',
    'pending'
FROM series s WHERE s.title_primary = 'Naruto'
ON CONFLICT DO NOTHING;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kiremisu;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kiremisu;