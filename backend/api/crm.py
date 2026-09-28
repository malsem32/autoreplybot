"""Pro: leads mini-CRM ("Обращения"), team access and CSV export to the bot
chat (AGENTS.md 4.16)."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.rate_limit import rate_limit
from backend.db.session import get_db
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.lead import LEAD_STATUSES, Lead
from backend.models.team import AccountMember, TeamInvite
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.crm import (
    LeadListOut,
    LeadOut,
    LeadUpdate,
    MeOut,
    MeUpdate,
    TeamInviteOut,
    TeamMemberOut,
    TeamOut,
)
from backend.services import access, pro
from backend.services.bot_api import build_csv, send_document
from backend.services.team import MAX_TEAM_MEMBERS, TEAM_PREFIX

router = APIRouter(prefix="/api", tags=["crm"])

INVITE_TTL = timedelta(hours=24)
EXPORT_LIMIT = 5000

STATUS_LABELS = {"new": "Новое", "in_work": "В работе", "done": "Готово"}


async def _pro_account(
    db: AsyncSession, user: User, account_id: int, feature: str
) -> TelegramAccount:
    account = await access.get_account(db, user, account_id)
    if not pro.has_access(await access.account_owner(db, account)):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"{feature} — функция Pro")
    return account


# --- Leads ---------------------------------------------------------------------


@router.get("/leads/{account_id}", response_model=LeadListOut)
async def list_leads(
    account_id: int,
    lead_status: str | None = Query(default=None, alias="status", pattern="^(new|in_work|done)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeadListOut:
    await _pro_account(db, user, account_id, "Обращения")
    query = select(Lead).where(Lead.account_id == account_id)
    if lead_status:
        query = query.where(Lead.status == lead_status)
    leads = (await db.execute(query.order_by(Lead.last_message_at.desc()).limit(300))).scalars()
    counts = dict(
        (
            await db.execute(
                select(Lead.status, func.count())
                .where(Lead.account_id == account_id)
                .group_by(Lead.status)
            )
        )
        .tuples()
        .all()
    )
    return LeadListOut(
        leads=[LeadOut.model_validate(lead) for lead in leads],
        counts={s: counts.get(s, 0) for s in LEAD_STATUSES},
    )


@router.patch("/leads/{account_id}/{lead_id}", response_model=LeadOut)
async def update_lead(
    account_id: int,
    lead_id: int,
    payload: LeadUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeadOut:
    await _pro_account(db, user, account_id, "Обращения")
    lead = await db.scalar(select(Lead).where(Lead.id == lead_id, Lead.account_id == account_id))
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Обращение не найдено")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    await db.commit()
    await db.refresh(lead)
    return LeadOut.model_validate(lead)


# --- CSV export to the bot chat --------------------------------------------------


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else ""


@router.post("/export/leads/{account_id}", status_code=202)
async def export_leads(
    account_id: int,
    user: User = Depends(rate_limit("export", limit=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _pro_account(db, user, account_id, "Выгрузка")
    leads = (
        await db.execute(
            select(Lead)
            .where(Lead.account_id == account_id)
            .order_by(Lead.last_message_at.desc())
            .limit(EXPORT_LIMIT)
        )
    ).scalars()
    rows = [
        [
            lead.name,
            f"@{lead.username}" if lead.username else "",
            lead.peer_id,
            STATUS_LABELS.get(lead.status, lead.status),
            lead.messages_count,
            _fmt(lead.created_at),
            _fmt(lead.last_message_at),
            lead.last_text,
            lead.note,
        ]
        for lead in leads
    ]
    content = build_csv(
        [
            "Имя",
            "Юзернейм",
            "ID",
            "Статус",
            "Сообщений",
            "Первое обращение",
            "Последнее",
            "Последнее сообщение",
            "Заметка",
        ],
        rows,
    )
    if not await send_document(
        user.telegram_id, "obrashcheniya.csv", content, f"Обращения: {len(rows)}"
    ):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Не удалось отправить файл — откройте чат с ботом"
        )
    return {"rows": len(rows)}


@router.post("/export/campaigns/{account_id}/{campaign_id}", status_code=202)
async def export_campaign(
    account_id: int,
    campaign_id: int,
    user: User = Depends(rate_limit("export", limit=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _pro_account(db, user, account_id, "Выгрузка")
    campaign = await db.scalar(
        select(BroadcastCampaign).where(
            BroadcastCampaign.id == campaign_id, BroadcastCampaign.account_id == account_id
        )
    )
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Рассылка не найдена")
    logs = (
        await db.execute(
            select(BroadcastLog)
            .where(BroadcastLog.campaign_id == campaign.id)
            .order_by(BroadcastLog.sent_at.desc())
            .limit(EXPORT_LIMIT)
        )
    ).scalars()
    rows = [
        [
            _fmt(log.sent_at),
            log.target or "",
            log.chat_id or "",
            "Доставлено" if log.status == "success" else "Ошибка",
            log.error_message or "",
        ]
        for log in logs
    ]
    content = build_csv(["Время (UTC)", "Цель", "ID чата", "Статус", "Ошибка"], rows)
    if not await send_document(
        user.telegram_id,
        f"rassylka_{campaign.id}.csv",
        content,
        f"«{campaign.title}»: {len(rows)} отправок",
    ):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Не удалось отправить файл — откройте чат с ботом"
        )
    return {"rows": len(rows)}


# --- Team ------------------------------------------------------------------------


@router.get("/team/{account_id}", response_model=TeamOut)
async def get_team(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamOut:
    await access.get_account(db, user, account_id, owner_only=True)
    members = (
        await db.execute(
            select(AccountMember)
            .where(AccountMember.account_id == account_id)
            .order_by(AccountMember.id)
        )
    ).scalars()
    return TeamOut(
        members=[
            TeamMemberOut(
                id=m.id, display_name=m.display_name or "Без имени", created_at=m.created_at
            )
            for m in members
        ],
        max_members=MAX_TEAM_MEMBERS,
    )


@router.post("/team/{account_id}/invite", response_model=TeamInviteOut)
async def create_invite(
    account_id: int,
    user: User = Depends(rate_limit("team_invite", limit=20, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> TeamInviteOut:
    await access.get_account(db, user, account_id, owner_only=True)
    if not pro.has_access(user):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Команда — функция Pro")
    count = await db.scalar(
        select(func.count())
        .select_from(AccountMember)
        .where(AccountMember.account_id == account_id)
    )
    if (count or 0) >= MAX_TEAM_MEMBERS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"В команде уже {MAX_TEAM_MEMBERS} человек — это максимум"
        )
    invite = TeamInvite(
        token=secrets.token_hex(12),
        account_id=account_id,
        created_by=user.id,
        expires_at=datetime.now(UTC) + INVITE_TTL,
    )
    db.add(invite)
    await db.commit()
    return TeamInviteOut(
        link=f"https://t.me/{settings.bot_username}?start={TEAM_PREFIX}{invite.token}",
        expires_at=invite.expires_at,
    )


@router.delete("/team/{account_id}/members/{member_id}", status_code=204)
async def remove_member(
    account_id: int,
    member_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """The owner removes anyone; a member can remove only themselves."""
    member = await db.scalar(
        select(AccountMember).where(
            AccountMember.id == member_id, AccountMember.account_id == account_id
        )
    )
    account = await db.get(TelegramAccount, account_id)
    if member is None or account is None or user.id not in (account.user_id, member.user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Участник не найден")
    await db.delete(member)
    await db.commit()


@router.post("/team/{account_id}/leave", status_code=204)
async def leave_team(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    member = await db.scalar(
        select(AccountMember).where(
            AccountMember.account_id == account_id, AccountMember.user_id == user.id
        )
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вы не в команде этого аккаунта")
    await db.delete(member)
    await db.commit()


# --- Personal settings -------------------------------------------------------------


@router.get("/me", response_model=MeOut)
async def get_me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut(weekly_digest=user.weekly_digest)


@router.patch("/me", response_model=MeOut)
async def update_me(
    payload: MeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    if payload.weekly_digest is not None:
        user.weekly_digest = payload.weekly_digest
    await db.commit()
    return MeOut(weekly_digest=user.weekly_digest)
