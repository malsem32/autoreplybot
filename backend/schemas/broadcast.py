from datetime import datetime

from pydantic import BaseModel, Field, computed_field, model_validator

from backend.schemas.autoresponder import _photo_url


class BroadcastCampaignIn(BaseModel):
    title: str
    text_template: str
    photo_path: str | None = None
    target_chats: list[str]
    schedule_type: str = Field(pattern="^(recurring|once)$", default="recurring")
    interval_minutes: int = Field(ge=1, default=60)
    scheduled_at: datetime | None = None

    @model_validator(mode="after")
    def _require_scheduled_at_for_once(self) -> "BroadcastCampaignIn":
        if self.schedule_type == "once" and self.scheduled_at is None:
            raise ValueError("scheduled_at is required when schedule_type is 'once'")
        return self


class BroadcastCampaignUpdate(BaseModel):
    title: str | None = None
    text_template: str | None = None
    photo_path: str | None = None
    remove_photo: bool = False
    target_chats: list[str] | None = None
    schedule_type: str | None = Field(pattern="^(recurring|once)$", default=None)
    interval_minutes: int | None = Field(ge=1, default=None)
    scheduled_at: datetime | None = None


class BroadcastCampaignOut(BaseModel):
    id: int
    account_id: int
    title: str
    text_template: str
    photo_path: str | None = Field(exclude=True, default=None)
    target_chats: list[str]
    schedule_type: str
    interval_minutes: int
    scheduled_at: datetime | None
    status: str

    class Config:
        from_attributes = True

    @computed_field
    @property
    def photo_url(self) -> str | None:
        return _photo_url(self.photo_path)


class BroadcastLogOut(BaseModel):
    id: int
    chat_id: int
    sent_at: datetime
    status: str
    error_message: str | None

    class Config:
        from_attributes = True
