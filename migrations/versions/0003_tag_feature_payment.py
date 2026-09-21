"""paid access for the tag-random-users broadcast feature

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21

"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tag_feature_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tag_feature_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stars_price", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
    )
    op.execute(
        "INSERT INTO tag_feature_settings (id, stars_price, duration_days) VALUES (1, 50, 30)"
    )


def downgrade() -> None:
    op.drop_table("tag_feature_settings")
    op.drop_column("users", "tag_feature_expires_at")
