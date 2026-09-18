from fastapi import APIRouter, Depends, HTTPException, status
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.security import encrypt_session
from backend.db.session import get_db
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.auth import (
    CheckPasswordRequest,
    SendCodeRequest,
    SendCodeResponse,
    SignInRequest,
    TelegramAccountOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pending pyrogram clients keyed by phone, alive only during the login flow.
# A single-process MVP store; move to a per-worker registry keyed via Redis
# before running more than one backend replica.
_pending_clients: dict[str, Client] = {}


def _new_client(phone: str) -> Client:
    return Client(
        name=f"login_{phone}",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        in_memory=True,
    )


@router.post("/send_code", response_model=SendCodeResponse)
async def send_code(payload: SendCodeRequest) -> SendCodeResponse:
    client = _new_client(payload.phone)
    await client.connect()
    try:
        sent = await client.send_code(payload.phone)
    except Exception as exc:
        await client.disconnect()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    _pending_clients[payload.phone] = client
    return SendCodeResponse(phone_code_hash=sent.phone_code_hash)


@router.post("/sign_in", response_model=TelegramAccountOut)
async def sign_in(
    payload: SignInRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TelegramAccount:
    client = _pending_clients.get(payload.phone)
    if client is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "call send_code first")

    try:
        await client.sign_in(payload.phone, payload.phone_code_hash, payload.code)
    except SessionPasswordNeeded:
        # Client stays pending; frontend must call /check_password next.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "2fa_required") from None
    except Exception as exc:
        await client.disconnect()
        _pending_clients.pop(payload.phone, None)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return await _finalize_login(db, user, payload.phone, client)


@router.post("/check_password", response_model=TelegramAccountOut)
async def check_password(
    payload: CheckPasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TelegramAccount:
    client = _pending_clients.get(payload.phone)
    if client is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "call send_code/sign_in first")

    try:
        await client.check_password(payload.password)
    except Exception as exc:
        await client.disconnect()
        _pending_clients.pop(payload.phone, None)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return await _finalize_login(db, user, payload.phone, client)


async def _finalize_login(
    db: AsyncSession, user: User, phone: str, client: Client
) -> TelegramAccount:
    me = await client.get_me()
    session_string = await client.export_session_string()
    await client.disconnect()
    _pending_clients.pop(phone, None)

    account = TelegramAccount(
        user_id=user.id,
        phone=phone,
        encrypted_session=encrypt_session(session_string),
        is_active=True,
        first_name=me.first_name,
        username=me.username,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account
