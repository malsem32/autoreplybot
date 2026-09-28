from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.rate_limit import rate_limit
from backend.core.uploads import delete_uploads
from backend.db.session import get_db
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.broadcast import (
    PRO_CAMPAIGN_FIELDS,
    BroadcastCampaignIn,
    BroadcastCampaignOut,
    BroadcastCampaignUpdate,
    BroadcastLogOut,
    CampaignStatsOut,
    TargetStatsOut,
)
from backend.services import access, pro
from backend.services.media import resolve_photos

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])

# AGENTS.md 4.7: endpoints that trigger external actions are rate-limited per user.
_broadcasts_rate_limit = rate_limit("broadcasts", limit=60, window_seconds=60)


_PRO_OPTION_MESSAGES = {
    "tag_random_users": "Теги случайных участников доступны в Pro",
    "protect_content": "Защита от пересылки доступна в Pro",
    "auto_disable_failing": "Автоотключение недоступных чатов доступно в Pro",
    "notify_report": "Отчёты о рассылке доступны в Pro",
}


def _require_pro_for_options(owner: User, data: dict) -> None:
    """Tags, forward protection, auto-disabling and reports are Pro
    (AGENTS.md 4.13) — of the account *owner*; switching them off is always
    allowed."""
    if pro.has_access(owner):
        return
    for field in PRO_CAMPAIGN_FIELDS:
        if data.get(field):
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, _PRO_OPTION_MESSAGES[field])


async def _campaign_owner(db: AsyncSession, campaign: BroadcastCampaign) -> User:
    account = await db.get(TelegramAccount, campaign.account_id)
    assert account is not None
    return await access.account_owner(db, account)


async def _get_owned_campaign(
    db: AsyncSession, user: User, account_id: int, campaign_id: int
) -> BroadcastCampaign:
    await access.get_account(db, user, account_id)
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
    await access.get_account(db, user, account_id)
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
    account = await access.get_account(db, user, account_id)
    owner = await access.account_owner(db, account)
    _require_pro_for_options(owner, payload.model_dump())
    if not pro.has_access(owner):
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
        photo_paths=resolve_photos(payload.photos, owner),
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
    owner = await _campaign_owner(db, campaign)
    data = payload.model_dump(exclude_unset=True, exclude={"photos", "disabled_targets"})
    _require_pro_for_options(owner, data)
    if payload.photos is not None:
        new_paths = resolve_photos(payload.photos, owner)
        delete_uploads(campaign.photo_paths, keep=new_paths)
        campaign.photo_paths = new_paths

    for field, value in data.items():
        setattr(campaign, field, value)

    disabled = list(campaign.disabled_targets or [])
    if payload.disabled_targets is not None:
        # Only restoring is allowed here; disabling is the worker's call.
        disabled = [t for t in disabled if t in payload.disabled_targets]
    campaign.disabled_targets = [t for t in disabled if t in campaign.target_chats]

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


@router.get("/{account_id}/campaigns/{campaign_id}/stats", response_model=CampaignStatsOut)
async def campaign_stats(
    account_id: int,
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CampaignStatsOut:
    """Per-chat delivery statistics (Pro), aggregated in SQL (AGENTS.md 4.6)."""
    campaign = await _get_owned_campaign(db, user, account_id, campaign_id)
    if not pro.has_access(await _campaign_owner(db, campaign)):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Статистика по чатам доступна в Pro")

    per_target = (
        select(
            BroadcastLog.target.label("target"),
            func.max(BroadcastLog.id).label("last_id"),
            func.sum(case((BroadcastLog.status == "success", 1), else_=0)).label("sent"),
            func.sum(case((BroadcastLog.status != "success", 1), else_=0)).label("failed"),
        )
        .where(BroadcastLog.campaign_id == campaign.id, BroadcastLog.target.is_not(None))
        .group_by(BroadcastLog.target)
        .subquery()
    )
    rows = await db.execute(
        select(
            per_target.c.target,
            per_target.c.sent,
            per_target.c.failed,
            BroadcastLog.status,
            BroadcastLog.error_message,
            BroadcastLog.sent_at,
        ).join(BroadcastLog, BroadcastLog.id == per_target.c.last_id)
    )
    found = {row.target: row for row in rows}

    disabled = set(campaign.disabled_targets or [])
    targets = []
    for target in campaign.target_chats:
        row = found.get(target)
        targets.append(
            TargetStatsOut(
                target=target,
                sent=int(row.sent) if row else 0,
                failed=int(row.failed) if row else 0,
                last_status=row.status if row else None,
                last_error=row.error_message if row else None,
                last_sent_at=row.sent_at if row else None,
                disabled=target in disabled,
            )
        )
    return CampaignStatsOut(
        sent=sum(t.sent for t in targets),
        failed=sum(t.failed for t in targets),
        targets=targets,
    )


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
