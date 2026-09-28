"""Pro automation: autoreply schedule & smart options, per-chat broadcast
stats, auto-disabling failing chats, reports, templates, Pro plans and trial

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _bool(name: str) -> sa.Column:
    return sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())


def _int(name: str, default: int) -> sa.Column:
    return sa.Column(name, sa.Integer(), nullable=False, server_default=str(default))


def upgrade() -> None:
    op.add_column("autoresponder_rules", _bool("schedule_enabled"))
    op.add_column(
        "autoresponder_rules",
        sa.Column("schedule_days", sa.JSON(), nullable=False, server_default="[0,1,2,3,4,5,6]"),
    )
    op.add_column(
        "autoresponder_rules",
        sa.Column("schedule_start", sa.String(5), nullable=False, server_default="19:00"),
    )
    op.add_column(
        "autoresponder_rules",
        sa.Column("schedule_end", sa.String(5), nullable=False, server_default="09:00"),
    )
    op.add_column(
        "autoresponder_rules",
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/Moscow"),
    )
    op.add_column("autoresponder_rules", _bool("new_contacts_only"))
    op.add_column("autoresponder_rules", _int("skip_if_owner_active_minutes", 0))
    op.add_column("autoresponder_rules", _int("typing_delay_seconds", 0))
    op.add_column("autoresponder_rules", _bool("notify_owner"))

    op.create_table(
        "autoresponder_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("autoresponder_rules.id"), nullable=False),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_autoresponder_events_rule_id", "autoresponder_events", ["rule_id"])
    op.create_index("ix_autoresponder_events_account_id", "autoresponder_events", ["account_id"])
    op.create_index("ix_autoresponder_events_created_at", "autoresponder_events", ["created_at"])

    op.add_column("broadcast_campaigns", _bool("auto_disable_failing"))
    op.add_column(
        "broadcast_campaigns",
        sa.Column("disabled_targets", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("broadcast_campaigns", _bool("notify_report"))

    op.add_column("broadcast_logs", sa.Column("target", sa.String(255), nullable=True))
    # Older error rows carry the target as the "<target>: <error>" prefix.
    op.execute(
        "UPDATE broadcast_logs SET target = split_part(error_message, ': ', 1) "
        "WHERE target IS NULL AND status = 'error' AND error_message LIKE '%: %'"
    )
    op.create_index(
        "ix_broadcast_logs_campaign_target", "broadcast_logs", ["campaign_id", "target"]
    )

    op.create_table(
        "flood_wait_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("telegram_accounts.id"), nullable=False
        ),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_flood_wait_events_account_id", "flood_wait_events", ["account_id"])
    op.create_index("ix_flood_wait_events_created_at", "flood_wait_events", ["created_at"])

    op.create_table(
        "message_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_message_templates_user_id", "message_templates", ["user_id"])

    op.add_column("users", sa.Column("trial_used_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pro_settings", _int("quarter_stars_price", 130))
    op.add_column("pro_settings", _int("year_stars_price", 450))
    op.add_column("pro_settings", _int("trial_days", 3))


def downgrade() -> None:
    op.drop_column("pro_settings", "trial_days")
    op.drop_column("pro_settings", "year_stars_price")
    op.drop_column("pro_settings", "quarter_stars_price")
    op.drop_column("users", "trial_used_at")
    op.drop_table("message_templates")
    op.drop_table("flood_wait_events")
    op.drop_index("ix_broadcast_logs_campaign_target", table_name="broadcast_logs")
    op.drop_column("broadcast_logs", "target")
    for column in ("notify_report", "disabled_targets", "auto_disable_failing"):
        op.drop_column("broadcast_campaigns", column)
    op.drop_table("autoresponder_events")
    for column in (
        "notify_owner",
        "typing_delay_seconds",
        "skip_if_owner_active_minutes",
        "new_contacts_only",
        "timezone",
        "schedule_end",
        "schedule_start",
        "schedule_days",
        "schedule_enabled",
    ):
        op.drop_column("autoresponder_rules", column)
