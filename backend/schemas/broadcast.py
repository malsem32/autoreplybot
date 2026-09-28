from datetime import datetime

from pydantic import BaseModel, Field, computed_field, model_validator

from backend.core.uploads import photo_url
from backend.schemas.autoresponder import MAX_PHOTOS, MAX_TEXT_LENGTH

# Pro options; the API rejects enabling them without Pro (backend/api/broadcasts.py).
PRO_CAMPAIGN_FIELDS = (
    "tag_random_users",
    "protect_content",
    "auto_disable_failing",
    "notify_report",
    "hide_signature",
)


class BroadcastCampaignIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text_template: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    photos: list[str] = Field(default_factory=list, max_length=MAX_PHOTOS)
    target_chats: list[str] = Field(min_length=1)
    tag_random_users: bool = False
    disable_notification: bool = False
    protect_content: bool = False
    disable_link_preview: bool = False
    auto_disable_failing: bool = False
    notify_report: bool = False
    hide_signature: bool = False
    schedule_type: str = Field(pattern="^(recurring|once)$", default="recurring")
    interval_minutes: int = Field(ge=1, default=60)
    scheduled_at: datetime | None = None

    @model_validator(mode="after")
    def _require_scheduled_at_for_once(self) -> "BroadcastCampaignIn":
        if self.schedule_type == "once" and self.scheduled_at is None:
            raise ValueError("scheduled_at is required when schedule_type is 'once'")
        return self


class BroadcastCampaignUpdate(BaseModel):
    title: str | None = Field(min_length=1, max_length=255, default=None)
    text_template: str | None = Field(min_length=1, max_length=MAX_TEXT_LENGTH, default=None)
    # Replaces the whole photo list when given; [] removes all photos.
    photos: list[str] | None = Field(max_length=MAX_PHOTOS, default=None)
    target_chats: list[str] | None = Field(min_length=1, default=None)
    tag_random_users: bool | None = None
    disable_notification: bool | None = None
    protect_content: bool | None = None
    disable_link_preview: bool | None = None
    auto_disable_failing: bool | None = None
    notify_report: bool | None = None
    hide_signature: bool | None = None
    # Lets the owner bring auto-disabled chats back (only shrinking is allowed).
    disabled_targets: list[str] | None = None
    schedule_type: str | None = Field(pattern="^(recurring|once)$", default=None)
    interval_minutes: int | None = Field(ge=1, default=None)
    scheduled_at: datetime | None = None


class BroadcastCampaignOut(BaseModel):
    id: int
    account_id: int
    title: str
    text_template: str
    photo_paths: list[str] = Field(exclude=True, default_factory=list)
    target_chats: list[str]
    tag_random_users: bool
    disable_notification: bool
    protect_content: bool
    disable_link_preview: bool
    auto_disable_failing: bool
    notify_report: bool
    hide_signature: bool
    disabled_targets: list[str]
    schedule_type: str
    interval_minutes: int
    scheduled_at: datetime | None
    status: str

    class Config:
        from_attributes = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_urls(self) -> list[str]:
        return [photo_url(p) for p in self.photo_paths or []]


class BroadcastLogOut(BaseModel):
    id: int
    target: str | None = None
    chat_id: int
    sent_at: datetime
    status: str
    error_message: str | None

    class Config:
        from_attributes = True


class TargetStatsOut(BaseModel):
    """Per-chat delivery statistics of a campaign (Pro)."""

    target: str
    sent: int
    failed: int
    last_status: str | None
    last_error: str | None
    last_sent_at: datetime | None
    disabled: bool


class CampaignStatsOut(BaseModel):
    sent: int
    failed: int
    targets: list[TargetStatsOut]
