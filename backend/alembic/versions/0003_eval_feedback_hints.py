"""evaluation feedback and hints schema

Revision ID: 0003_eval_feedback_hints
Revises: 0002_security_and_skills_schema
Create Date: 2026-10-20 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_eval_feedback_hints'
down_revision: Union[str, None] = '0002_security_and_skills_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('interviews', sa.Column('hint_level_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('interviews', sa.Column('coding_problem_id', sa.String(length=100), nullable=True))
    op.add_column('evaluations', sa.Column('question_feedback', sa.JSON(), nullable=False, server_default='[]'))

def downgrade() -> None:
    op.drop_column('evaluations', 'question_feedback')
    op.drop_column('interviews', 'coding_problem_id')
    op.drop_column('interviews', 'hint_level_used')
