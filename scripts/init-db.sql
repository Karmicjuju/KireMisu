-- KireMisu Database Initialization Script
-- This script is run when the PostgreSQL container starts for the first time

-- Create extensions that might be needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create the application database if it doesn't exist (handled by POSTGRES_DB env var)
-- This file is mainly for additional setup

-- Create indexes that might be useful for full-text search
-- These will be created by Alembic migrations, but we can prepare the extensions

-- Grant permissions if needed (not typically required for single-user setups)
-- GRANT ALL PRIVILEGES ON DATABASE kiremisu TO kiremisu;

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'KireMisu database initialized successfully';
END $$;