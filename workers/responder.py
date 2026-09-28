import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from redis.asyncio import Redis
from sqlalchemy import select

from backend.core.config import settings
from backend.core.telegram_errors import flood_wait_seconds
from backend.db.session import SessionLocal
from backend.models.autoresponder_rule import AutoresponderRule
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro
from workers.sending import SendOptions, send_content
from workers.spintax import render_spintax

logger = logging.getLogger(__name__)

_redis = Redis.from_url(settings.redis_url)


def _cooldown_key(account_id: int, peer_id: int) -> str:
    return f"autoresponder:cooldown:{account_id}:{peer_id}"


async def _on_cooldown(account_id: int, peer_id: int) -> bool:
    return await _redis.exists(_cooldown_key(account_id, peer_id)) == 1


async def _set_cooldown(account_id: int, peer_id: int, seconds: int) -> None:
    await _redis.set(_cooldown_key(account_id, peer_id), "1", ex=seconds)


def _matches(rule: AutoresponderRule, text: str) -> bool:
    if rule.trigger_type == "all":
        return True
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in rule.keywords)


async def _load_active_rules(account_id: int) -> list[AutoresponderRule]:
    async with SessionLocal() as db:
        result = await db.execute(
            select(AutoresponderRule).where(
                AutoresponderRule.account_id == account_id,
                AutoresponderRule.is_enabled.is_(True),
            )
        )
        return list(result.scalars().all())


async def _owner_max_photos(account_id: int) -> int:
    """Albums in replies are Pro; re-checked at send time so they shrink to
    the free limit once the subscription expires (AGENTS.md 4.13)."""
    async with SessionLocal() as db:
        user = await db.scalar(
            select(User)
            .join(TelegramAccount, TelegramAccount.user_id == User.id)
            .where(TelegramAccount.id == account_id)
        )
    return pro.max_photos(user) if user is not None else pro.FREE_MAX_PHOTOS


def register_responder(client: Client, account_id: int) -> None:
    """Wires private-message autoreply for one account's client.

    Rules are re-read from the DB on every incoming message (not captured
    once at registration) so edits made in the Mini App take effect without
    restarting the worker. Per AGENTS.md 4.3: ignores bot senders and
    enforces per-peer cooldown (rule.cooldown_seconds, minimum 1h —
    validated at the API layer).
    """

    @client.on_message(filters.private & filters.incoming)  # type: ignore[misc]
    async def _handle(_: Client, message: Message) -> None:
        if message.from_user is None or message.from_user.is_bot:
            return

        peer_id = message.from_user.id
        if await _on_cooldown(account_id, peer_id):
            return

        text = message.text or message.caption or ""
        rules = await _load_active_rules(account_id)
        rule = next((r for r in rules if _matches(r, text)), None)
        if rule is None:
            return

        # Cooldown is set before sending so a burst of messages from one peer
        # can't trigger several replies while the first is still in flight.
        await _set_cooldown(account_id, peer_id, rule.cooldown_seconds)
        text = render_spintax(rule.response_text)
        photo_paths = list(rule.photo_paths or [])
        if len(photo_paths) > pro.FREE_MAX_PHOTOS:
            photo_paths = photo_paths[: await _owner_max_photos(account_id)]
        for _attempt in range(2):
            try:
                await send_content(
                    client,
                    (message.chat.id if message.chat else None) or peer_id,
                    text,
                    photo_paths,
                    SendOptions(reply_to_message_id=message.id),
                )
                return
            except FloodWait as exc:
                # AGENTS.md 4.3: sleep it out, never retry head-on.
                await asyncio.sleep(flood_wait_seconds(exc) + 5)
            except Exception:  # noqa: BLE001 - one failed reply must not kill the handler
                logger.exception("autoreply failed for account %s", account_id)
                return
