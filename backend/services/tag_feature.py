from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.feature_settings import TagFeatureSetting
from backend.models.user import User

SETTINGS_ID = 1


async def get_settings(db: AsyncSession) -> TagFeatureSetting:
    """Returns the singleton price/duration row, creating it with defaults
    if a fresh DB hasn't been migrated through the seed insert."""
    row = await db.get(TagFeatureSetting, SETTINGS_ID)
    if row is None:
        row = TagFeatureSetting(id=SETTINGS_ID)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def is_admin(user: User) -> bool:
    return user.telegram_id in settings.admin_telegram_ids_list


def has_access(user: User) -> bool:
    """Admins always have access; everyone else needs an unexpired purchase."""
    if is_admin(user):
        return True
    return user.tag_feature_expires_at is not None and user.tag_feature_expires_at > datetime.now(
        UTC
    )


async def grant_access(db: AsyncSession, telegram_id: int, duration_days: int) -> User | None:
    """Extends `tag_feature_expires_at` from now or from the current expiry,
    whichever is later, so early renewals stack instead of being wasted."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None

    now = datetime.now(UTC)
    current_expiry = user.tag_feature_expires_at
    base = current_expiry if current_expiry and current_expiry > now else now
    user.tag_feature_expires_at = base + timedelta(days=duration_days)
    await db.commit()
    await db.refresh(user)
    return user
