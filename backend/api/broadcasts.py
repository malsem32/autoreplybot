from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models.broadcast import BroadcastCampaign
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.broadcast import BroadcastCampaignIn, BroadcastCampaignOut

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])


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


@router.get("/{account_id}/campaigns", response_model=list[BroadcastCampaignOut])
async def list_campaigns(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BroadcastCampaign]:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(BroadcastCampaign).where(BroadcastCampaign.account_id == account_id)
    )
    return list(result.scalars().all())


@router.post("/{account_id}/campaigns", response_model=BroadcastCampaignOut, status_code=201)
async def create_campaign(
    account_id: int,
    payload: BroadcastCampaignIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    await _get_owned_account(db, user, account_id)
    campaign = BroadcastCampaign(account_id=account_id, status="active", **payload.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{account_id}/campaigns/{campaign_id}/pause", response_model=BroadcastCampaignOut)
async def pause_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    await _get_owned_account(db, user, account_id)
    result = await db.execute(
        select(BroadcastCampaign).where(
            BroadcastCampaign.id == campaign_id, BroadcastCampaign.account_id == account_id
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "campaign not found")
    campaign.status = "paused"
    await db.commit()
    await db.refresh(campaign)
    return campaign
