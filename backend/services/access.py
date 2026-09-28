"""Who may manage which TelegramAccount: its owner, plus team members the
owner invited while the owner has Pro (AGENTS.md 4.16)."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.team import AccountMember
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro


async def account_owner(db: AsyncSession, account: TelegramAccount) -> User:
    owner = await db.get(User, account.user_id)
    assert owner is not None
    return owner


async def get_account(
    db: AsyncSession, user: User, account_id: int, *, owner_only: bool = False
) -> TelegramAccount:
    """The account if `user` owns it or (unless `owner_only`) is a member of
    it and the owner's Pro is active. 404 otherwise — never reveals that an
    account exists to outsiders."""
    account = await db.get(TelegramAccount, account_id)
    if account is not None and account.user_id == user.id:
        return account
    if account is not None and not owner_only:
        member = await db.scalar(
            select(AccountMember.id).where(
                AccountMember.account_id == account_id, AccountMember.user_id == user.id
            )
        )
        if member is not None and pro.has_access(await account_owner(db, account)):
            return account
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Аккаунт не найден")


async def shared_accounts(db: AsyncSession, user: User) -> list[TelegramAccount]:
    """Accounts shared with `user` whose owners currently have Pro."""
    rows = await db.execute(
        select(TelegramAccount, User)
        .join(AccountMember, AccountMember.account_id == TelegramAccount.id)
        .join(User, User.id == TelegramAccount.user_id)
        .where(AccountMember.user_id == user.id)
        .order_by(TelegramAccount.id)
    )
    return [account for account, owner in rows.tuples() if pro.has_access(owner)]
