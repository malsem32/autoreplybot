"""Quick phrases, vacation mode and AI replies

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "snippets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("shortcut", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("photo_paths", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("account_id", "shortcut"),
    )
    op.create_index("ix_snippets_account_id", "snippets", ["account_id"])

    op.add_column(
        "telegram_accounts", sa.Column("away_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "telegram_accounts", sa.Column("away_text", sa.Text(), nullable=False, server_default="")
    )
    op.add_column(
        "telegram_accounts",
        sa.Column("away_timezone", sa.String(64), nullable=False, server_default="Europe/Moscow"),
    )
    op.add_column(
        "telegram_accounts",
        sa.Column("ai_knowledge", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "telegram_accounts",
        sa.Column("ai_tone", sa.String(16), nullable=False, server_default="friendly"),
    )
    op.add_column(
        "autoresponder_rules",
        sa.Column("ai_reply", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("autoresponder_events", "rule_id", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "autoresponder_events",
        sa.Column("kind", sa.String(16), nullable=False, server_default="rule"),
    )


def downgrade() -> None:
    op.execute("DELETE FROM autoresponder_events WHERE rule_id IS NULL")
    op.drop_column("autoresponder_events", "kind")
    op.alter_column("autoresponder_events", "rule_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("autoresponder_rules", "ai_reply")
    op.drop_column("telegram_accounts", "ai_tone")
    op.drop_column("telegram_accounts", "ai_knowledge")
    op.drop_column("telegram_accounts", "away_timezone")
    op.drop_column("telegram_accounts", "away_text")
    op.drop_column("telegram_accounts", "away_until")
    op.drop_index("ix_snippets_account_id", table_name="snippets")
    op.drop_table("snippets")
