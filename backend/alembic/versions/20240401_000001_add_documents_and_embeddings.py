"""Add documents and document chunks tables for RAG.

Revision ID: 20240401_000001
Revises: 20240301_000001
Create Date: 2024-04-01 00:00:00.000000

This migration adds:
- documents table for uploaded files
- document_chunks table for vector search with pgvector embeddings
- Proper indexes for efficient similarity search
- Audit log table for security events
- Semantic cache metadata table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20240401_000001'
down_revision: Union[str, None] = '20240301_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> str:
    """Generate SQL to check if table exists."""
    return f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """


def upgrade() -> None:
    conn = op.get_bind()

    # Documents table
    if not conn.execute(sa.text(table_exists('documents'))).scalar():
        op.create_table(
            'documents',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),

            # File info
            sa.Column('filename', sa.String(500), nullable=False),
            sa.Column('original_filename', sa.String(500), nullable=False),
            sa.Column('file_path', sa.Text, nullable=False),
            sa.Column('file_size', sa.Integer, nullable=False),
            sa.Column('mime_type', sa.String(100), nullable=False),
            sa.Column('document_type', sa.String(50), nullable=False),

            # Processing status
            sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
            sa.Column('error_message', sa.Text, nullable=True),

            # Content
            sa.Column('title', sa.String(500), nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('content_hash', sa.String(64), nullable=True),

            # Chunk statistics
            sa.Column('chunk_count', sa.Integer, nullable=False, server_default='0'),
            sa.Column('total_tokens', sa.Integer, nullable=False, server_default='0'),

            # Document metadata (using doc_metadata to avoid reserved name)
            sa.Column('doc_metadata', postgresql.JSONB, nullable=True, server_default='{}'),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_user_status ON documents (user_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (content_hash)")

    # Document chunks table with vector embeddings
    if not conn.execute(sa.text(table_exists('document_chunks'))).scalar():
        op.create_table(
            'document_chunks',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),

            # Chunk content
            sa.Column('content', sa.Text, nullable=False),
            sa.Column('chunk_index', sa.Integer, nullable=False),

            # Token count
            sa.Column('token_count', sa.Integer, nullable=False, server_default='0'),

            # Position in document
            sa.Column('start_char', sa.Integer, nullable=True),
            sa.Column('end_char', sa.Integer, nullable=True),
            sa.Column('page_number', sa.Integer, nullable=True),

            # Chunk metadata (using chunk_metadata to avoid reserved name)
            sa.Column('chunk_metadata', postgresql.JSONB, nullable=True, server_default='{}'),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks (document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_document_index ON document_chunks (document_id, chunk_index)")

    # Add vector column separately (pgvector specific)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='document_chunks' AND column_name='embedding') THEN
                ALTER TABLE document_chunks ADD COLUMN embedding vector(1536);
            END IF;
        END $$;
    """)

    # Create IVFFlat index for vector similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # Audit logs table for security events
    if not conn.execute(sa.text(table_exists('audit_logs'))).scalar():
        op.create_table(
            'audit_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),

            # Event info
            sa.Column('event_type', sa.String(50), nullable=False),
            sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
            sa.Column('resource_type', sa.String(50), nullable=True),
            sa.Column('resource_id', sa.String(255), nullable=True),
            sa.Column('action', sa.String(100), nullable=False),
            sa.Column('summary', sa.Text, nullable=True),

            # Request context
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.String(500), nullable=True),
            sa.Column('request_id', sa.String(100), nullable=True),

            # Event details (redacted if sensitive)
            sa.Column('details', postgresql.JSONB, nullable=True, server_default='{}'),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_event_type ON audit_logs (event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_severity ON audit_logs (severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON audit_logs (resource_type, resource_id)")

    # Semantic cache metadata table
    if not conn.execute(sa.text(table_exists('semantic_cache_entries'))).scalar():
        op.create_table(
            'semantic_cache_entries',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('cache_key', sa.String(64), nullable=False, unique=True),

            # Query info
            sa.Column('query_hash', sa.String(64), nullable=False),
            sa.Column('query_text', sa.Text, nullable=True),

            # Model/provider info
            sa.Column('model', sa.String(100), nullable=True),
            sa.Column('provider', sa.String(50), nullable=True),

            # Cache metadata
            sa.Column('hit_count', sa.Integer, nullable=False, server_default='0'),
            sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

            # Response metadata (actual response in Redis)
            sa.Column('response_tokens', sa.Integer, nullable=True),
            sa.Column('response_cost_usd', sa.Float, nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_semantic_cache_cache_key ON semantic_cache_entries (cache_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_semantic_cache_query_hash ON semantic_cache_entries (query_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_semantic_cache_expires_at ON semantic_cache_entries (expires_at)")

    # Add embedding column for semantic cache (for similarity lookup)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='semantic_cache_entries' AND column_name='embedding') THEN
                ALTER TABLE semantic_cache_entries ADD COLUMN embedding vector(1536);
            END IF;
        END $$;
    """)

    # Create index for semantic cache embeddings
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_semantic_cache_embedding
        ON semantic_cache_entries
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
    """)

    # Agent conversation state table
    if not conn.execute(sa.text(table_exists('agent_states'))).scalar():
        op.create_table(
            'agent_states',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),

            # State info
            sa.Column('current_agent', sa.String(100), nullable=True),
            sa.Column('workflow_status', sa.String(50), nullable=False, server_default='pending'),
            sa.Column('iteration_count', sa.Integer, nullable=False, server_default='0'),

            # State data
            sa.Column('messages', postgresql.JSONB, nullable=True, server_default='[]'),
            sa.Column('task_results', postgresql.JSONB, nullable=True, server_default='[]'),
            sa.Column('context', postgresql.JSONB, nullable=True, server_default='{}'),
            sa.Column('errors', postgresql.JSONB, nullable=True, server_default='[]'),

            # Human-in-the-loop
            sa.Column('requires_human_input', sa.Boolean, nullable=False, server_default='false'),
            sa.Column('human_input_prompt', sa.Text, nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_states_conversation_id ON agent_states (conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_states_user_id ON agent_states (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_states_workflow_status ON agent_states (workflow_status)")


def downgrade() -> None:
    op.drop_table('agent_states')
    op.drop_table('semantic_cache_entries')
    op.drop_table('audit_logs')
    op.drop_table('document_chunks')
    op.drop_table('documents')
