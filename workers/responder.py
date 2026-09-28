import asyncio
import logging
from datetime import UTC, datetime, timedelta

from pyrogram import Client, enums, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from redis.asyncio import Redis
from sqlalchemy import select

from backend.core.config import settings
from backend.core.telegram_errors import flood_wait_seconds
from backend.db.session import SessionLocal
from backend.models.autoresponder_rule import AutoresponderEvent, AutoresponderRule
from backend.models.broadcast import FloodWaitEvent
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro
from backend.services.schedule import is_within_schedule
from workers.notify import esc, notify_user
from workers.sending import SendOptions, send_content
from workers.spintax import render_spintax

logger = logging.getLogger(__name__)

_redis = Redis.from_url(settings.redis_url)

# How far back to look for the owner's own messages / earlier messages.
HISTORY_LIMIT = 30
NOTIFY_PREVIEW_CHARS = 300


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


def _naive_local(value: datetime) -> datetime:
    # Pyrogram message dates are naive local time; normalize aware values to that.
    return value if value.tzinfo is None else value.astimezone().replace(tzinfo=None)


def owner_recently_active(history: list[Message], minutes: int, now: datetime) -> bool:
    """True if the owner sent something in this chat within `minutes`."""
    if minutes <= 0:
        return False
    border = _naive_local(now) - timedelta(minutes=minutes)
    return any(m.outgoing and m.date and _naive_local(m.date) >= border for m in history)


def is_new_contact(history: list[Message], current_message_id: int) -> bool:
    """True if nothing but the incoming message exists in the chat."""
    return all(m.id == current_message_id for m in history)


class _ChatContext:
    """Lazily fetched chat history, shared by all rules checked for one
    incoming message (one API call at most)."""

    def __init__(self, client: Client, chat_id: int) -> None:
        self._client = client
        self._chat_id = chat_id
        self._history: list[Message] | None = None

    async def history(self) -> list[Message]:
        if self._history is None:
            self._history = [
                m async for m in self._client.get_chat_history(self._chat_id, limit=HISTORY_LIMIT)
            ]
        return self._history


async def _rule_applies(
    rule: AutoresponderRule, has_pro: bool, message: Message, ctx: _ChatContext
) -> bool:
    """Pro filters (AGENTS.md 4.13) apply only while the owner has Pro;
    after expiry the rule behaves like a plain free rule."""
    if not has_pro:
        return True
    if rule.schedule_enabled and not is_within_schedule(
        rule.schedule_days, rule.schedule_start, rule.schedule_end, rule.timezone
    ):
        return False
    if rule.new_contacts_only and not is_new_contact(await ctx.history(), message.id):
        return False
    if rule.skip_if_owner_active_minutes and owner_recently_active(
        await ctx.history(), rule.skip_if_owner_active_minutes, datetime.now(UTC)
    ):
        return False
    return True


async def _load(account_id: int) -> tuple[list[AutoresponderRule], User | None]:
    async with SessionLocal() as db:
        result = await db.execute(
            select(AutoresponderRule)
            .where(
                AutoresponderRule.account_id == account_id,
                AutoresponderRule.is_enabled.is_(True),
            )
            .order_by(AutoresponderRule.id)
        )
        owner = await db.scalar(
            select(User)
            .join(TelegramAccount, TelegramAccount.user_id == User.id)
            .where(TelegramAccount.id == account_id)
        )
        return list(result.scalars().all()), owner


async def _record(event: AutoresponderEvent | FloodWaitEvent) -> None:
    try:
        async with SessionLocal() as db:
            db.add(event)
            await db.commit()
    except Exception:  # noqa: BLE001 - stats must never break replying
        logger.warning("failed to record %s", type(event).__name__)


