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
from workers.responder import register_responder

logger = logging.getLogger(__name__)

_responder_registered: set[int] = set()


async def ensure_responders_running() -> None:
    """Keeps a Pyrogram client alive with a registered autoresponder for
    every active TelegramAccount. Runs on a timer so an account activated
    after the worker started still gets picked up."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.is_active.is_(True))
        )
        for account in result.scalars().all():
            try:
                client = await client_manager.start(account.id, account.encrypted_session)
            except Exception:
                logger.exception("failed to start client for account %s", account.id)
                continue

            if account.id not in _responder_registered:
                register_responder(client, account.id)
                _responder_registered.add(account.id)


async def _is_due(db, campaign: BroadcastCampaign) -> bool:
    last_sent_at = await db.scalar(
        select(BroadcastLog.sent_at)
        .where(BroadcastLog.campaign_id == campaign.id)
        .order_by(BroadcastLog.sent_at.desc())
        .limit(1)
    )

    if campaign.schedule_type == "once":
        return last_sent_at is None and datetime.now(UTC) >= campaign.scheduled_at

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

            if campaign.schedule_type == "once":
                campaign.status = "finished"
                await db.commit()


async def main() -> None:
    configure_logging()

    scheduler = AsyncIOScheduler()
    # Short interval so a freshly created campaign goes out within
    # seconds instead of waiting up to a minute for the next tick.
    scheduler.add_job(dispatch_due_campaigns, "interval", seconds=15)
    scheduler.add_job(ensure_responders_running, "interval", minutes=1)
    scheduler.start()

    await ensure_responders_running()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
