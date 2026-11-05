"""create project_events (test runs / submissions process log)

Revision ID: 0019_project_events
Revises: 0018_message_delivery
Create Date: 2026-11-06 04:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0019_project_events'
down_revision: Union[str, None] = '0018_message_delivery'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_project_events_user_project', 'project_events', ['user_id', 'project_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_project_events_user_project', table_name='project_events')
    op.drop_table('project_events')
