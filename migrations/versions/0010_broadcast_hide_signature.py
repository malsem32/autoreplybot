"""Pro option to send broadcasts without the bot signature

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broadcast_campaigns",
        sa.Column("hide_signature", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("broadcast_campaigns", "hide_signature")
