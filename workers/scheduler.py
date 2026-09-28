import asyncio
import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.errors import AuthKeyUnregistered, SessionRevoked, UserDeactivated
from sqlalchemy import select

from backend.core.logging import configure_logging
from backend.core.timeutil import as_utc
from backend.db.session import SessionLocal
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from workers.broadcaster import run_campaign
from workers.client_manager import client_manager
from workers.digests import send_pro_reminders, send_weekly_digests
from workers.responder import register_responder

logger = logging.getLogger(__name__)

# Errors meaning the stored session is dead for good (user terminated it in
# Telegram's "Devices" screen, account deleted, ...). The account is marked
# inactive so the Mini App shows it needs reconnecting, instead of the
# worker retrying it forever.
_DEAD_SESSION_ERRORS = (AuthKeyUnregistered, SessionRevoked, UserDeactivated)

_responder_registered: set[int] = set()
# One running broadcast per account at a time: parallel campaigns of the
# same account would halve the 20-45s anti-ban delay (AGENTS.md 4.3).
_busy_accounts: set[int] = set()
_background_tasks: set[asyncio.Task] = set()


async def _stop_client(account_id: int) -> None:
    await client_manager.stop(account_id)
    _responder_registered.discard(account_id)


async def ensure_responders_running() -> None:
    """Keeps a Pyrogram client alive with a registered autoresponder for
    every active TelegramAccount, and disconnects clients of accounts that
    were paused or deleted in the Mini App (AGENTS.md 4.5). Runs on a timer
    so changes are picked up without restarting the worker."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.is_active.is_(True))
        )
        accounts = list(result.scalars().all())
        active_ids = {a.id for a in accounts}

        for account_id in client_manager.running_ids() - active_ids:
            if account_id not in _busy_accounts:
                await _stop_client(account_id)

        for account in accounts:
            if not account.encrypted_session:
                continue
            try:
                client = await client_manager.start(account.id, account.encrypted_session)
            except _DEAD_SESSION_ERRORS:
                logger.warning("session of account %s was revoked, deactivating", account.id)
                account.is_active = False
                await db.commit()
                await _stop_client(account.id)
                continue
            except Exception:
                logger.exception("failed to start client for account %s", account.id)
                continue

            if account.id not in _responder_registered:
                register_responder(client, account.id)
                _responder_registered.add(account.id)


async def _is_due(db, campaign: BroadcastCampaign) -> bool:
    last_sent_at = as_utc(
        await db.scalar(
            select(BroadcastLog.sent_at)
            .where(BroadcastLog.campaign_id == campaign.id)
            .order_by(BroadcastLog.sent_at.desc())
            .limit(1)
        )
    )
    now = datetime.now(UTC)

    if campaign.schedule_type == "once":
        scheduled_at = as_utc(campaign.scheduled_at)
        if scheduled_at is None or now < scheduled_at:
            return False
        # Not sent yet for the current scheduled time (it may have been
        # re-scheduled after an earlier run).
        return last_sent_at is None or last_sent_at < scheduled_at

    if last_sent_at is None:
        return True
    return now - last_sent_at >= timedelta(minutes=campaign.interval_minutes)


async def _run_campaign_task(campaign_id: int, account_id: int) -> None:
    try:
        async with SessionLocal() as db:
            campaign = await db.get(BroadcastCampaign, campaign_id)
            account = await db.get(TelegramAccount, account_id)
            if campaign is None or account is None or campaign.status != "active":
                return

            try:
                client = await client_manager.start(account.id, account.encrypted_session)
            except Exception:
                logger.exception("failed to start client for campaign %s", campaign_id)
                return

            try:
                await run_campaign(client, db, campaign)
            except Exception:
                logger.exception("campaign %s failed", campaign_id)

            if campaign.schedule_type == "once" and campaign.status == "active":
                campaign.status = "finished"
                await db.commit()
    finally:
        _busy_accounts.discard(account_id)


async def dispatch_due_campaigns() -> None:
    """Starts every due campaign as its own background task, so one long
    campaign (20-45s per chat) doesn't hold up the rest."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(BroadcastCampaign, TelegramAccount)
            .join(TelegramAccount, BroadcastCampaign.account_id == TelegramAccount.id)
            .where(BroadcastCampaign.status == "active", TelegramAccount.is_active.is_(True))
            .order_by(BroadcastCampaign.id)
        )
        for campaign, account in result.all():
            if account.id in _busy_accounts or not await _is_due(db, campaign):
                continue
            _busy_accounts.add(account.id)
            task = asyncio.create_task(_run_campaign_task(campaign.id, account.id))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)


async def main() -> None:
    configure_logging()

    scheduler = AsyncIOScheduler()
    # Short interval so a freshly created campaign goes out within
    # seconds instead of waiting up to a minute for the next tick.
    scheduler.add_job(dispatch_due_campaigns, "interval", seconds=15, max_instances=1)
    scheduler.add_job(ensure_responders_running, "interval", minutes=1, max_instances=1)
    scheduler.add_job(send_pro_reminders, "interval", hours=1, max_instances=1)
    scheduler.add_job(send_weekly_digests, "interval", hours=1, max_instances=1)
    scheduler.start()

    await ensure_responders_running()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
