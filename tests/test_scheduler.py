from datetime import UTC, datetime, timedelta

from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from workers.scheduler import _is_due


async def _campaign(db, **kwargs) -> BroadcastCampaign:
    user = User(telegram_id=1)
    db.add(user)
    await db.flush()
    account = TelegramAccount(user_id=user.id, phone="1", encrypted_session="x", is_active=True)
    db.add(account)
    await db.flush()
    campaign = BroadcastCampaign(
        account_id=account.id, title="t", text_template="x", target_chats=["@a"], **kwargs
    )
    db.add(campaign)
    await db.commit()
    return campaign


async def test_once_campaign_waits_for_its_time_and_runs_once(db_sessionmaker):
    now = datetime.now(UTC)
    async with db_sessionmaker() as db:
        campaign = await _campaign(
            db, schedule_type="once", scheduled_at=now + timedelta(hours=1), status="active"
        )
        assert not await _is_due(db, campaign)

        campaign.scheduled_at = now - timedelta(minutes=1)
        assert await _is_due(db, campaign)

        db.add(BroadcastLog(campaign_id=campaign.id, chat_id=1, sent_at=now, status="success"))
        await db.commit()
        assert not await _is_due(db, campaign)


async def test_once_campaign_without_time_is_never_due(db_sessionmaker):
    async with db_sessionmaker() as db:
        campaign = await _campaign(db, schedule_type="once", scheduled_at=None, status="active")
        assert not await _is_due(db, campaign)


async def test_recurring_campaign_respects_interval(db_sessionmaker):
    now = datetime.now(UTC)
    async with db_sessionmaker() as db:
        campaign = await _campaign(db, schedule_type="recurring", interval_minutes=60)
        assert await _is_due(db, campaign)
        db.add(BroadcastLog(campaign_id=campaign.id, chat_id=1, sent_at=now, status="success"))
        await db.commit()
        assert not await _is_due(db, campaign)
