"""Final migration marker

Revision ID: e196f9b2d0b4
Revises: 20260119_005
Create Date: 2026-01-20 01:20:05.861947+00:00

This is the final migration in the chain. The migration order is:
001_initial -> 20240201_000001 -> 20240301_000001 -> 20240401_000001 ->
20260119_001 -> 20260119_002 -> 20260119_003 -> 20260119_004 -> 20260119_005 -> this
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e196f9b2d0b4'
down_revision: Union[str, None] = '20260119_005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
