from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.timeutil import as_utc
from backend.models.team import AccountMember, TeamInvite
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User

MAX_TEAM_MEMBERS = 5
TEAM_PREFIX = "team_"


def parse_team_code(value: str | None) -> str | None:
    if not value or not value.startswith(TEAM_PREFIX):
        return None
    token = value[len(TEAM_PREFIX) :]
    return token if token.isalnum() and len(token) <= 32 else None


async def accept_invite(
    db: AsyncSession, token: str, telegram_id: int, display_name: str
) -> tuple[str, TelegramAccount | None]:
    """Consumes a single-use team invite. Returns (outcome, account) where
    outcome is "joined" | "already" | "own" | "invalid" | "full"."""
    invite = await db.get(TeamInvite, token)
    now = datetime.now(UTC)
    expires_at = as_utc(invite.expires_at) if invite is not None else None
    if invite is None or invite.used_at is not None or expires_at is None or expires_at < now:
        return "invalid", None
    account = await db.get(TelegramAccount, invite.account_id)
    if account is None:
        return "invalid", None

    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id)
        db.add(user)
        await db.flush()
    if user.id == account.user_id:
        return "own", account
    existing = await db.scalar(
        select(AccountMember).where(
            AccountMember.account_id == account.id, AccountMember.user_id == user.id
        )
    )
    if existing is not None:
        return "already", account
    count = await db.scalar(
        select(func.count())
        .select_from(AccountMember)
        .where(AccountMember.account_id == account.id)
    )
    if (count or 0) >= MAX_TEAM_MEMBERS:
        return "full", account

    db.add(AccountMember(account_id=account.id, user_id=user.id, display_name=display_name[:128]))
    invite.used_at = now
    await db.commit()
    return "joined", account
