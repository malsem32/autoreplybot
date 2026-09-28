from dataclasses import dataclass
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

QUARTER_DAYS = 90
YEAR_DAYS = 365

# Human-readable list shown in the Mini App paywall, grouped for display.
PRO_FEATURE_GROUPS: list[dict] = [
    {
        "title": "Автоответчик",
        "items": [
            "Расписание: отвечать только в нерабочее время",
            "Только новым собеседникам",
            "Не вмешиваться, когда вы сами в диалоге",
            "Эффект «печатает…» перед ответом",
            "Уведомления в бот о новых обращениях",
        ],
    },
    {
        "title": "Рассылки",
        "items": [
            "Статистика доставки по каждому чату",
            "Автоотключение чатов, куда не доходит",
            "Отчёт в бот после каждой рассылки",
            "Теги случайных участников",
            "Защита от пересылки и сохранения",
        ],
    },
    {
        "title": "Без ограничений",
        "items": [
            "Альбомы до 10 фото в одном сообщении",
            "Свои шаблоны сообщений",
            "Безлимит правил и рассылок",
        ],
    },
]
PRO_FEATURES = [item for group in PRO_FEATURE_GROUPS for item in group["items"]]


@dataclass(frozen=True)
class Plan:
    id: str  # month | quarter | year
    title: str
    days: int
    stars: int


def plans(row: ProSetting) -> list[Plan]:
    """Purchasable plans; a plan priced at 0 is hidden."""
    candidates = [
        Plan("month", f"{row.duration_days} дней", row.duration_days, row.stars_price),
        Plan("quarter", "3 месяца", QUARTER_DAYS, row.quarter_stars_price),
        Plan("year", "Год", YEAR_DAYS, row.year_stars_price),
    ]
    return [p for p in candidates if p.stars > 0 and p.days > 0]


def find_plan(row: ProSetting, plan_id: str) -> Plan | None:
    return next((p for p in plans(row) if p.id == plan_id), None)


def price_matches(row: ProSetting, days: int, stars: int) -> bool:
    """Checked at pre-checkout: the invoice must still match a current plan
    (the admin may have changed prices since the invoice was created)."""
    return any(p.days == days and p.stars == stars for p in plans(row))


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


def trial_available(user: User, row: ProSetting) -> bool:
    return row.trial_days > 0 and user.trial_used_at is None and not has_access(user)


def _extend(user: User, days: int) -> None:
    now = datetime.now(UTC)
    current_expiry = as_utc(user.pro_expires_at)
    base = current_expiry if current_expiry and current_expiry > now else now
    user.pro_expires_at = base + timedelta(days=days)


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

    _extend(user, duration_days)
    await db.commit()
    await db.refresh(user)
    return user


async def start_trial(db: AsyncSession, user: User) -> bool:
    """Grants the one-time free trial. Returns False if not available."""
    row = await get_settings(db)
    if not trial_available(user, row):
        return False
    user.trial_used_at = datetime.now(UTC)
    _extend(user, row.trial_days)
    await db.commit()
    await db.refresh(user)
    return True


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
            f"Pro на {duration_days} дн.: расписание и умные автоответы, уведомления, "
            "статистика рассылок, альбомы, шаблоны и безлимит."
        ),
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": "Pro", "amount": stars_price}],
    }
