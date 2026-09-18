from pyrogram import Client, filters
from pyrogram.types import Message
from redis.asyncio import Redis

from backend.core.config import settings
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


def register_responder(client: Client, account_id: int, rules: list[AutoresponderRule]) -> None:
    """Wires private-message autoreply for one account's client.

    Per AGENTS.md 4.3: ignores bot senders and enforces per-peer cooldown
    (rule.cooldown_seconds, minimum 1h — validated at the API layer).
    """

    @client.on_message(filters.private & filters.incoming)
    async def _handle(_: Client, message: Message) -> None:
        if message.from_user is None or message.from_user.is_bot:
            return

        peer_id = message.from_user.id
        if await _on_cooldown(account_id, peer_id):
            return

        text = message.text or message.caption or ""
        active_rules = [r for r in rules if r.is_enabled]
        rule = next((r for r in active_rules if _matches(r, text)), None)
        if rule is None:
            return

        await message.reply(rule.response_text)
        await _set_cooldown(account_id, peer_id, rule.cooldown_seconds)
