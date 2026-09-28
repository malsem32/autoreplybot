from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.user import User
from backend.services import pro

REF_PREFIX = "ref_"


def referral_code(telegram_id: int) -> str:
    return f"{REF_PREFIX}{telegram_id}"


def referral_link(telegram_id: int) -> str:
    """Deep link into the bot; /start picks the code up (bot/handlers/start.py)."""
    return f"https://t.me/{settings.bot_username}?start={referral_code(telegram_id)}"


def parse_referral_code(value: str | None) -> int | None:
    """Returns the inviter's telegram_id from a "ref_<id>" start parameter."""
    if not value or not value.startswith(REF_PREFIX):
        return None
    raw = value[len(REF_PREFIX) :]
    return int(raw) if raw.isdigit() else None


async def attach_referrer(db: AsyncSession, user: User, inviter_telegram_id: int | None) -> bool:
    """Records who invited a *newly created* user. Callers invoke this only
    right after creating the User row, so existing users can't be
    re-attributed by opening someone's link. No self-invites."""
    if inviter_telegram_id is None or user.referred_by_id is not None:
        return False
    if inviter_telegram_id == user.telegram_id:
        return False
    inviter = await db.scalar(select(User).where(User.telegram_id == inviter_telegram_id))
    if inviter is None or inviter.id == user.id:
        return False
    user.referred_by_id = inviter.id
    return True


async def reward_first_payment(db: AsyncSession, invitee: User) -> tuple[User, int] | None:
    """On an invited user's first Pro payment, grants `referral_bonus_days`
    of Pro to both the inviter and the invitee — once per invitee.
    Returns (inviter, bonus_days) for notifying the inviter, or None."""
    if invitee.referred_by_id is None or invitee.referral_rewarded:
        return None
    row = await pro.get_settings(db)
    bonus = row.referral_bonus_days
    invitee.referral_rewarded = True
    inviter = await db.get(User, invitee.referred_by_id)
    if inviter is None or bonus <= 0:
        await db.commit()
        return None

    inviter.referral_days_earned = (inviter.referral_days_earned or 0) + bonus
    await db.commit()
    await pro.grant_access(db, invitee.telegram_id, bonus)
    await pro.grant_access(db, inviter.telegram_id, bonus)
    return inviter, bonus


async def referral_stats(db: AsyncSession, user: User) -> dict:
    invited = await db.scalar(
        select(func.count()).select_from(User).where(User.referred_by_id == user.id)
    )
    paid = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.referred_by_id == user.id, User.referral_rewarded.is_(True))
    )
    row = await pro.get_settings(db)
    return {
        "link": referral_link(user.telegram_id),
        "invited_count": invited or 0,
        "paid_count": paid or 0,
        "days_earned": user.referral_days_earned or 0,
        "bonus_days": row.referral_bonus_days,
    }
