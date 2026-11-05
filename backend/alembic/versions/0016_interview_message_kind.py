"""add interview_messages.kind for turn accounting

Revision ID: 0016_interview_message_kind
Revises: 0015_project_copilot_turns
Create Date: 2026-11-05 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0016_interview_message_kind'
down_revision: Union[str, None] = '0015_project_copilot_turns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_messages', sa.Column('kind', sa.String(length=20), nullable=False, server_default='answer'))
    # Backfill legacy rows.
    op.execute("UPDATE interview_messages SET kind = 'question' WHERE role = 'assistant'")
    op.execute("UPDATE interview_messages SET kind = 'hint' WHERE role = 'assistant' AND content LIKE '[Level %'")
    op.execute("UPDATE interview_messages SET kind = 'wrapup' WHERE role = 'assistant' AND content LIKE 'That concludes our interview session%'")
    op.execute("UPDATE interview_messages SET kind = 'hint_request' WHERE role = 'user' AND content LIKE '[Requested Level %'")
    op.execute("UPDATE interview_messages SET kind = 'code_submit' WHERE role = 'user' AND content LIKE '[Candidate Code Submission%'")


def downgrade() -> None:
    op.drop_column('interview_messages', 'kind')
