"""roles_and_tenants

Revision ID: 0012_roles_and_tenants
Revises: 0011_company_and_enterprise
Create Date: 2026-11-03 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0012_roles_and_tenants'
down_revision: Union[str, None] = '0011_company_and_enterprise'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    -- 1. Create tenants table
    CREATE TABLE IF NOT EXISTS tenants (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        slug VARCHAR(100) NOT NULL UNIQUE,
        is_test BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- 2. Seed default production tenant and sandbox test tenant
    INSERT INTO tenants (id, name, slug, is_test)
    VALUES 
        ('tenant-prod-default', 'Production Candidates', 'default', FALSE),
        ('tenant-test-sandbox', 'Engineering Test Sandbox', 'test-sandbox', TRUE)
    ON CONFLICT (slug) DO NOTHING;

    -- 3. Add columns to users table
    ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'candidate';
    ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id) ON DELETE SET NULL;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

    -- Update existing users to default tenant
    UPDATE users SET tenant_id = 'tenant-prod-default' WHERE tenant_id IS NULL;

    -- 4. Add oa_config to assessment_pipelines
    ALTER TABLE assessment_pipelines ADD COLUMN IF NOT EXISTS oa_config JSONB NOT NULL DEFAULT '{"mode": "preset", "rating_min": 1200, "rating_max": 1600, "topic_tags": ["dp", "graphs"]}'::jsonb;

    -- 5. Add resume and OA fields to candidate_assessments
    ALTER TABLE candidate_assessments ADD COLUMN IF NOT EXISTS resume_text TEXT;
    ALTER TABLE candidate_assessments ADD COLUMN IF NOT EXISTS oa_problem_title VARCHAR(200);
    ALTER TABLE candidate_assessments ADD COLUMN IF NOT EXISTS oa_submitted_code TEXT;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE candidate_assessments DROP COLUMN IF EXISTS oa_submitted_code;
    ALTER TABLE candidate_assessments DROP COLUMN IF EXISTS oa_problem_title;
    ALTER TABLE candidate_assessments DROP COLUMN IF EXISTS resume_text;
    ALTER TABLE assessment_pipelines DROP COLUMN IF EXISTS oa_config;
    ALTER TABLE users DROP COLUMN IF EXISTS is_test;
    ALTER TABLE users DROP COLUMN IF EXISTS tenant_id;
    ALTER TABLE users DROP COLUMN IF EXISTS role;
    DROP TABLE IF EXISTS tenants;
    """)
