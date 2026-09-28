import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.rate_limit import rate_limit
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.feature import ProInvoiceOut, ProStatusOut
from backend.services import pro

router = APIRouter(prefix="/api/features/pro", tags=["pro-subscription"])

_INVOICE_FAILED = "Не удалось создать счёт на оплату"


@router.get("", response_model=ProStatusOut)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProStatusOut:
    row = await pro.get_settings(db)
    return ProStatusOut(
        has_access=pro.has_access(user),
        is_admin=pro.is_admin(user),
        expires_at=user.pro_expires_at,
        stars_price=row.stars_price,
        duration_days=row.duration_days,
        features=pro.PRO_FEATURES,
        max_photos=pro.max_photos(user),
        free_max_rules=pro.FREE_MAX_RULES_PER_ACCOUNT,
        free_max_campaigns=pro.FREE_MAX_CAMPAIGNS_PER_ACCOUNT,
        bot_username=settings.bot_username,
    )


@router.post("/invoice", response_model=ProInvoiceOut)
async def create_invoice(
    user: User = Depends(rate_limit("pro_invoice", limit=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> ProInvoiceOut:
    if pro.is_admin(user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "У администраторов уже есть Pro")

    row = await pro.get_settings(db)
    params = pro.invoice_params(
        row.stars_price, row.duration_days, pro.invoice_payload(user.telegram_id, row.duration_days)
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.bot_token}/createInvoiceLink", json=params
            )
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Не удалось создать счёт на оплату"
        ) from exc

    if not data.get("ok"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Не удалось создать счёт на оплату")

    return ProInvoiceOut(invoice_link=data["result"])
