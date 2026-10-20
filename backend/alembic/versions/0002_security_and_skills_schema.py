"""security and skills schema

Revision ID: 0002_security_and_skills_schema
Revises: 0001_initial_schema
Create Date: 2026-10-20 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_security_and_skills_schema'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add token_version to users
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'))

    # 2. Add monthly budgets to provider_configs
    op.add_column('provider_configs', sa.Column('monthly_token_budget', sa.Integer(), nullable=False, server_default='1000000'))
    op.add_column('provider_configs', sa.Column('monthly_tokens_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('provider_configs', sa.Column('monthly_cost_cents_budget', sa.Integer(), nullable=False, server_default='1000'))
    op.add_column('provider_configs', sa.Column('monthly_cost_cents_used', sa.Integer(), nullable=False, server_default='0'))

    # 3. Add tests_passed and tests_total to coding_submissions
    op.add_column('coding_submissions', sa.Column('tests_passed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('coding_submissions', sa.Column('tests_total', sa.Integer(), nullable=False, server_default='0'))

    # 4. Create user_skills table
    op.create_table(
        'user_skills',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'topic', name='uq_user_skills_user_topic')
    )
    op.create_index(op.f('ix_user_skills_user_id'), 'user_skills', ['user_id'])

def downgrade() -> None:
    op.drop_index(op.f('ix_user_skills_user_id'), table_name='user_skills')
    op.drop_table('user_skills')
    op.drop_column('coding_submissions', 'tests_total')
    op.drop_column('coding_submissions', 'tests_passed')
    op.drop_column('provider_configs', 'monthly_cost_cents_used')
    op.drop_column('provider_configs', 'monthly_cost_cents_budget')
    op.drop_column('provider_configs', 'monthly_tokens_used')
    op.drop_column('provider_configs', 'monthly_token_budget')
    op.drop_column('users', 'token_version')
