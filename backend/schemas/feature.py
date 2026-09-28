from datetime import datetime

from pydantic import BaseModel, Field


class ProSettingsOut(BaseModel):
    stars_price: int
    duration_days: int
    quarter_stars_price: int
    year_stars_price: int
    trial_days: int
    referral_bonus_days: int

    class Config:
        from_attributes = True


class ProSettingsUpdate(BaseModel):
    stars_price: int | None = Field(ge=1, default=None)
    duration_days: int | None = Field(ge=1, default=None)
    quarter_stars_price: int | None = Field(ge=0, default=None)  # 0 hides the plan
    year_stars_price: int | None = Field(ge=0, default=None)
    trial_days: int | None = Field(ge=0, le=30, default=None)  # 0 disables the trial
    referral_bonus_days: int | None = Field(ge=0, default=None)


class ProPlanOut(BaseModel):
    id: str
    title: str
    days: int
    stars: int
    # Saving vs. buying the base plan repeatedly, in percent (0 for the base plan).
    discount_percent: int


class ProFeatureGroupOut(BaseModel):
    title: str
    items: list[str]


class ProStatusOut(BaseModel):
    has_access: bool
    is_admin: bool
    expires_at: datetime | None
    stars_price: int
    duration_days: int
    plans: list[ProPlanOut]
    trial_available: bool
    trial_days: int
    features: list[str]
    feature_groups: list[ProFeatureGroupOut]
    max_photos: int
    free_max_rules: int
    free_max_campaigns: int
    bot_username: str  # for the "Отправлено через @…" signature preview


class ProInvoiceIn(BaseModel):
    plan: str = "month"


class ProInvoiceOut(BaseModel):
    invoice_link: str


class ReferralStatsOut(BaseModel):
    link: str
    invited_count: int
    paid_count: int
    days_earned: int
    bonus_days: int
