from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.timeutil import as_utc
from backend.models.feature_settings import ProSetting
from backend.models.user import User

SETTINGS_ID = 1

# Free-plan limits; Pro lifts them (AGENTS.md 4.13). Enforced in the API on
# create/update and re-checked by the worker where it matters at send time.
FREE_MAX_PHOTOS = 1
PRO_MAX_PHOTOS = 10  # Telegram's album limit
FREE_MAX_RULES_PER_ACCOUNT = 3
FREE_MAX_CAMPAIGNS_PER_ACCOUNT = 3

# Human-readable list shown in the Mini App paywall.
PRO_FEATURES = [
    "Альбомы до 10 фото в одном сообщении",
    "Теги случайных участников в рассылках",
    "Защита от пересылки и сохранения сообщений",
    "Безлимит правил автоответа и рассылок",
]


async def get_settings(db: AsyncSession) -> ProSetting:
    """Returns the singleton price/duration row, creating it with defaults
    if a fresh DB hasn't been migrated through the seed insert."""
    row = await db.get(ProSetting, SETTINGS_ID)
    if row is None:
        row = ProSetting(id=SETTINGS_ID)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def is_admin(user: User) -> bool:
    return user.telegram_id in settings.admin_telegram_ids_list


def has_access(user: User) -> bool:
    """Admins always have Pro; everyone else needs an unexpired purchase."""
    if is_admin(user):
        return True
    expires_at = as_utc(user.pro_expires_at)
    return expires_at is not None and expires_at > datetime.now(UTC)


def max_photos(user: User) -> int:
    return PRO_MAX_PHOTOS if has_access(user) else FREE_MAX_PHOTOS


async def grant_access(db: AsyncSession, telegram_id: int, duration_days: int) -> User:
    """Extends `pro_expires_at` from now or from the current expiry,
    whichever is later, so early renewals stack instead of being wasted.
    Creates the User if they paid via the bot's /pro before ever opening
    the Mini App."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id)
        db.add(user)

    now = datetime.now(UTC)
    current_expiry = as_utc(user.pro_expires_at)
    base = current_expiry if current_expiry and current_expiry > now else now
    user.pro_expires_at = base + timedelta(days=duration_days)
    await db.commit()
    await db.refresh(user)
    return user


def invoice_payload(telegram_id: int, duration_days: int) -> str:
    return f"pro:{telegram_id}:{duration_days}"


def parse_invoice_payload(payload: str) -> tuple[int, int] | None:
    """Returns (telegram_id, duration_days). Accepts the legacy
    "tag_broadcast:" prefix of invoices issued before Pro existed."""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] not in {"pro", "tag_broadcast"}:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def invoice_params(stars_price: int, duration_days: int, payload: str) -> dict:
    """Shared by the Mini App (createInvoiceLink) and the bot's /pro command
    (sendInvoice) so both sell exactly the same thing."""
    return {
        "title": "Автопилот Pro",
        "description": (
            f"Pro на {duration_days} дн.: альбомы до 10 фото, теги участников, "
            "защита от пересылки, безлимит правил и рассылок."
        ),
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": "Pro", "amount": stars_price}],
    }
