from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.uploads import delete_upload
from backend.db.session import get_db
from backend.models.broadcast import BroadcastCampaign
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.broadcast import (
    BroadcastCampaignIn,
    BroadcastCampaignOut,
    BroadcastCampaignUpdate,
)
from backend.services import tag_feature

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])


def _require_tag_feature_access(user: User) -> None:
    if not tag_feature.has_access(user):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "tag_random_users requires an active purchase (see /api/features/tag-broadcast)",
        )


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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "campaign not found")
    return campaign


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
    if payload.tag_random_users:
        _require_tag_feature_access(user)
    campaign = BroadcastCampaign(account_id=account_id, status="active", **payload.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.patch("/{account_id}/campaigns/{campaign_id}", response_model=BroadcastCampaignOut)
async def update_campaign(
    account_id: int,
    campaign_id: int,
    payload: BroadcastCampaignUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    if payload.tag_random_users:
        _require_tag_feature_access(user)

    data = payload.model_dump(exclude_unset=True, exclude={"remove_photo"})
    new_photo = data.pop("photo_path", None)
    if payload.remove_photo:
        delete_upload(campaign.photo_path)
        campaign.photo_path = None
    elif new_photo is not None:
        delete_upload(campaign.photo_path)
        campaign.photo_path = new_photo

    for field, value in data.items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{account_id}/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    delete_upload(campaign.photo_path)
    await db.delete(campaign)
    await db.commit()


@router.post("/{account_id}/campaigns/{campaign_id}/pause", response_model=BroadcastCampaignOut)
async def pause_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BroadcastCampaign:
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    campaign.status = "active"
    await db.commit()
    await db.refresh(campaign)
    return campaign
