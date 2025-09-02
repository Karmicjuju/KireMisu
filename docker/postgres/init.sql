-- KireMisu PostgreSQL initialization script

-- Create the database if it doesn't exist (handled by Docker environment variables)
-- This file is for any initial schema setup or seed data

-- Example: Create a settings table
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add any other initial setup here
