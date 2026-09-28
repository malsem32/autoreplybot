from typing import Literal

from pydantic import BaseModel, Field


class SendCodeRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=32)


class SentCodeInfo(BaseModel):
    """Where Telegram delivered the login code, so the Mini App can tell the
    user where to look (most often it is the Telegram app itself, not SMS)."""

    phone: str  # normalized, digits only — send it back unchanged in later calls
    phone_code_hash: str
    code_type: str  # app | sms | call | flash_call | missed_call | fragment_sms | email_code | ...
    next_type: str | None = None  # what /resend_code would switch delivery to
    timeout: int | None = None  # seconds before /resend_code is allowed


class ResendCodeRequest(BaseModel):
    phone: str
    phone_code_hash: str


class CancelLoginRequest(BaseModel):
    phone: str


class SignInRequest(BaseModel):
    phone: str
    phone_code_hash: str
    code: str = Field(min_length=1, max_length=32)


class CheckPasswordRequest(BaseModel):
    phone: str
    password: str = Field(min_length=1)


class QrPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class TelegramAccountOut(BaseModel):
    id: int
    phone: str
    is_active: bool
    first_name: str | None
    username: str | None

    class Config:
        from_attributes = True


class TelegramAccountUpdate(BaseModel):
    is_active: bool


class LoginResult(BaseModel):
    """Outcome of a login step: either the account is connected, or the
    account has two-step verification and the password step comes next."""

    status: Literal["success", "password_required"]
    account: TelegramAccountOut | None = None
    password_hint: str | None = None


class QrStartResponse(BaseModel):
    request_id: str
    qr_url: str
    expires_in: int


class QrPollResponse(BaseModel):
    status: Literal["pending", "success", "password_required", "restart"]
    qr_url: str | None = None
    expires_in: int | None = None
    account: TelegramAccountOut | None = None
    password_hint: str | None = None
