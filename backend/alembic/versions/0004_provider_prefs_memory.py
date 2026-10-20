"""provider preferences, interview memory, and question evaluations

Revision ID: 0004_provider_prefs_memory
Revises: 0003_eval_feedback_hints
Create Date: 2026-10-20 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_provider_prefs_memory'
down_revision: Union[str, None] = '0003_eval_feedback_hints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Provider preferences
    op.add_column('provider_configs', sa.Column('default_model', sa.String(length=100), nullable=True))
    op.add_column('provider_configs', sa.Column('interviewer_model', sa.String(length=100), nullable=True))
    op.add_column('provider_configs', sa.Column('evaluation_model', sa.String(length=100), nullable=True))
    op.add_column('provider_configs', sa.Column('coding_model', sa.String(length=100), nullable=True))
    op.add_column('provider_configs', sa.Column('planning_model', sa.String(length=100), nullable=True))
    op.add_column('provider_configs', sa.Column('fallback_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('provider_configs', sa.Column('fallback_provider', sa.String(length=50), nullable=True))
    op.add_column('provider_configs', sa.Column('fallback_model', sa.String(length=100), nullable=True))
    op.add_column('provider_configs', sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'))
    op.add_column('provider_configs', sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='2048'))

    # Self-evaluation per question
    op.add_column('self_evaluations', sa.Column('question_evaluations', sa.JSON(), nullable=False, server_default='[]'))

    # Interview running summary and memory tracking
    op.add_column('interviews', sa.Column('current_summary', sa.Text(), nullable=False, server_default=''))
    op.add_column('interviews', sa.Column('covered_topics', sa.JSON(), nullable=False, server_default='[]'))

def downgrade() -> None:
    op.drop_column('interviews', 'covered_topics')
    op.drop_column('interviews', 'current_summary')
    op.drop_column('self_evaluations', 'question_evaluations')
    op.drop_column('provider_configs', 'max_tokens')
    op.drop_column('provider_configs', 'temperature')
    op.drop_column('provider_configs', 'fallback_model')
    op.drop_column('provider_configs', 'fallback_provider')
    op.drop_column('provider_configs', 'fallback_enabled')
    op.drop_column('provider_configs', 'planning_model')
    op.drop_column('provider_configs', 'coding_model')
    op.drop_column('provider_configs', 'evaluation_model')
    op.drop_column('provider_configs', 'interviewer_model')
    op.drop_column('provider_configs', 'default_model')
