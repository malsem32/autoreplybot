import re
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def parse_hhmm(value: str) -> time:
    match = _HHMM.match(value)
    if not match:
        raise ValueError("время должно быть в формате ЧЧ:ММ")
    return time(int(match.group(1)), int(match.group(2)))


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def is_within_schedule(
    days: list[int], start: str, end: str, timezone: str, now: datetime | None = None
) -> bool:
    """True if `now` falls into the working-hours window of an autoreply rule.

    `days` are weekdays (0 = Monday) on which the window *starts*; a window
    whose end is not after its start wraps past midnight (19:00–09:00 means
    "from 19:00 until 09:00 the next morning"). start == end means all day.
    """
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    local = (now or datetime.now(UTC)).astimezone(tz)
    start_t, end_t = parse_hhmm(start), parse_hhmm(end)
    current = local.time().replace(second=0, microsecond=0)
    weekday = local.weekday()

    if start_t == end_t:
        return weekday in days
    if start_t < end_t:
        return weekday in days and start_t <= current < end_t
    # Overnight window: the evening part belongs to today, the morning part
    # to the window that started yesterday.
    if current >= start_t:
        return weekday in days
    if current < end_t:
        return (weekday - 1) % 7 in days
    return False
