"""add tag_random_users to broadcast_campaigns

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21

"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broadcast_campaigns",
        sa.Column("tag_random_users", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("broadcast_campaigns", "tag_random_users")
