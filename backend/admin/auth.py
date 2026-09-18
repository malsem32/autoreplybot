import bcrypt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.security import create_admin_token

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str


@router.post("/login", response_model=AdminLoginResponse)
async def login(payload: AdminLoginRequest) -> AdminLoginResponse:
    valid_username = payload.username == settings.admin_username
    valid_password = valid_username and bcrypt.checkpw(
        payload.password.encode(), settings.admin_password_hash.encode()
    )
    if not (valid_username and valid_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    token = create_admin_token(admin_id=payload.username, role="superadmin")
    return AdminLoginResponse(access_token=token)
