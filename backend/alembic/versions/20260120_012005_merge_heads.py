"""Chain link between 20260119 and 20260120 migration batches.

Revision ID: e196f9b2d0b4
Revises: 20260119_005
Create Date: 2026-01-20 01:20:05.861947+00:00

No-op migration that bridges the 20260119 batch (events, entities, metrics,
prompts, evaluation) to the 20260120 batch (conversations, organizations,
messages, audit logs). Not a merge — the revision chain is linear.
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'e196f9b2d0b4'
down_revision: Union[str, None] = '20260119_005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
