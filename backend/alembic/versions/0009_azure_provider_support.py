"""azure_provider_support

Revision ID: 0009_azure_provider_support
Revises: 0008_provider_config_version
Create Date: 2026-10-28 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0009_azure_provider_support'
down_revision: Union[str, None] = '0008_provider_config_version'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TABLE provider_configs ADD COLUMN IF NOT EXISTS azure_endpoint VARCHAR(255)")
    op.execute("ALTER TABLE provider_configs ADD COLUMN IF NOT EXISTS azure_api_version VARCHAR(50) DEFAULT '2024-06-01'")
    op.execute("ALTER TABLE provider_configs ADD COLUMN IF NOT EXISTS azure_deployment_name VARCHAR(100)")

def downgrade() -> None:
    op.execute("ALTER TABLE provider_configs DROP COLUMN IF EXISTS azure_endpoint")
    op.execute("ALTER TABLE provider_configs DROP COLUMN IF EXISTS azure_api_version")
    op.execute("ALTER TABLE provider_configs DROP COLUMN IF EXISTS azure_deployment_name")
