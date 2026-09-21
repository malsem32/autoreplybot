from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.uploads import delete_upload
from backend.db.session import get_db
from backend.models.autoresponder_rule import AutoresponderRule
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.autoresponder import (
    AutoresponderRuleIn,
    AutoresponderRuleOut,
    AutoresponderRuleUpdate,
)

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


async def _get_owned_rule(
    db: AsyncSession, user: User, account_id: int, rule_id: int
) -> AutoresponderRule:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(AutoresponderRule).where(
            AutoresponderRule.id == rule_id, AutoresponderRule.account_id == account_id
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rule not found")
    return rule


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


@router.patch("/{account_id}/rules/{rule_id}", response_model=AutoresponderRuleOut)
async def update_rule(
    account_id: int,
    rule_id: int,
    payload: AutoresponderRuleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoresponderRule:
    rule = await _get_owned_rule(db, user, account_id, rule_id)

    data = payload.model_dump(exclude_unset=True, exclude={"remove_photo"})
    new_photo = data.pop("photo_path", None)
    if payload.remove_photo:
        delete_upload(rule.photo_path)
        rule.photo_path = None
    elif new_photo is not None:
        delete_upload(rule.photo_path)
        rule.photo_path = new_photo

    for field, value in data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{account_id}/rules/{rule_id}", status_code=204)
async def delete_rule(
    account_id: int,
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    rule = await _get_owned_rule(db, user, account_id, rule_id)
    delete_upload(rule.photo_path)
    await db.delete(rule)
    await db.commit()
