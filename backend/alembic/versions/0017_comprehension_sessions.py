"""create comprehension_sessions table

Revision ID: 0017_comprehension_sessions
Revises: 0016_interview_message_kind
Create Date: 2026-11-06 01:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0017_comprehension_sessions'
down_revision: Union[str, None] = '0016_interview_message_kind'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comprehension_sessions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='in_progress'),
        sa.Column('answers', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_comprehension_sessions_user_id', 'comprehension_sessions', ['user_id'])
    op.create_index('ix_comprehension_sessions_item_id', 'comprehension_sessions', ['item_id'])


def downgrade() -> None:
    op.drop_index('ix_comprehension_sessions_item_id', table_name='comprehension_sessions')
    op.drop_index('ix_comprehension_sessions_user_id', table_name='comprehension_sessions')
    op.drop_table('comprehension_sessions')
