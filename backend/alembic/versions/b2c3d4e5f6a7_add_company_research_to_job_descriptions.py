"""add company_research to job_descriptions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company_research JSONB column to job_descriptions."""
    op.add_column(
        'job_descriptions',
        sa.Column('company_research', JSONB, nullable=True),
    )


def downgrade() -> None:
    """Remove company_research from job_descriptions."""
    op.drop_column('job_descriptions', 'company_research')
