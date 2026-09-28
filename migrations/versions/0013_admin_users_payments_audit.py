"""Admin section: user display info, payments, audit log

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("charge_id", sa.String(128), nullable=True, unique=True),
        _created_at(),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])

    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("details", sa.String(255), nullable=False, server_default=""),
        _created_at(),
    )
    op.create_index(
        "ix_admin_audit_log_admin_telegram_id", "admin_audit_log", ["admin_telegram_id"]
    )
    op.create_index("ix_admin_audit_log_target_user_id", "admin_audit_log", ["target_user_id"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_log_target_user_id", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_admin_telegram_id", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "last_seen_at")
    op.drop_column("users", "username")
    op.drop_column("users", "first_name")
