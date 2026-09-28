"""Leads mini-CRM, team access, group autoreplies, keyword match modes,
weekly digest and Pro expiry reminders

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def upgrade() -> None:
    op.add_column(
        "autoresponder_rules",
        sa.Column("match_mode", sa.String(16), nullable=False, server_default="contains"),
    )
    op.add_column(
        "autoresponder_rules",
        sa.Column("scope", sa.String(16), nullable=False, server_default="private"),
    )

    op.add_column(
        "users", sa.Column("weekly_digest", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column("users", _ts("digest_sent_at", nullable=True))
    op.add_column("users", _ts("pro_reminder_for", nullable=True))

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("peer_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False, server_default=""),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("last_text", sa.String(500), nullable=False, server_default=""),
        sa.Column("messages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("note", sa.String(1000), nullable=False, server_default=""),
        _ts("created_at"),
        _ts("last_message_at"),
        sa.UniqueConstraint("account_id", "peer_id"),
    )
    op.create_index("ix_leads_account_id", "leads", ["account_id"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])
    op.create_index("ix_leads_last_message_at", "leads", ["last_message_at"])

    op.create_table(
        "account_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False, server_default=""),
        _ts("created_at"),
        sa.UniqueConstraint("account_id", "user_id"),
    )
    op.create_index("ix_account_members_account_id", "account_members", ["account_id"])
    op.create_index("ix_account_members_user_id", "account_members", ["user_id"])

    op.create_table(
        "team_invites",
        sa.Column("token", sa.String(32), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_team_invites_account_id", "team_invites", ["account_id"])


def downgrade() -> None:
    op.drop_table("team_invites")
    op.drop_table("account_members")
    op.drop_table("leads")
    for column in ("pro_reminder_for", "digest_sent_at", "weekly_digest"):
        op.drop_column("users", column)
    op.drop_column("autoresponder_rules", "scope")
    op.drop_column("autoresponder_rules", "match_mode")
