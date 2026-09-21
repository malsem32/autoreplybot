from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.db.session import get_db
from backend.models.user import User
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
