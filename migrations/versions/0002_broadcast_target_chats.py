"""rename broadcast_campaigns.target_chat_ids to target_chats (str, accepts links/usernames)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21

"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("broadcast_campaigns", "target_chat_ids", new_column_name="target_chats")


def downgrade() -> None:
    op.alter_column("broadcast_campaigns", "target_chats", new_column_name="target_chat_ids")
