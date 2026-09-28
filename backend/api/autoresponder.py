from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.rate_limit import rate_limit
from backend.core.uploads import delete_uploads
from backend.db.session import get_db
from backend.models.autoresponder_rule import AutoresponderEvent, AutoresponderRule
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.autoresponder import (
    PRO_RULE_FIELDS,
    AutoresponderRuleIn,
    AutoresponderRuleOut,
    AutoresponderRuleUpdate,
)
from backend.services import pro
from backend.services.media import resolve_photos

router = APIRouter(prefix="/api/autoresponder", tags=["autoresponder"])

# AGENTS.md 4.7: endpoints that trigger external actions are rate-limited per user.
_autoresponder_rate_limit = rate_limit("autoresponder", limit=60, window_seconds=60)


async def _get_owned_account(db: AsyncSession, user: User, account_id: int) -> TelegramAccount:
    result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == account_id, TelegramAccount.user_id == user.id
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Аккаунт не найден")
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Правило не найдено")
    return rule


def _require_pro_for_options(user: User, data: dict) -> None:
    """Schedule, smart filters, typing effect and notifications are Pro
    (AGENTS.md 4.13); switching them *off* is always allowed."""
    if pro.has_access(user):
        return
    if any(data.get(field) for field in PRO_RULE_FIELDS):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Расписание, умные фильтры и уведомления доступны в Pro",
        )


async def _replies_7d(db: AsyncSession, rule_ids: list[int]) -> dict[int, int]:
    if not rule_ids:
        return {}
    since = datetime.now(UTC) - timedelta(days=7)
    rows = await db.execute(
        select(AutoresponderEvent.rule_id, func.count())
        .where(AutoresponderEvent.rule_id.in_(rule_ids), AutoresponderEvent.created_at >= since)
        .group_by(AutoresponderEvent.rule_id)
    )
    return dict(rows.tuples().all())


async def _to_out(db: AsyncSession, rule: AutoresponderRule) -> AutoresponderRuleOut:
    out = AutoresponderRuleOut.model_validate(rule)
    out.replies_7d = (await _replies_7d(db, [rule.id])).get(rule.id, 0)
    return out


@router.get("/{account_id}/rules", response_model=list[AutoresponderRuleOut])
async def list_rules(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AutoresponderRuleOut]:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(AutoresponderRule)
        .where(AutoresponderRule.account_id == account_id)
        .order_by(AutoresponderRule.id)
    )
    rules = list(result.scalars().all())
    counts = await _replies_7d(db, [r.id for r in rules])
    out = []
    for rule in rules:
        item = AutoresponderRuleOut.model_validate(rule)
        item.replies_7d = counts.get(rule.id, 0)
        out.append(item)
    return out


@router.post("/{account_id}/rules", response_model=AutoresponderRuleOut, status_code=201)
async def create_rule(
    account_id: int,
    payload: AutoresponderRuleIn,
    user: User = Depends(_autoresponder_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> AutoresponderRuleOut:
    await _get_owned_account(db, user, account_id)
    data = payload.model_dump(exclude={"photos"})
    _require_pro_for_options(user, data)
    if not pro.has_access(user):
        count = await db.scalar(
            select(func.count())
            .select_from(AutoresponderRule)
            .where(AutoresponderRule.account_id == account_id)
        )
        if (count or 0) >= pro.FREE_MAX_RULES_PER_ACCOUNT:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"Без Pro — до {pro.FREE_MAX_RULES_PER_ACCOUNT} правил на аккаунт",
            )
    rule = AutoresponderRule(
        account_id=account_id, photo_paths=resolve_photos(payload.photos, user), **data
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return await _to_out(db, rule)


@router.patch("/{account_id}/rules/{rule_id}", response_model=AutoresponderRuleOut)
async def update_rule(
    account_id: int,
    rule_id: int,
    payload: AutoresponderRuleUpdate,
    user: User = Depends(_autoresponder_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> AutoresponderRuleOut:
    rule = await _get_owned_rule(db, user, account_id, rule_id)

    data = payload.model_dump(exclude_unset=True, exclude={"photos"})
    _require_pro_for_options(user, data)
    if payload.photos is not None:
        new_paths = resolve_photos(payload.photos, user)
        delete_uploads(rule.photo_paths, keep=new_paths)
        rule.photo_paths = new_paths

    for field, value in data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return await _to_out(db, rule)


@router.delete("/{account_id}/rules/{rule_id}", status_code=204)
async def delete_rule(
    account_id: int,
    rule_id: int,
    user: User = Depends(_autoresponder_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> None:
    rule = await _get_owned_rule(db, user, account_id, rule_id)
    delete_uploads(rule.photo_paths)
    await db.execute(delete(AutoresponderEvent).where(AutoresponderEvent.rule_id == rule.id))
    await db.delete(rule)
    await db.commit()
