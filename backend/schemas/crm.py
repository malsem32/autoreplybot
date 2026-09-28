from datetime import datetime

from pydantic import BaseModel, Field


class LeadOut(BaseModel):
    id: int
    peer_id: int
    name: str
    username: str | None
    last_text: str
    messages_count: int
    status: str
    note: str
    created_at: datetime
    last_message_at: datetime

    class Config:
        from_attributes = True


class LeadListOut(BaseModel):
    leads: list[LeadOut]
    counts: dict[str, int]  # per status


class LeadUpdate(BaseModel):
    status: str | None = Field(pattern="^(new|in_work|done)$", default=None)
    note: str | None = Field(max_length=1000, default=None)


class TeamMemberOut(BaseModel):
    id: int
    display_name: str
    created_at: datetime


class TeamOut(BaseModel):
    members: list[TeamMemberOut]
    max_members: int


class TeamInviteOut(BaseModel):
    link: str
    expires_at: datetime


class MeOut(BaseModel):
    weekly_digest: bool


class MeUpdate(BaseModel):
    weekly_digest: bool | None = None
