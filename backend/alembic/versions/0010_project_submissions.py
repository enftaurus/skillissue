"""project_submissions

Revision ID: 0010_project_submissions
Revises: 0009_azure_provider_support
Create Date: 2026-10-30 01:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0010_project_submissions'
down_revision: Union[str, None] = '0009_azure_provider_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS project_submissions (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        project_id VARCHAR(100) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'incomplete',
        files JSONB NOT NULL DEFAULT '{}'::jsonb,
        test_results JSONB NOT NULL DEFAULT '{}'::jsonb,
        prompt_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
        prompts_count INTEGER NOT NULL DEFAULT 0,
        time_spent_seconds INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_project_submissions_user_id ON project_submissions(user_id);
    CREATE INDEX IF NOT EXISTS ix_project_submissions_project_id ON project_submissions(project_id);
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_submissions;")
