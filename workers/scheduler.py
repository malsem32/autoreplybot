import asyncio
import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from backend.core.logging import configure_logging
from backend.db.session import SessionLocal
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from workers.broadcaster import run_campaign
from workers.client_manager import client_manager

logger = logging.getLogger(__name__)


async def _is_due(db, campaign: BroadcastCampaign) -> bool:
    last_sent_at = await db.scalar(
        select(BroadcastLog.sent_at)
        .where(BroadcastLog.campaign_id == campaign.id)
        .order_by(BroadcastLog.sent_at.desc())
        .limit(1)
    )
    if last_sent_at is None:
        return True
    return datetime.now(UTC) - last_sent_at >= timedelta(minutes=campaign.interval_minutes)


async def dispatch_due_campaigns() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(BroadcastCampaign, TelegramAccount)
            .join(TelegramAccount, BroadcastCampaign.account_id == TelegramAccount.id)
            .where(BroadcastCampaign.status == "active", TelegramAccount.is_active.is_(True))
        )
        for campaign, account in result.all():
            if not await _is_due(db, campaign):
                continue

            client = await client_manager.start(account.id, account.encrypted_session)
            try:
                await run_campaign(client, db, campaign)
            except Exception:
                logger.exception("campaign %s failed", campaign.id)


async def main() -> None:
    configure_logging()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(dispatch_due_campaigns, "interval", minutes=1)
    scheduler.start()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
