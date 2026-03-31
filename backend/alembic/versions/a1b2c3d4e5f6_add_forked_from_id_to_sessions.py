"""add forked_from_id to sessions

Revision ID: a1b2c3d4e5f6
Revises: 6323d988a33a
Create Date: 2026-03-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6323d988a33a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add forked_from_id self-referential FK to sessions."""
    op.add_column(
        'sessions',
        sa.Column('forked_from_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        op.f('fk_sessions_forked_from_id_sessions'),
        'sessions',
        'sessions',
        ['forked_from_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Remove forked_from_id from sessions."""
    op.drop_constraint(
        op.f('fk_sessions_forked_from_id_sessions'),
        'sessions',
        type_='foreignkey',
    )
    op.drop_column('sessions', 'forked_from_id')
