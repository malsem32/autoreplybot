import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.security import encrypt_secret
from backend.db.session import get_db
from backend.models.admin import AdminAuditLog, Payment
from backend.models.autoresponder_rule import AutoresponderEvent, AutoresponderRule
from backend.models.broadcast import BroadcastCampaign
from backend.models.feature_settings import ProSetting
from backend.models.lead import Lead
from backend.models.proxy import Proxy
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.admin import (
    AdminAccount,
    AdminAuditEntry,
    AdminPayment,
    AdminUserDetail,
    AdminUserList,
    AdminUserRow,
    GrantProIn,
)
from backend.schemas.feature import ProSettingsOut, ProSettingsUpdate
from backend.schemas.proxy import ProxyIn, ProxyOut, ProxyUpdate
from backend.services import bot_api, pro
from backend.services.proxy_check import check_proxy
from backend.services.stats import (
    DashboardStats,
    Timeseries,
    collect_dashboard_stats,
    collect_timeseries,
)

router = APIRouter(prefix="/api/admin", tags=["mini-app-admin"])


async def require_admin_user(user: User = Depends(get_current_user)) -> User:
    """Gate for admin-only routes exposed inside the Mini App itself: the
    caller's Telegram user_id must be in ADMIN_TELEGRAM_IDS. There is no
    separate Admin Panel or login — see AGENTS.md 4.6."""
    if user.telegram_id not in settings.admin_telegram_ids_list:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Доступно только администраторам")
    return user


