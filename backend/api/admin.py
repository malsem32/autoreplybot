from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.db.session import get_db
from backend.models.feature_settings import TagFeatureSetting
from backend.models.user import User
from backend.schemas.feature import TagFeatureSettingsOut, TagFeatureSettingsUpdate
from backend.services import tag_feature
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


@router.get("/tag-feature", response_model=TagFeatureSettingsOut)
async def get_tag_feature_settings(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TagFeatureSetting:
    return await tag_feature.get_settings(db)


@router.patch("/tag-feature", response_model=TagFeatureSettingsOut)
async def update_tag_feature_settings(
    payload: TagFeatureSettingsUpdate,
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TagFeatureSetting:
    row = await tag_feature.get_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row
