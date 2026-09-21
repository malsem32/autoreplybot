from pydantic import BaseModel


class SendCodeRequest(BaseModel):
    phone: str


class SendCodeResponse(BaseModel):
    phone_code_hash: str


class SignInRequest(BaseModel):
    phone: str
    phone_code_hash: str
    code: str


class CheckPasswordRequest(BaseModel):
    phone: str
    password: str


class TelegramAccountOut(BaseModel):
    id: int
    phone: str
    is_active: bool
    first_name: str | None
    username: str | None

    class Config:
        from_attributes = True


class QrStartResponse(BaseModel):
    request_id: str
    qr_url: str


class QrPollResponse(BaseModel):
    status: str  # pending | success | restart
    qr_url: str | None = None
    account: TelegramAccountOut | None = None
