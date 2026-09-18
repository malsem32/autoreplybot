from pydantic import BaseModel, Field


class BroadcastCampaignIn(BaseModel):
    title: str
    text_template: str
    target_chat_ids: list[int]
    interval_minutes: int = Field(ge=1, default=60)


class BroadcastCampaignOut(BroadcastCampaignIn):
    id: int
    account_id: int
    status: str

    class Config:
        from_attributes = True
