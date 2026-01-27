"""Initial schema with all NexusAI tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gin')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=True, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('bio', sa.Text, nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('auth_provider', sa.String(50), nullable=True),
        sa.Column('provider_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_superuser', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('preferences', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('limits', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # Organization members table
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
    )
    op.create_index('ix_org_members_org_id', 'organization_members', ['organization_id'])
    op.create_index('ix_org_members_user_id', 'organization_members', ['user_id'])

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('devlake_project_name', sa.String(255), nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('organization_id', 'slug', name='uq_project_slug'),
    )
    op.create_index('ix_projects_tenant_id', 'projects', ['tenant_id'])
    op.create_index('ix_projects_org_id', 'projects', ['organization_id'])

    # Connections table
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plugin', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('secret_ref', sa.String(255), nullable=True),
        sa.Column('domain_id', sa.String(500), nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_connections_tenant_id', 'connections', ['tenant_id'])
    op.create_index('ix_connections_project_id', 'connections', ['project_id'])
    op.create_index('ix_connections_plugin', 'connections', ['plugin'])

    # Personal Access Tokens table
    op.create_table(
        'personal_access_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('token_prefix', sa.String(20), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_ip', sa.String(45), nullable=True),
        sa.Column('use_count', sa.String(20), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.String(255), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pat_tenant_id', 'personal_access_tokens', ['tenant_id'])
    op.create_index('ix_pat_user_id', 'personal_access_tokens', ['user_id'])
    op.create_index('ix_pat_token_prefix', 'personal_access_tokens', ['token_prefix'])

    # AI Usage Log table
    op.create_table(
        'ai_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tool_type', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('lines_generated', sa.Integer, nullable=True),
        sa.Column('lines_accepted', sa.Integer, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_ai_usage_tenant_id', 'ai_usage_logs', ['tenant_id'])
    op.create_index('ix_ai_usage_project_id', 'ai_usage_logs', ['project_id'])
    op.create_index('ix_ai_usage_tool_type', 'ai_usage_logs', ['tool_type'])
    op.create_index('ix_ai_usage_created_at', 'ai_usage_logs', ['created_at'])

    # Blueprints table
    op.create_table(
        'blueprints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('mode', sa.String(50), nullable=False, server_default='NORMAL'),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('cron_config', sa.String(100), nullable=True),
        sa.Column('is_manual', sa.String(10), nullable=False, server_default='false'),
        sa.Column('settings', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('plan', postgresql.JSONB, nullable=True, server_default='[]'),
        sa.Column('labels', postgresql.JSONB, nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_blueprints_tenant_id', 'blueprints', ['tenant_id'])
    op.create_index('ix_blueprints_project_id', 'blueprints', ['project_id'])

    # Pipeline runs table
    op.create_table(
        'pipeline_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blueprint_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('blueprints.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('plan', postgresql.JSONB, nullable=True, server_default='[]'),
        sa.Column('stages', postgresql.JSONB, nullable=True, server_default='[]'),
        sa.Column('stage_index', sa.String(10), nullable=True, server_default='0'),
        sa.Column('finished_tasks', sa.String(10), nullable=True, server_default='0'),
        sa.Column('total_tasks', sa.String(10), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('skip_on_fail', sa.String(10), nullable=True, server_default='false'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pipeline_runs_tenant_id', 'pipeline_runs', ['tenant_id'])
    op.create_index('ix_pipeline_runs_blueprint_id', 'pipeline_runs', ['blueprint_id'])
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])

    # PR-Issue Correlations table
    op.create_table(
        'pr_issue_correlations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pr_id', sa.String(255), nullable=False),
        sa.Column('pr_number', sa.String(20), nullable=True),
        sa.Column('pr_title', sa.Text, nullable=True),
        sa.Column('pr_description', sa.Text, nullable=True),
        sa.Column('pr_author', sa.String(255), nullable=True),
        sa.Column('pr_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issue_id', sa.String(255), nullable=False),
        sa.Column('issue_number', sa.String(20), nullable=True),
        sa.Column('issue_title', sa.Text, nullable=True),
        sa.Column('issue_description', sa.Text, nullable=True),
        sa.Column('issue_author', sa.String(255), nullable=True),
        sa.Column('issue_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correlation_type', sa.String(50), nullable=False, server_default='semantic'),
        sa.Column('confidence_score', sa.Float, nullable=True, server_default='0.0'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('title_similarity', sa.Float, nullable=True, server_default='0.0'),
        sa.Column('description_similarity', sa.Float, nullable=True, server_default='0.0'),
        sa.Column('semantic_similarity', sa.Float, nullable=True, server_default='0.0'),
        sa.Column('signals', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pr_issue_corr_tenant_id', 'pr_issue_correlations', ['tenant_id'])
    op.create_index('ix_pr_issue_corr_project_id', 'pr_issue_correlations', ['project_id'])
    op.create_index('ix_pr_issue_corr_pr_id', 'pr_issue_correlations', ['pr_id'])
    op.create_index('ix_pr_issue_corr_issue_id', 'pr_issue_correlations', ['issue_id'])

    # Code snippets table (for similarity service)
    op.create_table(
        'code_snippets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('embedding', sa.LargeBinary, nullable=True),  # vector(1536)
        sa.Column('metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('content_hash', 'tenant_id', name='uq_code_snippet_hash'),
    )
    op.create_index('ix_code_snippets_tenant_id', 'code_snippets', ['tenant_id'])
    op.create_index('ix_code_snippets_project_id', 'code_snippets', ['project_id'])

    # Create RLS helper functions
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id()
        RETURNS UUID AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
        EXCEPTION
            WHEN OTHERS THEN
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION rls_enabled()
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN COALESCE(current_setting('app.rls_enabled', true)::boolean, true);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)


def downgrade() -> None:
    # Drop RLS functions
    op.execute('DROP FUNCTION IF EXISTS rls_enabled()')
    op.execute('DROP FUNCTION IF EXISTS current_tenant_id()')

    # Drop tables in reverse order
    op.drop_table('code_snippets')
    op.drop_table('pr_issue_correlations')
    op.drop_table('pipeline_runs')
    op.drop_table('blueprints')
    op.drop_table('ai_usage_logs')
    op.drop_table('personal_access_tokens')
    op.drop_table('connections')
    op.drop_table('projects')
    op.drop_table('organization_members')
    op.drop_table('organizations')
    op.drop_table('users')
