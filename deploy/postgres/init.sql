-- =============================================================================
-- PostgreSQL Initialization Script for NexusAI
-- =============================================================================
-- This script runs on first database initialization
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas for different services
CREATE SCHEMA IF NOT EXISTS nexusai;
CREATE SCHEMA IF NOT EXISTS keycloak;
CREATE SCHEMA IF NOT EXISTS openfga;

-- Grant permissions on schemas to current user (postgres by default)
GRANT ALL ON SCHEMA nexusai TO CURRENT_USER;
GRANT ALL ON SCHEMA keycloak TO CURRENT_USER;
GRANT ALL ON SCHEMA openfga TO CURRENT_USER;
GRANT ALL ON SCHEMA public TO CURRENT_USER;

-- Set default configurations for logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = 'on';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Set search path
ALTER DATABASE nexusai SET search_path TO nexusai, public;

-- Create function for updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Enable Row Level Security helper functions
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id', true);
END;
$$ LANGUAGE plpgsql STABLE;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'NexusAI database initialization completed successfully!';
END $$;
