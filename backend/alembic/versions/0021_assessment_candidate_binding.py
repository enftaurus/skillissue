"""bind enterprise assessments to a signed-in user; server-side round state

Revision ID: 0021_assessment_binding
Revises: 0020_evaluation_credibility
Create Date: 2026-11-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0021_assessment_binding'
down_revision: Union[str, None] = '0020_evaluation_credibility'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('candidate_assessments', sa.Column('candidate_user_id', sa.String(length=36),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_candidate_assessments_candidate_user_id', 'candidate_assessments', ['candidate_user_id'])
    op.add_column('candidate_assessments', sa.Column('round_state', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('candidate_assessments', 'round_state')
    op.drop_index('ix_candidate_assessments_candidate_user_id', table_name='candidate_assessments')
    op.drop_column('candidate_assessments', 'candidate_user_id')
