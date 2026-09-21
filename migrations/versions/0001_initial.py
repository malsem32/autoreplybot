"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-18

"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "telegram_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("encrypted_session", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("username", sa.String(128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_telegram_accounts_user_id", "telegram_accounts", ["user_id"], unique=False)

    op.create_table(
        "autoresponder_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trigger_type", sa.String(16), nullable=False, server_default="all"),
        sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("response_text", sa.String(), nullable=False),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_autoresponder_rules_account_id", "autoresponder_rules", ["account_id"], unique=False
    )

    op.create_table(
        "broadcast_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("text_template", sa.String(), nullable=False),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("target_chat_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("schedule_type", sa.String(16), nullable=False, server_default="recurring"),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_broadcast_campaigns_account_id", "broadcast_campaigns", ["account_id"], unique=False
    )

    op.create_table(
        "broadcast_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "campaign_id", sa.Integer(), sa.ForeignKey("broadcast_campaigns.id"), nullable=False
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_broadcast_logs_campaign_id", "broadcast_logs", ["campaign_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("broadcast_logs")
    op.drop_table("broadcast_campaigns")
    op.drop_table("autoresponder_rules")
    op.drop_table("telegram_accounts")
    op.drop_table("users")
