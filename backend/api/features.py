import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.rate_limit import rate_limit
from backend.db.session import get_db
from backend.models.feature_settings import ProSetting
from backend.models.user import User
from backend.schemas.feature import (
    ProFeatureGroupOut,
    ProInvoiceIn,
    ProInvoiceOut,
    ProPlanOut,
    ProStatusOut,
)
from backend.services import pro

router = APIRouter(prefix="/api/features/pro", tags=["pro-subscription"])

_INVOICE_FAILED = "Не удалось создать счёт на оплату"


def _plans_out(row: ProSetting) -> list[ProPlanOut]:
    per_day = row.stars_price / row.duration_days if row.duration_days else 0
    out = []
    for plan in pro.plans(row):
        full = per_day * plan.days
        discount = round((1 - plan.stars / full) * 100) if full and plan.id != "month" else 0
        out.append(
            ProPlanOut(
                id=plan.id,
                title=plan.title,
                days=plan.days,
                stars=plan.stars,
                discount_percent=max(0, discount),
            )
        )
    return out


async def _status(db: AsyncSession, user: User) -> ProStatusOut:
    row = await pro.get_settings(db)
    return ProStatusOut(
        has_access=pro.has_access(user),
        is_admin=pro.is_admin(user),
        expires_at=user.pro_expires_at,
        stars_price=row.stars_price,
        duration_days=row.duration_days,
        plans=_plans_out(row),
        trial_available=pro.trial_available(user, row),
        trial_days=row.trial_days,
        features=pro.PRO_FEATURES,
        feature_groups=[ProFeatureGroupOut(**g) for g in pro.PRO_FEATURE_GROUPS],
        max_photos=pro.max_photos(user),
        free_max_rules=pro.FREE_MAX_RULES_PER_ACCOUNT,
        free_max_campaigns=pro.FREE_MAX_CAMPAIGNS_PER_ACCOUNT,
        bot_username=settings.bot_username,
    )


@router.get("", response_model=ProStatusOut)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProStatusOut:
    return await _status(db, user)


@router.post("/trial", response_model=ProStatusOut)
async def start_trial(
    user: User = Depends(rate_limit("pro_trial", limit=5, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> ProStatusOut:
    """One free Pro trial per user."""
    if not await pro.start_trial(db, user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пробный период уже использован")
    return await _status(db, user)


@router.post("/invoice", response_model=ProInvoiceOut)
async def create_invoice(
    payload: ProInvoiceIn = Body(default_factory=ProInvoiceIn),
    user: User = Depends(rate_limit("pro_invoice", limit=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> ProInvoiceOut:
    if pro.is_admin(user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "У администраторов уже есть Pro")

    row = await pro.get_settings(db)
    plan = pro.find_plan(row, payload.plan)
    if plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Такого тарифа нет")
    params = pro.invoice_params(
        plan.stars, plan.days, pro.invoice_payload(user.telegram_id, plan.days)
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.bot_token}/createInvoiceLink", json=params
            )
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, _INVOICE_FAILED) from exc

    if not data.get("ok"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, _INVOICE_FAILED)

    return ProInvoiceOut(invoice_link=data["result"])
