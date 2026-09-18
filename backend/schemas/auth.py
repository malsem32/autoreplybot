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
