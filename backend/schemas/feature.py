from datetime import datetime

from pydantic import BaseModel, Field


class TagFeatureSettingsOut(BaseModel):
    stars_price: int
    duration_days: int

    class Config:
        from_attributes = True


class TagFeatureSettingsUpdate(BaseModel):
    stars_price: int | None = Field(ge=1, default=None)
    duration_days: int | None = Field(ge=1, default=None)


class TagFeatureStatusOut(BaseModel):
    has_access: bool
    is_admin: bool
    expires_at: datetime | None
    stars_price: int
    duration_days: int


class TagFeatureInvoiceOut(BaseModel):
    invoice_link: str
