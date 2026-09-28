from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.admin import Payment
from backend.models.autoresponder_rule import AutoresponderEvent
from backend.models.broadcast import BroadcastCampaign, BroadcastLog, FloodWaitEvent
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User


class DashboardStats(BaseModel):
    users_total: int
    users_new_1d: int
    users_new_7d: int
    users_new_30d: int
    pro_active: int
    accounts_total: int
    accounts_active: int
    campaigns_active: int
    campaigns_paused: int
    campaigns_finished: int
    messages_sent_24h: int
    messages_failed_24h: int
    autoreplies_24h: int
    autoreplies_7d: int
    flood_waits_24h: int
    flood_wait_seconds_24h: int


async def collect_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Aggregates for the admin dashboard, per AGENTS.md 4.6. Computed as SQL
    aggregates, not by paging through logs in Python."""
    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    async def count(model: type, *where: ColumnElement[bool]) -> int:
        return await db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    campaign_status_counts: dict[str, int] = dict(
        (
            await db.execute(
                select(BroadcastCampaign.status, func.count()).group_by(BroadcastCampaign.status)
            )
        )
        .tuples()
        .all()
    )
    flood_seconds = await db.scalar(
        select(func.coalesce(func.sum(FloodWaitEvent.seconds), 0)).where(
            FloodWaitEvent.created_at >= since_24h
        )
    )

    return DashboardStats(
        users_total=await count(User),
        users_new_1d=await count(User, User.created_at >= since_24h),
        users_new_7d=await count(User, User.created_at >= since_7d),
        users_new_30d=await count(User, User.created_at >= since_30d),
        pro_active=await count(User, User.pro_expires_at > now),
        accounts_total=await count(TelegramAccount),
        accounts_active=await count(TelegramAccount, TelegramAccount.is_active.is_(True)),
        campaigns_active=campaign_status_counts.get("active", 0),
        campaigns_paused=campaign_status_counts.get("paused", 0),
        campaigns_finished=campaign_status_counts.get("finished", 0),
        messages_sent_24h=await count(
            BroadcastLog, BroadcastLog.status == "success", BroadcastLog.sent_at >= since_24h
        ),
        messages_failed_24h=await count(
            BroadcastLog, BroadcastLog.status == "error", BroadcastLog.sent_at >= since_24h
        ),
        autoreplies_24h=await count(AutoresponderEvent, AutoresponderEvent.created_at >= since_24h),
        autoreplies_7d=await count(AutoresponderEvent, AutoresponderEvent.created_at >= since_7d),
        flood_waits_24h=await count(FloodWaitEvent, FloodWaitEvent.created_at >= since_24h),
        flood_wait_seconds_24h=int(flood_seconds or 0),
    )


class Timeseries(BaseModel):
    """Daily series for the admin charts (UTC days, oldest first)."""

    days: list[str]
    users: list[int]
    autoreplies: list[int]
    sent: list[int]
    failed: list[int]
    stars: list[int]
    stars_30d: int
    payments_30d: int
    stars_total: int


async def collect_timeseries(db: AsyncSession, days: int = 30) -> Timeseries:
    """Per-day SQL aggregates (GROUP BY date) — never a Python pass over logs."""
    today = datetime.now(UTC).date()
    start = today - timedelta(days=days - 1)
    since = datetime(start.year, start.month, start.day, tzinfo=UTC)
    labels = [(start + timedelta(days=i)).isoformat() for i in range(days)]

    async def per_day(column: Any, value: Any = None, *where: ColumnElement[bool]) -> list[int]:
        day = func.date(column)
        agg = func.count() if value is None else func.coalesce(func.sum(value), 0)
        rows = await db.execute(select(day, agg).where(column >= since, *where).group_by(day))
        by_day = {str(d)[:10]: int(n or 0) for d, n in rows.tuples().all()}
        return [by_day.get(label, 0) for label in labels]

    stars = await per_day(Payment.created_at, Payment.stars)
    return Timeseries(
        days=labels,
        users=await per_day(User.created_at),
        autoreplies=await per_day(AutoresponderEvent.created_at),
        sent=await per_day(BroadcastLog.sent_at, None, BroadcastLog.status == "success"),
        failed=await per_day(BroadcastLog.sent_at, None, BroadcastLog.status == "error"),
        stars=stars,
        stars_30d=sum(stars),
        payments_30d=await db.scalar(
            select(func.count()).select_from(Payment).where(Payment.created_at >= since)
        )
        or 0,
        stars_total=await db.scalar(select(func.coalesce(func.sum(Payment.stars), 0))) or 0,
    )
