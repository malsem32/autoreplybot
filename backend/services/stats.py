from datetime import UTC, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User


class DashboardStats(BaseModel):
    users_total: int
    users_new_7d: int
    accounts_total: int
    accounts_active: int
    campaigns_active: int
    campaigns_paused: int
    campaigns_finished: int
    messages_sent_24h: int
    messages_failed_24h: int


async def collect_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Aggregates for the admin dashboard, per AGENTS.md 4.6. Computed as SQL
    aggregates, not by paging through BroadcastLog in Python."""
    since_7d = datetime.now(UTC) - timedelta(days=7)
    since_24h = datetime.now(UTC) - timedelta(hours=24)

    users_total = await db.scalar(select(func.count()).select_from(User))
    users_new_7d = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= since_7d)
    )

    accounts_total = await db.scalar(select(func.count()).select_from(TelegramAccount))
    accounts_active = await db.scalar(
        select(func.count()).select_from(TelegramAccount).where(TelegramAccount.is_active.is_(True))
    )

    campaign_status_counts = dict(
        (
            await db.execute(
                select(BroadcastCampaign.status, func.count()).group_by(BroadcastCampaign.status)
            )
        ).all()
    )

    messages_sent_24h = await db.scalar(
        select(func.count())
        .select_from(BroadcastLog)
        .where(BroadcastLog.status == "success", BroadcastLog.sent_at >= since_24h)
    )
    messages_failed_24h = await db.scalar(
        select(func.count())
        .select_from(BroadcastLog)
        .where(BroadcastLog.status == "error", BroadcastLog.sent_at >= since_24h)
    )

    return DashboardStats(
        users_total=users_total or 0,
        users_new_7d=users_new_7d or 0,
        accounts_total=accounts_total or 0,
        accounts_active=accounts_active or 0,
        campaigns_active=campaign_status_counts.get("active", 0),
        campaigns_paused=campaign_status_counts.get("paused", 0),
        campaigns_finished=campaign_status_counts.get("finished", 0),
        messages_sent_24h=messages_sent_24h or 0,
        messages_failed_24h=messages_failed_24h or 0,
    )
