"""Scheduled bot messages: the "Pro ends in 3 days" reminder (everyone) and
the weekly activity digest (Pro, opt-out in the Mini App profile)."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.timeutil import as_utc
from backend.db.session import SessionLocal
from backend.models.autoresponder_rule import AutoresponderEvent
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.lead import Lead
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro
from backend.services.bot_api import send_message

logger = logging.getLogger(__name__)

REMIND_BEFORE = timedelta(days=3)
DIGEST_WEEKDAY = 0  # Monday
DIGEST_HOUR_UTC = 7  # 10:00 Moscow
PRO_MENU_BUTTON = {"inline_keyboard": [[{"text": "⭐️ Продлить Pro", "callback_data": "pro_menu"}]]}


def reminder_text(expires_at: datetime, now: datetime) -> str:
    days = max(1, round((as_utc(expires_at) - now).total_seconds() / 86400))  # type: ignore[operator]
    word = "день" if days == 1 else "дня"
    return (
        f"⏳ <b>Автопилот Pro закончится через {days} {word}</b>\n\n"
        "После этого перестанут работать расписание и умные автоответы, уведомления, "
        "статистика рассылок и альбомы. Продлите заранее — новые дни добавятся к текущему сроку."
    )


def digest_text(stats: dict[str, int]) -> str | None:
    """None when there was no activity at all (don't spam empty digests)."""
    if not any(stats.values()):
        return None
    total = stats["sent"] + stats["failed"]
    rate = f" ({round(stats['sent'] / total * 100)}% доставлено)" if total else ""
    lines = [
        "📊 <b>Автопилот за неделю</b>",
        "",
        f"💬 Автоответов: {stats['autoreplies']}",
        f"👤 Новых обращений: {stats['new_leads']}",
    ]
    if stats["open_leads"]:
        lines.append(f"📥 Ждут ответа: {stats['open_leads']}")
    lines.append(f"📣 Сообщений в рассылках: {stats['sent']}{rate}")
    return "\n".join(lines)


async def _user_stats(db: AsyncSession, user: User, since: datetime) -> dict[str, int]:
    account_ids = list(
        (
            await db.execute(select(TelegramAccount.id).where(TelegramAccount.user_id == user.id))
        ).scalars()
    )
    if not account_ids:
        return {"autoreplies": 0, "new_leads": 0, "open_leads": 0, "sent": 0, "failed": 0}

    async def count(model: type, *where: object) -> int:
        return await db.scalar(select(func.count()).select_from(model).where(*where)) or 0  # type: ignore[arg-type]

    log_rows = dict(
        (
            await db.execute(
                select(BroadcastLog.status, func.count())
                .join(BroadcastCampaign, BroadcastCampaign.id == BroadcastLog.campaign_id)
                .where(BroadcastCampaign.account_id.in_(account_ids), BroadcastLog.sent_at >= since)
                .group_by(BroadcastLog.status)
            )
        )
        .tuples()
        .all()
    )
    return {
        "autoreplies": await count(
            AutoresponderEvent,
            AutoresponderEvent.account_id.in_(account_ids),
            AutoresponderEvent.created_at >= since,
        ),
        "new_leads": await count(Lead, Lead.account_id.in_(account_ids), Lead.created_at >= since),
        "open_leads": await count(Lead, Lead.account_id.in_(account_ids), Lead.status == "new"),
        "sent": log_rows.get("success", 0),
        "failed": log_rows.get("error", 0),
    }


async def send_pro_reminders(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    sent = 0
    async with SessionLocal() as db:
        users = (
            await db.execute(
                select(User).where(
                    User.pro_expires_at > now, User.pro_expires_at <= now + REMIND_BEFORE
                )
            )
        ).scalars()
        for user in users:
            if pro.is_admin(user) or as_utc(user.pro_reminder_for) == as_utc(user.pro_expires_at):
                continue
            assert user.pro_expires_at is not None
            await send_message(
                user.telegram_id, reminder_text(user.pro_expires_at, now), PRO_MENU_BUTTON
            )
            user.pro_reminder_for = user.pro_expires_at
            sent += 1
        await db.commit()
    return sent


async def send_weekly_digests(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    if now.weekday() != DIGEST_WEEKDAY or now.hour < DIGEST_HOUR_UTC:
        return 0
    since = now - timedelta(days=7)
    sent = 0
    async with SessionLocal() as db:
        users = (
            await db.execute(
                select(User).where(
                    User.weekly_digest.is_(True),
                    or_(
                        User.digest_sent_at.is_(None), User.digest_sent_at < now - timedelta(days=6)
                    ),
                )
            )
        ).scalars()
        for user in users:
            if not pro.has_access(user):
                continue
            user.digest_sent_at = now
            text = digest_text(await _user_stats(db, user, since))
            if text:
                await send_message(user.telegram_id, text)
                sent += 1
        await db.commit()
    return sent
