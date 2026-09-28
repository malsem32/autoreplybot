import asyncio
import random
from datetime import UTC, datetime

from pyrogram import Client
from pyrogram.errors import FloodWait
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.telegram_errors import flood_wait_seconds
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro
from workers.sending import SendOptions, send_content
from workers.spintax import render_spintax
from workers.targets import resolve_target

MIN_DELAY_SECONDS = 20
MAX_DELAY_SECONDS = 45

# Zero-width space used as the (invisible) link text for each tag mention.
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
    return "".join(f'<a href="tg://user?id={user.id}">{TAG_PLACEHOLDER}</a>' for user in chosen)


async def _append_random_tags(
    client: Client, chat_id: int, text: str, tag_random_users: bool
) -> str:
    """Appends 5 invisible mentions of random chat members to the end of
    `text` when the campaign has `tag_random_users` on; no placeholder or
    manual insertion needed."""
    if not tag_random_users:
        return text
    try:
        mentions = await _random_member_mentions(client, chat_id)
    except Exception:  # noqa: BLE001 - send the message untagged rather than not at all
        mentions = ""
    return text + mentions


async def _owner_has_pro(db: AsyncSession, campaign: BroadcastCampaign) -> bool:
    """Re-checked on every run (not just at campaign creation) so a
    recurring campaign stops using Pro features once the purchase expires
    (AGENTS.md 4.13)."""
    user = await db.scalar(
        select(User)
        .join(TelegramAccount, TelegramAccount.user_id == User.id)
        .where(TelegramAccount.id == campaign.account_id)
    )
    return user is not None and pro.has_access(user)


async def run_campaign(client: Client, db: AsyncSession, campaign: BroadcastCampaign) -> None:
    """Sends `campaign.text_template` to every chat in `target_chats`.

    Per AGENTS.md 4.3: random 20-45s delay between chats, FloodWait is
    always caught and slept out (never retried immediately), spintax is
    resolved per-recipient, and every message carries the bot signature.
    """
    is_pro = await _owner_has_pro(db, campaign)
    tag_enabled = campaign.tag_random_users and is_pro
    # Re-checked here too: an album saved while Pro was active shrinks to
    # the free limit once the subscription expires.
    max_photos = pro.PRO_MAX_PHOTOS if is_pro else pro.FREE_MAX_PHOTOS
    photo_paths = list(campaign.photo_paths or [])
    for index, raw_target in enumerate(campaign.target_chats):
        if index > 0:
            # Pausing/deleting in the Mini App takes effect mid-run, not
            # only after the whole (possibly long) target list is done.
            try:
                await db.refresh(campaign)
            except InvalidRequestError:  # campaign was deleted meanwhile
                return
            if campaign.status != "active":
                return
        base_text = _with_signature(render_spintax(campaign.text_template))

        while True:
            try:
                chat_id = await resolve_target(client, raw_target)
                text = await _append_random_tags(client, chat_id, base_text, tag_enabled)
                await send_content(
                    client,
                    chat_id,
                    text,
                    photo_paths[:max_photos],
                    SendOptions(
                        disable_notification=campaign.disable_notification,
                        protect_content=campaign.protect_content and is_pro,
                        disable_link_preview=campaign.disable_link_preview,
                    ),
                )
                log = BroadcastLog(
                    campaign_id=campaign.id,
                    chat_id=chat_id,
                    sent_at=datetime.now(UTC),
                    status="success",
                )
            except FloodWait as exc:
                await asyncio.sleep(flood_wait_seconds(exc) + 5)
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
        if index < len(campaign.target_chats) - 1:
            await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