async def _type_for(client: Client, chat_id: int, seconds: int) -> None:
    """Shows "typing…" for `seconds` (the action expires after ~5s, so it is
    refreshed)."""
    remaining = float(seconds)
    while remaining > 0:
        try:
            await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
        except Exception:  # noqa: BLE001 - cosmetic only
            pass
        step = min(4.0, remaining)
        await asyncio.sleep(step)
        remaining -= step


def _notification_text(message: Message, rule: AutoresponderRule) -> str:
    sender = message.from_user
    assert sender is not None  # bots and anonymous senders are filtered out earlier
    name = esc(" ".join(p for p in (sender.first_name, sender.last_name) if p) or "Без имени")
    handle = f" (@{esc(sender.username)})" if sender.username else ""
    incoming = message.text or message.caption or "[медиа]"
    if len(incoming) > NOTIFY_PREVIEW_CHARS:
        incoming = incoming[:NOTIFY_PREVIEW_CHARS] + "…"
    trigger = "любое сообщение" if rule.trigger_type == "all" else ", ".join(rule.keywords[:5])
    return (
        f"💬 <b>Новое обращение</b> от {name}{handle}\n\n"
        f"<blockquote>{esc(incoming)}</blockquote>\n"
        f"Автопилот ответил по правилу «{esc(trigger)}»."
    )


def register_responder(client: Client, account_id: int) -> None:
    """Wires private-message autoreply for one account's client.

    Rules are re-read from the DB on every incoming message (not captured
    once at registration) so edits made in the Mini App take effect without
    restarting the worker. Per AGENTS.md 4.3: ignores bot senders and
    enforces per-peer cooldown (rule.cooldown_seconds, minimum 1h —
    validated at the API layer). The first enabled rule that matches and
    passes its Pro filters answers.
    """

    @client.on_message(filters.private & filters.incoming)  # type: ignore[misc]
    async def _handle(_: Client, message: Message) -> None:
        if message.from_user is None or message.from_user.is_bot:
            return

        peer_id = message.from_user.id
        if await _on_cooldown(account_id, peer_id):
            return

        chat_id = (message.chat.id if message.chat else None) or peer_id
        incoming = message.text or message.caption or ""
        rules, owner = await _load(account_id)
        has_pro = owner is not None and pro.has_access(owner)
        ctx = _ChatContext(client, chat_id)

        rule = None
        for candidate in rules:
            if not _matches(candidate, incoming):
                continue
            try:
                if await _rule_applies(candidate, has_pro, message, ctx):
                    rule = candidate
                    break
            except Exception:  # noqa: BLE001 - a failed history lookup skips the filter
                logger.warning("autoreply filter check failed for account %s", account_id)
                rule = candidate
                break
        if rule is None:
            return

        # Cooldown is set before sending so a burst of messages from one peer
        # can't trigger several replies while the first is still in flight.
        await _set_cooldown(account_id, peer_id, rule.cooldown_seconds)
        text = render_spintax(rule.response_text)
        photo_paths = list(rule.photo_paths or [])[
            : pro.PRO_MAX_PHOTOS if has_pro else pro.FREE_MAX_PHOTOS
        ]

        if has_pro and rule.typing_delay_seconds:
            await _type_for(client, chat_id, rule.typing_delay_seconds)

        for _attempt in range(2):
            try:
                await send_content(
                    client, chat_id, text, photo_paths, SendOptions(reply_to_message_id=message.id)
                )
                break
            except FloodWait as exc:
                # AGENTS.md 4.3: sleep it out, never retry head-on.
                wait = flood_wait_seconds(exc)
                await _record(
                    FloodWaitEvent(account_id=account_id, seconds=wait, source="autoreply")
                )
                await asyncio.sleep(wait + 5)
            except Exception:  # noqa: BLE001 - one failed reply must not kill the handler
                logger.exception("autoreply failed for account %s", account_id)
                return
        else:
            return

        await _record(AutoresponderEvent(rule_id=rule.id, account_id=account_id))
        if has_pro and rule.notify_owner and owner is not None:
            await notify_user(owner.telegram_id, _notification_text(message, rule))
