import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.feature import TagFeatureInvoiceOut, TagFeatureStatusOut
from backend.services import tag_feature

router = APIRouter(prefix="/api/features/tag-broadcast", tags=["tag-broadcast-feature"])


@router.get("", response_model=TagFeatureStatusOut)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TagFeatureStatusOut:
    row = await tag_feature.get_settings(db)
    return TagFeatureStatusOut(
        has_access=tag_feature.has_access(user),
        is_admin=tag_feature.is_admin(user),
        expires_at=user.tag_feature_expires_at,
        stars_price=row.stars_price,
        duration_days=row.duration_days,
    )


@router.post("/invoice", response_model=TagFeatureInvoiceOut)
async def create_invoice(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TagFeatureInvoiceOut:
    if tag_feature.is_admin(user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "admins already have access")

    row = await tag_feature.get_settings(db)
    payload = f"tag_broadcast:{user.telegram_id}:{row.duration_days}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.bot_token}/createInvoiceLink",
            json={
                "title": "Теги случайных участников",
                "description": (
                    f"Доступ к тегам случайных участников в рассылках на {row.duration_days} дней."
                ),
                "payload": payload,
                "currency": "XTR",
                "prices": [{"label": "Доступ", "amount": row.stars_price}],
            },
        )

    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "failed to create invoice")

    return TagFeatureInvoiceOut(invoice_link=data["result"])
