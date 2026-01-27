-- Initialize PostgreSQL with required extensions and databases
-- NexusAI Multi-Tenant Platform

-- ======================
-- NexusAI Database (AI Chat + RAG)
-- ======================

-- Enable pgvector for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for text similarity
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable btree_gin for better indexing
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ======================
-- Code Similarity Table (for similarity service)
-- ======================

CREATE TABLE IF NOT EXISTS code_snippets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    project_id UUID,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    language VARCHAR(50),
    file_path VARCHAR(500),
    embedding vector(1536),  -- OpenAI embedding dimensions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_hash, tenant_id)
);

-- Vector similarity index
CREATE INDEX IF NOT EXISTS idx_code_snippets_embedding ON code_snippets
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_code_snippets_tenant ON code_snippets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_code_snippets_project ON code_snippets(project_id);

-- ======================
-- DevLake Database (Engineering Analytics)
-- ======================

-- Create DevLake database if it doesn't exist
SELECT 'CREATE DATABASE devlake'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'devlake')\gexec

-- Connect to devlake database and enable extensions
\c devlake

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Switch back to default database
\c nexusai

-- ======================
-- OpenFGA Database (Authorization)
-- ======================

-- Create OpenFGA database if it doesn't exist
SELECT 'CREATE DATABASE openfga'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'openfga')\gexec

\c openfga

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c nexusai

-- ======================
-- Row-Level Security Helper Functions
-- ======================

-- Function to get current tenant from session variable
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if RLS should be bypassed (for migrations, etc.)
CREATE OR REPLACE FUNCTION rls_enabled()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE(current_setting('app.rls_enabled', true)::boolean, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ======================
-- RLS Policy Creation Helper
-- ======================

-- This procedure creates RLS policies for tenant isolation
-- Call after creating tables that need tenant isolation
CREATE OR REPLACE PROCEDURE create_tenant_rls_policy(table_name TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    -- Enable RLS on table
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);

    -- Drop existing policy if exists
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', table_name);

    -- Create tenant isolation policy
    EXECUTE format('
        CREATE POLICY tenant_isolation ON %I
        FOR ALL
        USING (
            NOT rls_enabled()
            OR tenant_id = current_tenant_id()
            OR current_tenant_id() IS NULL
        )
        WITH CHECK (
            NOT rls_enabled()
            OR tenant_id = current_tenant_id()
            OR current_tenant_id() IS NULL
        )
    ', table_name);
END;
$$;

-- Note: RLS policies will be created when SQLAlchemy creates the tables
-- by calling: CALL create_tenant_rls_policy('table_name');

COMMENT ON FUNCTION current_tenant_id() IS 'Returns the current tenant ID from session variable for RLS';
COMMENT ON FUNCTION rls_enabled() IS 'Returns whether RLS is currently enabled';
COMMENT ON PROCEDURE create_tenant_rls_policy(TEXT) IS 'Creates RLS policy for tenant isolation on a table';
