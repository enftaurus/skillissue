"""create explanation_checks and editor_event_batches tables

Revision ID: 0014_explanation_telemetry
Revises: 0013_security_and_integrity
Create Date: 2026-11-04 21:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0014_explanation_telemetry'
down_revision: Union[str, None] = '0013_security_and_integrity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create explanation_checks table
    op.create_table(
        'explanation_checks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('candidate_assessment_id', sa.String(length=36), sa.ForeignKey('candidate_assessments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('round_key', sa.String(length=50), nullable=False, server_default='oa_dsa'),
        sa.Column('submission_ref', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False, server_default='practice'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('questions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('answers', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('evaluation', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('discriminative_power', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('model_info', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_explanation_checks_user_id', 'explanation_checks', ['user_id'])
    op.create_index('ix_explanation_checks_candidate_assessment_id', 'explanation_checks', ['candidate_assessment_id'])

    # 2. Create editor_event_batches table
    op.create_table(
        'editor_event_batches',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('candidate_assessment_id', sa.String(length=36), sa.ForeignKey('candidate_assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('round_key', sa.String(length=50), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('payload', sa.JSON(), nullable=False),
    )
    op.create_index('ix_editor_event_batches_candidate_assessment_id', 'editor_event_batches', ['candidate_assessment_id'])
    op.create_index('ix_editor_event_batches_candidate_round', 'editor_event_batches', ['candidate_assessment_id', 'round_key'])


def downgrade() -> None:
    op.drop_index('ix_editor_event_batches_candidate_round', table_name='editor_event_batches')
    op.drop_index('ix_editor_event_batches_candidate_assessment_id', table_name='editor_event_batches')
    op.drop_table('editor_event_batches')

    op.drop_index('ix_explanation_checks_candidate_assessment_id', table_name='explanation_checks')
    op.drop_index('ix_explanation_checks_user_id', table_name='explanation_checks')
    op.drop_table('explanation_checks')
