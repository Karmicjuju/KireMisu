-- Migration: Create filter_presets table and performance indexes
-- Created for F6.2 and F6.3 implementation: Series filtering and sorting

-- Create filter_presets table
CREATE TABLE IF NOT EXISTS filter_presets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id VARCHAR(36) NOT NULL,
    filters_json JSONB NOT NULL,
    sorting_json JSONB,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for filter_presets table
CREATE INDEX IF NOT EXISTS ix_filter_presets_id ON filter_presets (id);
CREATE INDEX IF NOT EXISTS ix_filter_presets_name ON filter_presets (name);
CREATE INDEX IF NOT EXISTS ix_filter_presets_user_id ON filter_presets (user_id);
CREATE INDEX IF NOT EXISTS ix_filter_presets_is_public ON filter_presets (is_public);
CREATE INDEX IF NOT EXISTS ix_filter_presets_user_name ON filter_presets (user_id, name);
CREATE INDEX IF NOT EXISTS ix_filter_presets_public ON filter_presets (is_public, name);
CREATE INDEX IF NOT EXISTS ix_filter_presets_filters_gin ON filter_presets USING gin (filters_json);

-- Add performance indexes for series table filtering and sorting
-- These indexes improve performance for the advanced filtering queries

-- Existing indexes that should be preserved:
-- ix_series_title (already exists)
-- ix_series_status (already exists)
-- ix_series_title_gin (already exists from original schema)
-- ix_series_author_gin (already exists from original schema)

-- Additional indexes for better performance with filtering
CREATE INDEX IF NOT EXISTS ix_series_artist ON series (artist);
CREATE INDEX IF NOT EXISTS ix_series_created_at ON series (created_at);
CREATE INDEX IF NOT EXISTS ix_series_updated_at ON series (updated_at);

-- JSONB indexes for metadata filtering
CREATE INDEX IF NOT EXISTS ix_series_metadata_genres_gin ON series USING gin ((metadata_json->'genres'));
CREATE INDEX IF NOT EXISTS ix_series_metadata_tags_gin ON series USING gin ((metadata_json->'tags'));
CREATE INDEX IF NOT EXISTS ix_series_metadata_rating ON series USING btree (((metadata_json->>'rating')::numeric));
CREATE INDEX IF NOT EXISTS ix_series_metadata_read_status ON series USING btree ((metadata_json->>'read_status'));
CREATE INDEX IF NOT EXISTS ix_series_metadata_last_read ON series USING btree ((metadata_json->>'last_read'));

-- Composite indexes for common filter combinations
CREATE INDEX IF NOT EXISTS ix_series_status_created_at ON series (status, created_at);
CREATE INDEX IF NOT EXISTS ix_series_status_title ON series (status, title);
CREATE INDEX IF NOT EXISTS ix_series_author_title ON series (author, title);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at for filter_presets
CREATE TRIGGER update_filter_presets_updated_at
    BEFORE UPDATE ON filter_presets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE filter_presets IS 'Stores user-defined filter and sort presets for series';
COMMENT ON COLUMN filter_presets.filters_json IS 'JSONB containing SeriesFilterParams data';
COMMENT ON COLUMN filter_presets.sorting_json IS 'JSONB containing SeriesSortParams data';
COMMENT ON COLUMN filter_presets.is_public IS 'Whether the preset is accessible to all users';

-- Verify the pg_trgm extension exists for trigram text search
-- This extension should already be enabled for the existing GIN indexes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        RAISE NOTICE 'Creating pg_trgm extension for better text search performance';
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    END IF;
END
$$;