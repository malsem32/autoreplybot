from datetime import UTC, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
