"""Support requests: admin message ↔ user mapping for replies

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_message_id", sa.Integer(), nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("admin_chat_id", "admin_message_id"),
    )
    op.create_index(
        "ix_support_messages_user_telegram_id", "support_messages", ["user_telegram_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_support_messages_user_telegram_id", table_name="support_messages")
    op.drop_table("support_messages")
