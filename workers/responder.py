from pyrogram import Client, filters
from pyrogram.types import Message
from redis.asyncio import Redis
from sqlalchemy import select

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.autoresponder_rule import AutoresponderRule

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


def register_responder(client: Client, account_id: int) -> None:
    """Wires private-message autoreply for one account's client.

    Rules are re-read from the DB on every incoming message (not captured
    once at registration) so edits made in the Mini App take effect without
    restarting the worker. Per AGENTS.md 4.3: ignores bot senders and
    enforces per-peer cooldown (rule.cooldown_seconds, minimum 1h —
    validated at the API layer).
    """

    @client.on_message(filters.private & filters.incoming)
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

        if rule.photo_path:
            await message.reply_photo(rule.photo_path, caption=rule.response_text)
        else:
            await message.reply(rule.response_text)
        await _set_cooldown(account_id, peer_id, rule.cooldown_seconds)
