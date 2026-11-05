"""evaluation credibility column and evaluation_disputes table

Revision ID: 0020_evaluation_credibility
Revises: 0019_project_events
Create Date: 2026-11-06 04:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0020_evaluation_credibility'
down_revision: Union[str, None] = '0019_project_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('evaluations', sa.Column('credibility', sa.JSON(), nullable=True))
    op.create_table(
        'evaluation_disputes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluation_id', sa.String(length=36), sa.ForeignKey('evaluations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dimension_id', sa.String(length=80), nullable=False),
        sa.Column('argument', sa.Text(), nullable=False),
        sa.Column('quote', sa.Text(), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('old_score', sa.Integer(), nullable=True),
        sa.Column('new_score', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_evaluation_disputes_evaluation_id', 'evaluation_disputes', ['evaluation_id'])
    op.create_index('ix_evaluation_disputes_user_id', 'evaluation_disputes', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_evaluation_disputes_user_id', table_name='evaluation_disputes')
    op.drop_index('ix_evaluation_disputes_evaluation_id', table_name='evaluation_disputes')
    op.drop_table('evaluation_disputes')
    op.drop_column('evaluations', 'credibility')
