from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.rate_limit import rate_limit
from backend.core.uploads import delete_uploads
from backend.db.session import get_db
from backend.models.autoresponder_rule import AutoresponderEvent, AutoresponderRule
from backend.models.user import User
from backend.schemas.autoresponder import (
    PRO_RULE_FIELDS,
    AutoresponderRuleIn,
    AutoresponderRuleOut,
    AutoresponderRuleUpdate,
    RuleTestIn,
    RuleTestOut,
    RuleTestVerdict,
)
from backend.services import access, pro
from backend.services.media import resolve_photos
from backend.services.rule_match import matched_keyword
from backend.services.schedule import is_within_schedule

router = APIRouter(prefix="/api/autoresponder", tags=["autoresponder"])

# AGENTS.md 4.7: endpoints that trigger external actions are rate-limited per user.
_autoresponder_rate_limit = rate_limit("autoresponder", limit=60, window_seconds=60)


async def _get_rule(db: AsyncSession, account_id: int, rule_id: int) -> AutoresponderRule:
    rule = await db.scalar(
        select(AutoresponderRule).where(
            AutoresponderRule.id == rule_id, AutoresponderRule.account_id == account_id
        )
    )
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Правило не найдено")
    return rule


def _require_pro_for_options(owner: User, data: dict) -> None:
    """Schedule, smart filters, typing effect, notifications and group
    replies are Pro (AGENTS.md 4.13) — of the account *owner*, so team
    members work within the owner's plan. Switching them off is always
    allowed."""
    if pro.has_access(owner):
        return
    if any(data.get(field) for field in PRO_RULE_FIELDS) or data.get("scope") not in (
        None,
        "private",
    ):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Расписание, умные фильтры, группы и уведомления доступны в Pro",
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


async def _rules(db: AsyncSession, account_id: int) -> list[AutoresponderRule]:
    result = await db.execute(
        select(AutoresponderRule)
        .where(AutoresponderRule.account_id == account_id)
        .order_by(AutoresponderRule.id)
    )
    return list(result.scalars().all())


@router.get("/{account_id}/rules", response_model=list[AutoresponderRuleOut])
async def list_rules(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AutoresponderRuleOut]:
    await access.get_account(db, user, account_id)
    rules = await _rules(db, account_id)
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
    account = await access.get_account(db, user, account_id)
    owner = await access.account_owner(db, account)
    data = payload.model_dump(exclude={"photos"})
    _require_pro_for_options(owner, data)
    if not pro.has_access(owner):
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
        account_id=account_id, photo_paths=resolve_photos(payload.photos, owner), **data
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
    account = await access.get_account(db, user, account_id)
    owner = await access.account_owner(db, account)
    rule = await _get_rule(db, account_id, rule_id)

    data = payload.model_dump(exclude_unset=True, exclude={"photos"})
    _require_pro_for_options(owner, data)
    if payload.photos is not None:
        new_paths = resolve_photos(payload.photos, owner)
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
    await access.get_account(db, user, account_id)
    rule = await _get_rule(db, account_id, rule_id)
    delete_uploads(rule.photo_paths)
    await db.execute(delete(AutoresponderEvent).where(AutoresponderEvent.rule_id == rule.id))
    await db.delete(rule)
    await db.commit()


@router.post("/{account_id}/test", response_model=RuleTestOut)
async def test_rules(
    account_id: int,
    payload: RuleTestIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RuleTestOut:
    """Dry run: which rule would answer this message right now, and why the
    others wouldn't. Uses the same matching code as the worker; filters that
    depend on chat history can only be checked on a real message."""
    account = await access.get_account(db, user, account_id)
    has_pro = pro.has_access(await access.account_owner(db, account))
    verdicts: list[RuleTestVerdict] = []
    answer: int | None = None
    for rule in await _rules(db, account_id):
        keyword = matched_keyword(rule.trigger_type, rule.keywords, rule.match_mode, payload.text)
        blocked = None
        if not rule.is_enabled:
            blocked = "disabled"
        elif keyword is None:
            blocked = None
        elif payload.in_group and not (has_pro and rule.scope in ("groups", "all")):
            blocked = "scope"
        elif not payload.in_group and rule.scope == "groups":
            blocked = "scope"
        elif (
            has_pro
            and rule.schedule_enabled
            and not is_within_schedule(
                rule.schedule_days, rule.schedule_start, rule.schedule_end, rule.timezone
            )
        ):
            blocked = "schedule"
        verdicts.append(
            RuleTestVerdict(
                rule_id=rule.id, matched=keyword is not None, keyword=keyword, blocked_by=blocked
            )
        )
        if answer is None and keyword is not None and blocked is None:
            answer = rule.id

    note = (
        "Фильтры «только новым» и «не мешать диалогу» и паузу между ответами одному "
        "человеку можно проверить только на настоящем сообщении."
    )
    return RuleTestOut(answer_rule_id=answer, note=note, verdicts=verdicts)
