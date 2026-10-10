-- NexusAI Load Test Database Initialization
-- Enables required PostgreSQL extensions and sets performance tuning.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create test database for isolation
SELECT 'CREATE DATABASE nexusai_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nexusai_test')\gexec

-- Performance tuning for load tests
ALTER SYSTEM SET log_min_duration_statement = 100;    -- Log slow queries (>100ms)
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET track_activity_query_size = 4096;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
SELECT pg_reload_conf();
