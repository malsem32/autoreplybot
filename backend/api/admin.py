import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.security import encrypt_secret
from backend.db.session import get_db
from backend.models.proxy import Proxy
from backend.models.user import User
from backend.schemas.proxy import ProxyIn, ProxyOut, ProxyUpdate
from backend.services.proxy_check import check_proxy
from backend.services.stats import DashboardStats, collect_dashboard_stats

router = APIRouter(prefix="/api/admin", tags=["mini-app-admin"])


async def require_admin_user(user: User = Depends(get_current_user)) -> User:
    """Gate for admin-only routes exposed inside the Mini App itself: the
    caller's Telegram user_id must be in ADMIN_TELEGRAM_IDS. There is no
    separate Admin Panel or login — see AGENTS.md 4.6."""
    if user.telegram_id not in settings.admin_telegram_ids_list:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not an admin")
    return user


@router.get("/stats", response_model=DashboardStats)
async def stats(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    return await collect_dashboard_stats(db)


async def _get_proxy(db: AsyncSession, proxy_id: int) -> Proxy:
    proxy = await db.get(Proxy, proxy_id)
    if proxy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "proxy not found")
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
