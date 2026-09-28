"""Quick phrases (AGENTS.md 4.17): the owner sends `!shortcut` from any of
their devices and the worker swaps that message for the saved text.

This is the owner's own message edited in place (or, with photos, replaced),
one action per message they typed — not a broadcast, so no signature and
no anti-ban delay; FloodWait is still slept out, never retried head-on."""

import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from sqlalchemy import select

from backend.core.telegram_errors import flood_wait_seconds
from backend.db.session import SessionLocal
from backend.models.broadcast import FloodWaitEvent
from backend.models.snippet import Snippet
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro
from backend.services.snippets import FREE_MAX_SNIPPETS, parse_trigger
from workers.sending import SendOptions, send_content
from workers.spintax import render_spintax

logger = logging.getLogger(__name__)

# Separate handler group: the autoresponder's incoming-message handler must
# keep receiving updates regardless of this one.
SNIPPET_HANDLER_GROUP = 1


async def _load(account_id: int, shortcut: str) -> tuple[Snippet | None, bool]:
    """The snippet for `shortcut` if it is usable on the owner's plan: without
    Pro only the first FREE_MAX_SNIPPETS (by creation) work."""
    async with SessionLocal() as db:
        owner = await db.scalar(
            select(User)
            .join(TelegramAccount, TelegramAccount.user_id == User.id)
            .where(TelegramAccount.id == account_id)
        )
        has_pro = owner is not None and pro.has_access(owner)
        query = select(Snippet).where(Snippet.account_id == account_id).order_by(Snippet.id)
        if not has_pro:
            query = query.limit(FREE_MAX_SNIPPETS)
        snippets = (await db.execute(query)).scalars().all()
        return next((s for s in snippets if s.shortcut == shortcut), None), has_pro


async def expand(client: Client, account_id: int, message: Message) -> bool:
    shortcut = parse_trigger(message.text)
    if shortcut is None or message.chat is None or message.chat.id is None:
        return False
    chat_id = message.chat.id
    snippet, has_pro = await _load(account_id, shortcut)
    if snippet is None:
        return False
    text = render_spintax(snippet.text)
    photos = list(snippet.photo_paths or [])[
        : pro.PRO_MAX_PHOTOS if has_pro else pro.FREE_MAX_PHOTOS
    ]
    for _attempt in range(2):
        try:
            if photos:
                # A text message can't become a photo: send the snippet in its
                # place (keeping what it replied to) and remove the trigger.
                await send_content(
                    client,
                    chat_id,
                    text,
                    photos,
                    SendOptions(reply_to_message_id=message.reply_to_message_id),
                )
                await message.delete()
            else:
                await message.edit_text(text)
            return True
        except FloodWait as exc:
            wait = flood_wait_seconds(exc)
            async with SessionLocal() as db:
                db.add(FloodWaitEvent(account_id=account_id, seconds=wait, source="snippet"))
                await db.commit()
            await asyncio.sleep(wait + 5)
        except Exception:  # noqa: BLE001 - a failed expansion leaves the "!word" as is
            logger.warning("snippet expansion failed for account %s", account_id)
            return False
    return False


def register_snippets(client: Client, account_id: int) -> None:
    @client.on_message(  # type: ignore[misc]
        filters.outgoing & filters.text & filters.regex(r"^!"), group=SNIPPET_HANDLER_GROUP
    )
    async def _handle(_: Client, message: Message) -> None:
        await expand(client, account_id, message)
