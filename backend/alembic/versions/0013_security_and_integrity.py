"""security_and_integrity

Revision ID: 0013_security_and_integrity
Revises: 0012_roles_and_tenants
Create Date: 2026-11-04 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0013_security_and_integrity'
down_revision: Union[str, None] = '0012_roles_and_tenants'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    -- 1. Add tenant_id to assessment_pipelines with backfill from creators
    ALTER TABLE assessment_pipelines ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id) ON DELETE SET NULL;
    CREATE INDEX IF NOT EXISTS ix_assessment_pipelines_tenant_id ON assessment_pipelines(tenant_id);

    UPDATE assessment_pipelines ap
    SET tenant_id = u.tenant_id
    FROM users u
    WHERE ap.created_by_user_id = u.id AND u.tenant_id IS NOT NULL;

    -- 2. Add token_expires_at to candidate_assessments
    ALTER TABLE candidate_assessments ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ;
    UPDATE candidate_assessments
    SET token_expires_at = created_at + INTERVAL '7 days'
    WHERE token_expires_at IS NULL;

    -- 3. Ensure composite_score is nullable
    ALTER TABLE candidate_assessments ALTER COLUMN composite_score DROP NOT NULL;

    -- 4. Add unique index on (pipeline_id, LOWER(candidate_email))
    CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_assessments_pipeline_email
    ON candidate_assessments(pipeline_id, LOWER(candidate_email));

    -- 5. Add status to evaluations table and allow overall_score to be nullable for not_evaluated state
    ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'completed';
    ALTER TABLE evaluations ALTER COLUMN overall_score DROP NOT NULL;

    -- 6. Add indexes for grouped admin analytics queries
    CREATE INDEX IF NOT EXISTS ix_users_tenant_is_test ON users(tenant_id, is_test);
    CREATE INDEX IF NOT EXISTS ix_interviews_user_status ON interviews(user_id, status);
    """)

def downgrade() -> None:
    op.execute("""
    DROP INDEX IF EXISTS ix_interviews_user_status;
    DROP INDEX IF EXISTS ix_users_tenant_is_test;
    ALTER TABLE evaluations ALTER COLUMN overall_score SET NOT NULL;
    ALTER TABLE evaluations DROP COLUMN IF EXISTS status;
    DROP INDEX IF EXISTS uq_candidate_assessments_pipeline_email;
    ALTER TABLE candidate_assessments ALTER COLUMN composite_score SET NOT NULL;
    ALTER TABLE candidate_assessments DROP COLUMN IF EXISTS token_expires_at;
    DROP INDEX IF EXISTS ix_assessment_pipelines_tenant_id;
    ALTER TABLE assessment_pipelines DROP COLUMN IF EXISTS tenant_id;
    """)