@router.get("/stats", response_model=DashboardStats)
async def stats(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    return await collect_dashboard_stats(db)


@router.get("/pro", response_model=ProSettingsOut)
async def get_pro_settings(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ProSetting:
    return await pro.get_settings(db)


@router.patch("/pro", response_model=ProSettingsOut)
async def update_pro_settings(
    payload: ProSettingsUpdate,
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ProSetting:
    row = await pro.get_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row


async def _get_proxy(db: AsyncSession, proxy_id: int) -> Proxy:
    proxy = await db.get(Proxy, proxy_id)
    if proxy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Прокси не найден")
    return proxy


@router.get("/proxies", response_model=list[ProxyOut])
async def list_proxies(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[Proxy]:
    result = await db.execute(select(Proxy).order_by(Proxy.id))
    return list(result.scalars().all())


@router.post("/proxies", response_model=ProxyOut, status_code=201)
async def create_proxy(
    payload: ProxyIn,
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Proxy:
    data = payload.model_dump(exclude={"password"})
    proxy = Proxy(
        **data,
        encrypted_password=encrypt_secret(payload.password) if payload.password else None,
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.patch("/proxies/{proxy_id}", response_model=ProxyOut)
async def update_proxy(
    proxy_id: int,
    payload: ProxyUpdate,
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Proxy:
    proxy = await _get_proxy(db, proxy_id)
    data = payload.model_dump(exclude_unset=True, exclude={"password"})
    if payload.password is not None:
        proxy.encrypted_password = encrypt_secret(payload.password) if payload.password else None
    for field, value in data.items():
        setattr(proxy, field, value)
    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.delete("/proxies/{proxy_id}", status_code=204)
async def delete_proxy(
    proxy_id: int,
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    proxy = await _get_proxy(db, proxy_id)
    await db.delete(proxy)
    await db.commit()


@router.post("/proxies/check", response_model=list[ProxyOut])
async def check_all_proxies(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[Proxy]:
    result = await db.execute(select(Proxy))
    proxies = list(result.scalars().all())

    results = await asyncio.gather(*(check_proxy(p) for p in proxies))
    now = datetime.now(UTC)
    for proxy, (status_, latency_ms) in zip(proxies, results, strict=True):
        proxy.last_status = status_
        proxy.last_latency_ms = latency_ms
        proxy.last_checked_at = now
    await db.commit()
    for proxy in proxies:
        await db.refresh(proxy)
    return proxies


# --- Charts --------------------------------------------------------------------


@router.get("/timeseries", response_model=Timeseries)
async def timeseries(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Timeseries:
    return await collect_timeseries(db)


# --- Users -----------------------------------------------------------------------


def mask_phone(phone: str) -> str:
    """ "+7999•••••67": enough to recognise a number, not to reuse it."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 6:
        return "•••"
    return f"+{digits[:4]}{'•' * (len(digits) - 6)}{digits[-2:]}"


def _accounts_count() -> Any:
    return (
        select(TelegramAccount.user_id, func.count().label("n"))
        .group_by(TelegramAccount.user_id)
        .subquery()
    )


def _row(user: User, accounts: int) -> AdminUserRow:
    return AdminUserRow(
        id=user.id,
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        username=user.username,
        created_at=user.created_at,
        last_seen_at=user.last_seen_at,
        pro_expires_at=user.pro_expires_at,
        has_pro=pro.has_access(user),
        accounts=accounts,
    )


@router.get("/users", response_model=AdminUserList)
async def list_users(
    q: str = Query(default="", max_length=64),
    kind: str = Query(default="all", alias="filter", pattern="^(all|pro|accounts)$"),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserList:
    counts = _accounts_count()
    n = func.coalesce(counts.c.n, 0)
    query = select(User, n).outerjoin(counts, counts.c.user_id == User.id)
    term = q.strip().removeprefix("@")
    if term.isdigit():
        query = query.where(User.telegram_id == int(term))
    elif term:
        like = f"%{term.lower()}%"
        query = query.where(
            or_(func.lower(User.username).like(like), func.lower(User.first_name).like(like))
        )
    if kind == "pro":
        query = query.where(User.pro_expires_at > datetime.now(UTC))
    elif kind == "accounts":
        query = query.where(n > 0)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(50))
    return AdminUserList(users=[_row(u, c) for u, c in rows.tuples().all()], total=total)


async def _user_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return user


async def _detail(db: AsyncSession, user: User) -> AdminUserDetail:
    accounts = list(
        (
            await db.execute(
                select(TelegramAccount)
                .where(TelegramAccount.user_id == user.id)
                .order_by(TelegramAccount.id)
            )
        ).scalars()
    )
    ids = [a.id for a in accounts]
    since_7d = datetime.now(UTC) - timedelta(days=7)

    async def per_account(model: Any, *where: Any) -> dict[int, int]:
        if not ids:
            return {}
        rows = await db.execute(
            select(model.account_id, func.count())
            .where(model.account_id.in_(ids), *where)
            .group_by(model.account_id)
        )
        return {k: int(v) for k, v in rows.tuples().all()}

    rules = await per_account(AutoresponderRule)
    campaigns = await per_account(BroadcastCampaign)
    leads = await per_account(Lead)
    replies = await per_account(AutoresponderEvent, AutoresponderEvent.created_at >= since_7d)
    inviter = await db.get(User, user.referred_by_id) if user.referred_by_id else None
    payments = (
        await db.execute(
            select(Payment).where(Payment.user_id == user.id).order_by(Payment.id.desc()).limit(20)
        )
    ).scalars()
    audit = (
        await db.execute(
            select(AdminAuditLog)
            .where(AdminAuditLog.target_user_id == user.id)
            .order_by(AdminAuditLog.id.desc())
            .limit(20)
        )
    ).scalars()
    base = _row(user, len(accounts))
    return AdminUserDetail(
        **base.model_dump(),
        trial_used_at=user.trial_used_at,
        referred_by_telegram_id=inviter.telegram_id if inviter else None,
        referrals=await db.scalar(
            select(func.count()).select_from(User).where(User.referred_by_id == user.id)
        )
        or 0,
        account_list=[
            AdminAccount(
                id=a.id,
                first_name=a.first_name,
                username=a.username,
                phone=mask_phone(a.phone),
                is_active=a.is_active,
                created_at=a.created_at,
                rules=rules.get(a.id, 0),
                campaigns=campaigns.get(a.id, 0),
                leads=leads.get(a.id, 0),
                autoreplies_7d=replies.get(a.id, 0),
            )
            for a in accounts
        ],
        payments=[
            AdminPayment(stars=p.stars, days=p.days, created_at=p.created_at) for p in payments
        ],
        audit=[
            AdminAuditEntry(
                action=e.action,
                details=e.details,
                admin_telegram_id=e.admin_telegram_id,
                created_at=e.created_at,
            )
            for e in audit
        ],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def user_detail(
    user_id: int,
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    return await _detail(db, await _user_or_404(db, user_id))


@router.post("/users/{user_id}/pro", response_model=AdminUserDetail)
async def grant_pro(
    user_id: int,
    payload: GrantProIn,
    admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    """Gift Pro days (stacking onto an active subscription). Audited."""
    user = await _user_or_404(db, user_id)
    user = await pro.grant_access(db, user.telegram_id, payload.days)
    db.add(
        AdminAuditLog(
            admin_telegram_id=admin.telegram_id,
            action="pro_grant",
            target_user_id=user.id,
            details=f"+{payload.days} дн.",
        )
    )
    await db.commit()
    if payload.notify and user.pro_expires_at is not None:
        await bot_api.send_message(
            user.telegram_id,
            f"🎁 Вам подарен <b>Автопилот Pro</b> на {payload.days} дн. — "
            f"активен до {user.pro_expires_at:%d.%m.%Y}.",
        )
    return await _detail(db, user)


@router.delete("/users/{user_id}/pro", response_model=AdminUserDetail)
async def revoke_pro(
    user_id: int,
    admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    """Ends Pro right now (e.g. a mistaken gift). Audited."""
    user = await _user_or_404(db, user_id)
    user.pro_expires_at = datetime.now(UTC)
    db.add(
        AdminAuditLog(
            admin_telegram_id=admin.telegram_id,
            action="pro_revoke",
            target_user_id=user.id,
            details="Pro отключён",
        )
    )
    await db.commit()
    await db.refresh(user)
    return await _detail(db, user)
