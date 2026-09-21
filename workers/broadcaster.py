import asyncio
import random
from datetime import UTC, datetime

from pyrogram import Client
from pyrogram.errors import FloodWait
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from workers.spintax import render_spintax

MIN_DELAY_SECONDS = 20
MAX_DELAY_SECONDS = 45


def _with_signature(text: str) -> str:
    return f"{text}\n\nОтправлено через @{settings.bot_username}"


async def run_campaign(client: Client, db: AsyncSession, campaign: BroadcastCampaign) -> None:
    """Sends `campaign.text_template` to every chat in `target_chat_ids`.

    Per AGENTS.md 4.3: random 20-45s delay between chats, FloodWait is
    always caught and slept out (never retried immediately), spintax is
    resolved per-recipient, and every message carries the bot signature.
    """
    for chat_id in campaign.target_chat_ids:
        text = _with_signature(render_spintax(campaign.text_template))

        while True:
            try:
                if campaign.photo_path:
                    await client.send_photo(chat_id, campaign.photo_path, caption=text)
                else:
                    await client.send_message(chat_id, text)
                log = BroadcastLog(
                    campaign_id=campaign.id,
                    chat_id=chat_id,
                    sent_at=datetime.now(UTC),
                    status="success",
                )
            except FloodWait as exc:
                await asyncio.sleep(exc.value + 5)
                continue
            except Exception as exc:  # noqa: BLE001 - log and move on to the next chat
                log = BroadcastLog(
                    campaign_id=campaign.id,
                    chat_id=chat_id,
                    sent_at=datetime.now(UTC),
                    status="error",
                    error_message=str(exc),
                )
            break

        db.add(log)
        await db.commit()
        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
