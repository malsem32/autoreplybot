"""Vacation mode (AGENTS.md 4.17): while `TelegramAccount.away_until` is in
the future, every private message gets the away text instead of the rules.
It switches itself off when the date passes — nothing to clean up."""

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.core.timeutil import as_utc
from backend.models.telegram_account import TelegramAccount

MAX_AWAY_DAYS = 90
# Longer than a rule cooldown: people shouldn't get "I'm on vacation" on
# every message of a long conversation.
AWAY_COOLDOWN_SECONDS = 12 * 3600
DATE_PLACEHOLDER = "{дата}"

_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def is_away(account: TelegramAccount, now: datetime) -> bool:
    until = as_utc(account.away_until)
    return until is not None and until > now


def format_return_date(value: datetime, timezone: str = "Europe/Moscow") -> str:
    """ "12 октября" in the owner's timezone (the day they are back)."""
    aware = as_utc(value)
    assert aware is not None
    local = aware.astimezone(ZoneInfo(timezone))
    return f"{local.day} {_MONTHS[local.month - 1]}"


def render_away_text(text: str, until: datetime, timezone: str = "Europe/Moscow") -> str:
    return text.replace(DATE_PLACEHOLDER, format_return_date(until, timezone))
