"""Pro subscription + photo albums + broadcast send options

- The paid "tag random users" access becomes the general "Pro" subscription
  (same Stars purchase flow, covers several features): rename
  users.tag_feature_expires_at -> pro_expires_at and
  tag_feature_settings -> pro_settings.
- Single photo_path -> photo_paths (JSON list, up to 10 = a Telegram album)
  on autoresponder rules and broadcast campaigns; existing photos migrate.
- Broadcast send options: silent, protect content, no link preview.
- Referral program: who invited whom, whether the invite bonus was paid
  out, bonus days earned, admin-editable bonus size.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_MEDIA_TABLES = ("autoresponder_rules", "broadcast_campaigns")


def upgrade() -> None:
    op.alter_column("users", "tag_feature_expires_at", new_column_name="pro_expires_at")
    op.rename_table("tag_feature_settings", "pro_settings")

    for table in _MEDIA_TABLES:
        op.add_column(
            table,
            sa.Column("photo_paths", sa.JSON(), nullable=False, server_default="[]"),
        )
        op.execute(
            f"UPDATE {table} SET photo_paths = json_build_array(photo_path) "
            "WHERE photo_path IS NOT NULL AND photo_path <> ''"
        )
        op.drop_column(table, "photo_path")

    for column in ("disable_notification", "protect_content", "disable_link_preview"):
        op.add_column(
            "broadcast_campaigns",
            sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    op.add_column(
        "users",
        sa.Column("referred_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_users_referred_by_id", "users", ["referred_by_id"])
    op.add_column(
        "users",
        sa.Column("referral_rewarded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("referral_days_earned", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pro_settings",
        sa.Column("referral_bonus_days", sa.Integer(), nullable=False, server_default="7"),
    )


def downgrade() -> None:
    op.drop_column("pro_settings", "referral_bonus_days")
    op.drop_column("users", "referral_days_earned")
    op.drop_column("users", "referral_rewarded")
    op.drop_index("ix_users_referred_by_id", table_name="users")
    op.drop_column("users", "referred_by_id")

    for column in ("disable_notification", "protect_content", "disable_link_preview"):
        op.drop_column("broadcast_campaigns", column)

    for table in _MEDIA_TABLES:
        op.add_column(table, sa.Column("photo_path", sa.String(), nullable=True))
        op.execute(
            f"UPDATE {table} SET photo_path = photo_paths ->> 0 "
            "WHERE json_array_length(photo_paths) > 0"
        )
        op.drop_column(table, "photo_paths")

    op.rename_table("pro_settings", "tag_feature_settings")
    op.alter_column("users", "pro_expires_at", new_column_name="tag_feature_expires_at")
