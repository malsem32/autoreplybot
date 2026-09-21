"""add tag_random_users to broadcast_campaigns

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21

"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broadcast_campaigns",
        sa.Column("tag_random_users", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("broadcast_campaigns", "tag_random_users")
