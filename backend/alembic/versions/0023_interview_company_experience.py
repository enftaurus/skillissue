"""interview target company + experience level; JD extracted experience

Revision ID: 0023_company_experience
Revises: 0022_interview_termination
Create Date: 2026-11-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0023_company_experience'
down_revision: Union[str, None] = '0022_interview_termination'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('company_name', sa.String(length=200), nullable=True))
    op.add_column('interviews', sa.Column('experience_level', sa.String(length=30), nullable=True))
    op.add_column('job_descriptions', sa.Column('extracted_experience', sa.String(length=30), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('job_descriptions', 'extracted_experience')
    op.drop_column('interviews', 'experience_level')
    op.drop_column('interviews', 'company_name')
