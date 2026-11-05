"""add interview_messages.delivery (spoken delivery metrics)

Revision ID: 0018_message_delivery
Revises: 0017_comprehension_sessions
Create Date: 2026-11-06 03:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0018_message_delivery'
down_revision: Union[str, None] = '0017_comprehension_sessions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_messages', sa.Column('delivery', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_messages', 'delivery')
