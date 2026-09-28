from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.rate_limit import rate_limit
from backend.core.uploads import delete_uploads
from backend.db.session import get_db
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.broadcast import (
    BroadcastCampaignIn,
    BroadcastCampaignOut,
    BroadcastCampaignUpdate,
    BroadcastLogOut,
)
from backend.services import pro
from backend.services.media import resolve_photos

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])

# AGENTS.md 4.7: endpoints that trigger external actions are rate-limited per user.
_broadcasts_rate_limit = rate_limit("broadcasts", limit=60, window_seconds=60)


def _require_pro_for_options(
    user: User, payload: BroadcastCampaignIn | BroadcastCampaignUpdate
) -> None:
    """Tags and forward protection are Pro features (AGENTS.md 4.13)."""
    if pro.has_access(user):
        return
    if payload.tag_random_users:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED, "Теги случайных участников доступны в Pro"
        )
    if payload.protect_content:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Защита от пересылки доступна в Pro")


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


async def _get_owned_campaign(
    db: AsyncSession, user: User, account_id: int, campaign_id: int
) -> BroadcastCampaign:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(BroadcastCampaign).where(
            BroadcastCampaign.id == campaign_id, BroadcastCampaign.account_id == account_id
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Кампания не найдена")
    return campaign


@router.get("/{account_id}/campaigns", response_model=list[BroadcastCampaignOut])
async def list_campaigns(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BroadcastCampaign]:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(BroadcastCampaign)
        .where(BroadcastCampaign.account_id == account_id)
        .order_by(BroadcastCampaign.id)
    )
    return list(result.scalars().all())


@router.post("/{account_id}/campaigns", response_model=BroadcastCampaignOut, status_code=201)
async def create_campaign(
    account_id: int,
    payload: BroadcastCampaignIn,
    user: User = Depends(_broadcasts_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    await _get_owned_account(db, user, account_id)
    _require_pro_for_options(user, payload)
    if not pro.has_access(user):
        count = await db.scalar(
            select(func.count())
            .select_from(BroadcastCampaign)
            .where(BroadcastCampaign.account_id == account_id)
        )
        if (count or 0) >= pro.FREE_MAX_CAMPAIGNS_PER_ACCOUNT:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"Без Pro — до {pro.FREE_MAX_CAMPAIGNS_PER_ACCOUNT} рассылок на аккаунт",
            )
    campaign = BroadcastCampaign(
        account_id=account_id,
        status="active",
        photo_paths=resolve_photos(payload.photos, user),
        **payload.model_dump(exclude={"photos"}),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.patch("/{account_id}/campaigns/{campaign_id}", response_model=BroadcastCampaignOut)
async def update_campaign(
    account_id: int,
    campaign_id: int,
    payload: BroadcastCampaignUpdate,
    user: User = Depends(_broadcasts_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    _require_pro_for_options(user, payload)

    data = payload.model_dump(exclude_unset=True, exclude={"photos"})
    if payload.photos is not None:
        new_paths = resolve_photos(payload.photos, user)
        delete_uploads(campaign.photo_paths, keep=new_paths)
        campaign.photo_paths = new_paths

    for field, value in data.items():
        setattr(campaign, field, value)

    # Re-scheduling a finished one-off campaign sends it again at the new time.
    if (
        campaign.status == "finished"
        and "scheduled_at" in data
        and campaign.schedule_type == "once"
    ):
        campaign.status = "active"

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{account_id}/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(_broadcasts_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> None:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    delete_uploads(campaign.photo_paths)
    await db.execute(delete(BroadcastLog).where(BroadcastLog.campaign_id == campaign.id))
    await db.delete(campaign)
    await db.commit()


@router.get("/{account_id}/campaigns/{campaign_id}/logs", response_model=list[BroadcastLogOut])
async def list_campaign_logs(
    account_id: int,
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BroadcastLog]:
    await _get_owned_campaign(db, user, account_id, campaign_id)
    result = await db.execute(
        select(BroadcastLog)
        .where(BroadcastLog.campaign_id == campaign_id)
        .order_by(BroadcastLog.sent_at.desc())
        .limit(200)
    )
    return list(result.scalars().all())


@router.post("/{account_id}/campaigns/{campaign_id}/pause", response_model=BroadcastCampaignOut)
async def pause_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(_broadcasts_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    campaign.status = "paused"
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{account_id}/campaigns/{campaign_id}/resume", response_model=BroadcastCampaignOut)
async def resume_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(_broadcasts_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    campaign.status = "active"
    await db.commit()
    await db.refresh(campaign)
    return campaign
