"""Add agents, tools, and executions tables.

Revision ID: 20240201_000001
Revises: 001_initial
Create Date: 2024-02-01 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240201_000001'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Ownership
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),

        # Basic info
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),

        # Configuration
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('model_provider', sa.String(50), nullable=False, server_default='openai'),
        sa.Column('model_name', sa.String(100), nullable=False, server_default='gpt-4o'),
        sa.Column('model_config', postgresql.JSONB, nullable=True, server_default='{}'),

        # Capabilities
        sa.Column('capabilities', postgresql.ARRAY(sa.String), nullable=True, server_default='{}'),

        # Tools and MCP
        sa.Column('tools_config', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('mcp_servers', postgresql.JSONB, nullable=True, server_default='[]'),
        sa.Column('actions_config', postgresql.JSONB, nullable=True, server_default='[]'),

        # Sharing
        sa.Column('is_public', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('shared_with_users', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True, server_default='{}'),
        sa.Column('shared_with_groups', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True, server_default='{}'),

        # Marketplace
        sa.Column('is_marketplace_listed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('marketplace_category', sa.String(100), nullable=True),
        sa.Column('usage_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('rating', sa.Float, nullable=True),
        sa.Column('rating_count', sa.Integer, nullable=False, server_default='0'),

        # Extra data (note: 'metadata' is reserved by SQLAlchemy)
        sa.Column('agent_metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create indexes for agents
    op.create_index('ix_agents_creator_id', 'agents', ['creator_id'])
    op.create_index('ix_agents_organization_id', 'agents', ['organization_id'])

    # Create agent_tools table
    op.create_table(
        'agent_tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tool_type', sa.String(50), nullable=False, server_default='function'),
        sa.Column('schema_definition', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('config', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create index for agent_tools
    op.create_index('ix_agent_tools_agent_id', 'agent_tools', ['agent_id'])

    # Create agent_executions table
    op.create_table(
        'agent_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        # Note: conversation_id FK removed - conversations table may not exist yet
        # The FK can be added in a later migration when conversations table is created
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Execution details
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('input_message', sa.Text, nullable=False),
        sa.Column('output_message', sa.Text, nullable=True),

        # Tool calls
        sa.Column('tool_calls', postgresql.JSONB, nullable=True, server_default='[]'),
        sa.Column('tool_results', postgresql.JSONB, nullable=True, server_default='[]'),

        # Handoff
        sa.Column('handoff_to_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('handoff_context', postgresql.JSONB, nullable=True),

        # Metrics
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),

        # Error handling
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('error_details', postgresql.JSONB, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create indexes for agent_executions
    op.create_index('ix_agent_executions_agent_id', 'agent_executions', ['agent_id'])
    op.create_index('ix_agent_executions_user_id', 'agent_executions', ['user_id'])


def downgrade() -> None:
    op.drop_table('agent_executions')
    op.drop_table('agent_tools')
    op.drop_table('agents')
