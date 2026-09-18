from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models.autoresponder_rule import AutoresponderRule
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.autoresponder import AutoresponderRuleIn, AutoresponderRuleOut

router = APIRouter(prefix="/api/autoresponder", tags=["autoresponder"])


async def _get_owned_account(db: AsyncSession, user: User, account_id: int) -> TelegramAccount:
    result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == account_id, TelegramAccount.user_id == user.id
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "account not found")
    return account


@router.get("/{account_id}/rules", response_model=list[AutoresponderRuleOut])
async def list_rules(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AutoresponderRule]:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(AutoresponderRule).where(AutoresponderRule.account_id == account_id)
    )
    return list(result.scalars().all())


@router.post("/{account_id}/rules", response_model=AutoresponderRuleOut, status_code=201)
async def create_rule(
    account_id: int,
    payload: AutoresponderRuleIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoresponderRule:
    await _get_owned_account(db, user, account_id)
    rule = AutoresponderRule(account_id=account_id, **payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule
