"""provider_config_version

Revision ID: 0008_provider_config_version
Revises: 0007_learning_backlog
Create Date: 2026-10-20 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0008_provider_config_version'
down_revision: Union[str, None] = '0007_learning_backlog'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TABLE provider_configs ADD COLUMN IF NOT EXISTS config_version INTEGER NOT NULL DEFAULT 1")

def downgrade() -> None:
    op.execute("ALTER TABLE provider_configs DROP COLUMN IF EXISTS config_version")
