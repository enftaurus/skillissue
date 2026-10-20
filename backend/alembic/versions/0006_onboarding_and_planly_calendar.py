"""onboarding_and_planly_calendar

Revision ID: 0006_onboarding_and_planly_calendar
Revises: 0005_turn_id_and_topic_status
Create Date: 2026-10-20 20:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_onboarding_calendar'
down_revision: Union[str, None] = '0005_turn_id_and_topic_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add onboarding_completed to users
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'))

    # 2. Add latest_submission_id to interviews
    op.add_column('interviews', sa.Column('latest_submission_id', sa.String(length=36), nullable=True))

    # 3. Add calendar and topic fields to plans
    op.add_column('plans', sa.Column('topic', sa.String(length=150), nullable=True))
    op.add_column('plans', sa.Column('goal', sa.String(length=100), nullable=True))
    op.add_column('plans', sa.Column('schedule_days', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('plans', sa.Column('current_level', sa.String(length=30), nullable=False, server_default='intermediate'))
    op.add_column('plans', sa.Column('start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('plans', sa.Column('target_date', sa.DateTime(timezone=True), nullable=True))

    # 4. Add scheduled_date, subtopic, status to plan_tasks
    op.add_column('plan_tasks', sa.Column('subtopic', sa.String(length=150), nullable=True))
    op.add_column('plan_tasks', sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('plan_tasks', sa.Column('status', sa.String(length=30), nullable=False, server_default='upcoming'))

def downgrade() -> None:
    op.drop_column('plan_tasks', 'status')
    op.drop_column('plan_tasks', 'scheduled_date')
    op.drop_column('plan_tasks', 'subtopic')

    op.drop_column('plans', 'target_date')
    op.drop_column('plans', 'start_date')
    op.drop_column('plans', 'current_level')
    op.drop_column('plans', 'schedule_days')
    op.drop_column('plans', 'goal')
    op.drop_column('plans', 'topic')

    op.drop_column('interviews', 'latest_submission_id')
    op.drop_column('users', 'onboarding_completed')
