"""create project_copilot_turns table (server-side prompt log)

Revision ID: 0015_project_copilot_turns
Revises: 0014_explanation_telemetry
Create Date: 2026-11-05 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0015_project_copilot_turns'
down_revision: Union[str, None] = '0014_explanation_telemetry'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_copilot_turns',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False, server_default=''),
        sa.Column('response_source', sa.String(length=20), nullable=False, server_default='llm'),
        sa.Column('tests_passed', sa.Integer(), nullable=True),
        sa.Column('tests_total', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_project_copilot_turns_user_id', 'project_copilot_turns', ['user_id'])
    op.create_index('ix_project_copilot_turns_project_id', 'project_copilot_turns', ['project_id'])
    op.create_index('ix_project_copilot_turns_created_at', 'project_copilot_turns', ['created_at'])
    op.create_index('ix_project_copilot_turns_user_project', 'project_copilot_turns', ['user_id', 'project_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_project_copilot_turns_user_project', table_name='project_copilot_turns')
    op.drop_index('ix_project_copilot_turns_created_at', table_name='project_copilot_turns')
    op.drop_index('ix_project_copilot_turns_project_id', table_name='project_copilot_turns')
    op.drop_index('ix_project_copilot_turns_user_id', table_name='project_copilot_turns')
    op.drop_table('project_copilot_turns')
