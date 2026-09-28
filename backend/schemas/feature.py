from datetime import datetime

from pydantic import BaseModel, Field


class ProSettingsOut(BaseModel):
    stars_price: int
    duration_days: int
    referral_bonus_days: int

    class Config:
        from_attributes = True


class ProSettingsUpdate(BaseModel):
    stars_price: int | None = Field(ge=1, default=None)
    duration_days: int | None = Field(ge=1, default=None)
    referral_bonus_days: int | None = Field(ge=0, default=None)


class ProStatusOut(BaseModel):
    has_access: bool
    is_admin: bool
    expires_at: datetime | None
    stars_price: int
    duration_days: int
    features: list[str]
    max_photos: int
    free_max_rules: int
    free_max_campaigns: int


class ProInvoiceOut(BaseModel):
    invoice_link: str


class ReferralStatsOut(BaseModel):
    link: str
    invited_count: int
    paid_count: int
    days_earned: int
    bonus_days: int
