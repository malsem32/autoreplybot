import asyncio
import random
from datetime import UTC, datetime

from pyrogram import Client
from pyrogram.errors import FloodWait
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import tag_feature
from workers.spintax import render_spintax
from workers.targets import resolve_target

MIN_DELAY_SECONDS = 20
MAX_DELAY_SECONDS = 45

# Placeholder character a user can drop into `text_template`; when
# `tag_random_users` is on it's replaced per-chat with mentions of 5
# random chat members, otherwise it's stripped out.
TAG_PLACEHOLDER = "​"
TAG_COUNT = 5


def _with_signature(text: str) -> str:
    return f"{text}\n\nОтправлено через @{settings.bot_username}"


async def _random_member_mentions(client: Client, chat_id: int) -> str:
    members = []
    async for member in client.get_chat_members(chat_id):
        user = member.user
        if user is None or user.is_bot or user.is_deleted:
            continue
        members.append(user)

    if not members:
        return ""

    chosen = random.sample(members, k=min(TAG_COUNT, len(members)))
    # Link text is the zero-width space itself, not the member's name: the
    # mentions must stay invisible in the rendered message (see AGENTS.md
    # 4.13/4.8) while still notifying the tagged member.
    return "".join(f"[{TAG_PLACEHOLDER}](tg://user?id={user.id})" for user in chosen)


async def _resolve_tag_placeholder(
    client: Client, chat_id: int, text: str, tag_random_users: bool
) -> str:
    if TAG_PLACEHOLDER not in text:
        return text
    mentions = ""
    if tag_random_users:
        try:
            mentions = await _random_member_mentions(client, chat_id)
        except Exception:  # noqa: BLE001 - fall back to stripping the placeholder
            mentions = ""
    return text.replace(TAG_PLACEHOLDER, mentions)


async def _has_tag_feature_access(db: AsyncSession, campaign: BroadcastCampaign) -> bool:
    """Re-checked on every run (not just at campaign creation) so a
    recurring campaign stops tagging for free once its purchase expires."""
    if not campaign.tag_random_users:
        return False
    user = await db.scalar(
        select(User)
        .join(TelegramAccount, TelegramAccount.user_id == User.id)
        .where(TelegramAccount.id == campaign.account_id)
    )
    return user is not None and tag_feature.has_access(user)


async def run_campaign(client: Client, db: AsyncSession, campaign: BroadcastCampaign) -> None:
    """Sends `campaign.text_template` to every chat in `target_chats`.

    Per AGENTS.md 4.3: random 20-45s delay between chats, FloodWait is
    always caught and slept out (never retried immediately), spintax is
    resolved per-recipient, and every message carries the bot signature.
    """
    tag_enabled = await _has_tag_feature_access(db, campaign)
    for raw_target in campaign.target_chats:
        base_text = _with_signature(render_spintax(campaign.text_template))

        while True:
            try:
                chat_id = await resolve_target(client, raw_target)
                text = await _resolve_tag_placeholder(client, chat_id, base_text, tag_enabled)
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
                    chat_id=0,
                    sent_at=datetime.now(UTC),
                    status="error",
                    error_message=f"{raw_target}: {exc}",
                )
            break

        db.add(log)
        await db.commit()
        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
