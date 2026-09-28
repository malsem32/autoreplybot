from pydantic import BaseModel, Field, computed_field, field_validator

from backend.core.uploads import photo_url
from backend.services.schedule import parse_hhmm, valid_timezone

# Telegram's own limits: 4096 chars per message, 10 items per album.
MAX_TEXT_LENGTH = 4096
MAX_PHOTOS = 10

# Pro options; the API rejects enabling them without Pro (backend/api/autoresponder.py).
PRO_RULE_FIELDS = (
    "schedule_enabled",
    "new_contacts_only",
    "skip_if_owner_active_minutes",
    "typing_delay_seconds",
    "notify_owner",
    "ai_reply",
)


class _RuleOptionsValidators(BaseModel):
    @field_validator("schedule_start", "schedule_end", check_fields=False)
    @classmethod
    def _check_time(cls, value: str | None) -> str | None:
        if value is not None:
            parse_hhmm(value)
        return value

    @field_validator("timezone", check_fields=False)
    @classmethod
    def _check_timezone(cls, value: str | None) -> str | None:
        if value is not None and not valid_timezone(value):
            raise ValueError("неизвестный часовой пояс")
        return value

    @field_validator("schedule_days", check_fields=False)
    @classmethod
    def _check_days(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        if any(d < 0 or d > 6 for d in value):
            raise ValueError("дни недели — числа от 0 (пн) до 6 (вс)")
        return sorted(set(value))


class AutoresponderRuleIn(_RuleOptionsValidators):
    is_enabled: bool = True
    trigger_type: str = Field(pattern="^(all|keywords)$", default="all")
    keywords: list[str] = Field(default_factory=list)
    match_mode: str = Field(pattern="^(contains|word|exact)$", default="contains")
    scope: str = Field(pattern="^(private|groups|all)$", default="private")
    response_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    # Upload refs (path / URL / filename from POST /api/uploads/photo).
    photos: list[str] = Field(default_factory=list, max_length=MAX_PHOTOS)
    cooldown_seconds: int = Field(ge=3600, default=3600)  # min 1h, see AGENTS.md 4.3

    schedule_enabled: bool = False
    schedule_days: list[int] = Field(default_factory=lambda: list(range(7)))
    schedule_start: str = "19:00"
    schedule_end: str = "09:00"
    timezone: str = "Europe/Moscow"
    new_contacts_only: bool = False
    skip_if_owner_active_minutes: int = Field(ge=0, le=24 * 60, default=0)
    typing_delay_seconds: int = Field(ge=0, le=30, default=0)
    notify_owner: bool = False
    ai_reply: bool = False


class AutoresponderRuleUpdate(_RuleOptionsValidators):
    is_enabled: bool | None = None
    trigger_type: str | None = Field(pattern="^(all|keywords)$", default=None)
    keywords: list[str] | None = None
    match_mode: str | None = Field(pattern="^(contains|word|exact)$", default=None)
    scope: str | None = Field(pattern="^(private|groups|all)$", default=None)
    response_text: str | None = Field(min_length=1, max_length=MAX_TEXT_LENGTH, default=None)
    # Replaces the whole photo list when given; [] removes all photos.
    photos: list[str] | None = Field(max_length=MAX_PHOTOS, default=None)
    cooldown_seconds: int | None = Field(ge=3600, default=None)

    schedule_enabled: bool | None = None
    schedule_days: list[int] | None = None
    schedule_start: str | None = None
    schedule_end: str | None = None
    timezone: str | None = None
    new_contacts_only: bool | None = None
    skip_if_owner_active_minutes: int | None = Field(ge=0, le=24 * 60, default=None)
    typing_delay_seconds: int | None = Field(ge=0, le=30, default=None)
    notify_owner: bool | None = None
    ai_reply: bool | None = None


class AutoresponderRuleOut(BaseModel):
    id: int
    account_id: int
    is_enabled: bool
    trigger_type: str
    keywords: list[str]
    match_mode: str
    scope: str
    response_text: str
    cooldown_seconds: int
    photo_paths: list[str] = Field(exclude=True, default_factory=list)

    schedule_enabled: bool
    schedule_days: list[int]
    schedule_start: str
    schedule_end: str
    timezone: str
    new_contacts_only: bool
    skip_if_owner_active_minutes: int
    typing_delay_seconds: int
    notify_owner: bool
    ai_reply: bool
    # Autoreplies sent by this rule during the last 7 days (filled by the API).
    replies_7d: int = 0

    class Config:
        from_attributes = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_urls(self) -> list[str]:
        return [photo_url(p) for p in self.photo_paths or []]


class RuleTestIn(BaseModel):
    text: str = Field(max_length=MAX_TEXT_LENGTH)
    in_group: bool = False  # simulate a mention in a group instead of a private message


class RuleTestVerdict(BaseModel):
    rule_id: int
    matched: bool
    keyword: str | None  # the keyword that fired ("" = "any message")
    blocked_by: str | None  # why a matching rule would stay silent right now


class RuleTestOut(BaseModel):
    answer_rule_id: int | None
    note: str
    verdicts: list[RuleTestVerdict]
