"""learning_backlog_and_weaknesses

Revision ID: 0007_learning_backlog
Revises: 0006_onboarding_calendar
Create Date: 2026-10-20 21:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_learning_backlog'
down_revision: Union[str, None] = '0006_onboarding_calendar'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add weakness_analysis to evaluations
    op.execute("ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS weakness_analysis JSON NOT NULL DEFAULT '[]'")

    # 2. Create learning_backlog table if not exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'learning_backlog' not in tables:
        op.create_table(
            'learning_backlog',
            sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('topic', sa.String(length=150), nullable=False),
            sa.Column('subtopic', sa.String(length=150), nullable=True),
            sa.Column('source', sa.String(length=50), nullable=False, server_default='manual'),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('reason', sa.Text(), nullable=False, server_default=''),
            sa.Column('learning_objective', sa.Text(), nullable=True),
            sa.Column('suggested_exercise', sa.Text(), nullable=True),
            sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='queued'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('planned_plan_id', sa.String(length=36), sa.ForeignKey('plans.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_learning_backlog_user_id', 'learning_backlog', ['user_id'])
        op.create_index('ix_learning_backlog_topic', 'learning_backlog', ['topic'])

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS learning_backlog CASCADE")
    op.execute("ALTER TABLE evaluations DROP COLUMN IF EXISTS weakness_analysis")
