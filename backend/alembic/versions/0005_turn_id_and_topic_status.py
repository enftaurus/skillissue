"""turn idempotency and topic lifecycle status

Revision ID: 0005_turn_id_and_topic_status
Revises: 0004_provider_prefs_memory
Create Date: 2026-10-20 17:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005_turn_id_and_topic_status'
down_revision: Union[str, None] = '0004_provider_prefs_memory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add client_turn_id to interview_messages for turn idempotency
    op.add_column('interview_messages', sa.Column('client_turn_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_interview_messages_client_turn_id'), 'interview_messages', ['client_turn_id'], unique=False)

    # Add topic_statuses to interviews for explicit topic lifecycle tracking
    op.add_column('interviews', sa.Column('topic_statuses', sa.JSON(), nullable=False, server_default='{}'))

def downgrade() -> None:
    op.drop_column('interviews', 'topic_statuses')
    op.drop_index(op.f('ix_interview_messages_client_turn_id'), table_name='interview_messages')
    op.drop_column('interview_messages', 'client_turn_id')
