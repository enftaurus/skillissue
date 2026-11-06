"""interview termination reason (conduct policy)

Revision ID: 0022_interview_termination
Revises: 0021_assessment_binding
Create Date: 2026-11-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0022_interview_termination'
down_revision: Union[str, None] = '0021_assessment_binding'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('termination_reason', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('interviews', 'termination_reason')
