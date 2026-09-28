from datetime import UTC, datetime


def as_utc(value: datetime | None) -> datetime | None:
    """Treats naive datetimes (e.g. from a DB driver without tz support)
    as UTC so they compare safely with `datetime.now(UTC)`."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
