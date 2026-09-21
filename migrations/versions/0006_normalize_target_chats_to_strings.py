"""normalize broadcast_campaigns.target_chats elements to strings

0002 renamed target_chat_ids -> target_chats but only renamed the column;
rows created before it still hold JSON numbers (the old int chat ids), while
BroadcastCampaignOut now declares `target_chats: list[str]` — Pydantic
rejects those rows on read, breaking GET /api/broadcasts/{account_id}/campaigns
with a 500 for any account with pre-existing campaigns.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-21

"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE broadcast_campaigns
        SET target_chats = (
            SELECT COALESCE(json_agg(to_json(elem #>> '{}')), '[]'::json)
            FROM json_array_elements(target_chats) AS elem
        )
        WHERE json_typeof(target_chats) = 'array';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE broadcast_campaigns
        SET target_chats = (
            SELECT COALESCE(
                json_agg(
                    CASE
                        WHEN (elem #>> '{}') ~ '^-?[0-9]+$'
                            THEN to_json((elem #>> '{}')::bigint)
                        ELSE elem
                    END
                ),
                '[]'::json
            )
            FROM json_array_elements(target_chats) AS elem
        )
        WHERE json_typeof(target_chats) = 'array';
        """
    )
