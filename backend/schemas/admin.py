from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserRow(BaseModel):
    id: int
    telegram_id: int
    first_name: str | None
    username: str | None
    created_at: datetime
    last_seen_at: datetime | None
    pro_expires_at: datetime | None
    has_pro: bool
    accounts: int


class AdminUserList(BaseModel):
    users: list[AdminUserRow]
    total: int


class AdminAccount(BaseModel):
    id: int
    first_name: str | None
    username: str | None
    phone: str  # masked: the admin section never shows full numbers
    is_active: bool
    created_at: datetime
    rules: int
    campaigns: int
    leads: int
    autoreplies_7d: int


class AdminPayment(BaseModel):
    stars: int
    days: int
    created_at: datetime


class AdminAuditEntry(BaseModel):
    action: str
    details: str
    admin_telegram_id: int
    created_at: datetime


class AdminUserDetail(AdminUserRow):
    trial_used_at: datetime | None
    referred_by_telegram_id: int | None
    referrals: int
    account_list: list[AdminAccount]
    payments: list[AdminPayment]
    audit: list[AdminAuditEntry]


class GrantProIn(BaseModel):
    days: int = Field(ge=1, le=3650)
    notify: bool = True
