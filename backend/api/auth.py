import asyncio
import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw import functions
from pyrogram.raw import types as raw_types
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.security import decrypt_secret, encrypt_session
from backend.db.session import get_db
from backend.models.proxy import Proxy
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.auth import (
    CheckPasswordRequest,
    QrPollResponse,
    QrStartResponse,
    SendCodeRequest,
    SendCodeResponse,
    SignInRequest,
    TelegramAccountOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pending pyrogram clients keyed by phone (SMS-code flow) or a generated
# request_id (QR flow), alive only during the login flow. A single-process
# MVP store; move to a per-worker registry keyed via Redis before running
# more than one backend replica.
_pending_clients: dict[str, Client] = {}
_qr_sessions: dict[str, dict] = {}

QR_TOKEN_TTL_SECONDS = 30


def _new_client(name: str, proxy: dict | None = None) -> Client:
    return Client(
        name=name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        in_memory=True,
        proxy=proxy,
    )


async def _pick_send_code_proxy(db: AsyncSession) -> dict | None:
    """Picks a random active proxy for `/send_code` only (per AGENTS.md:
    routing the code request through a rotating proxy pool, instead of
    always the VPS's own IP, reduces false-positive anti-fraud SMS
    suppression on some numbers — see the note on this in chat/AGENTS.md
    4.1). Prefers proxies whose last liveness check passed."""
    result = await db.execute(
        select(Proxy)
        .where(Proxy.is_active.is_(True))
        .order_by((Proxy.last_status == "alive").desc(), func.random())
        .limit(1)
    )
    proxy = result.scalar_one_or_none()
    if proxy is None:
        return None

    return {
        "scheme": proxy.protocol,
        "hostname": proxy.host,
        "port": proxy.port,
        "username": proxy.username,
        "password": decrypt_secret(proxy.encrypted_password) if proxy.encrypted_password else None,
    }


@router.get("/accounts", response_model=list[TelegramAccountOut])
async def list_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TelegramAccount]:
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.user_id == user.id))
    return list(result.scalars().all())


@router.post("/send_code", response_model=SendCodeResponse)
async def send_code(
    payload: SendCodeRequest, db: AsyncSession = Depends(get_db)
) -> SendCodeResponse:
    proxy = await _pick_send_code_proxy(db)
    client = _new_client(f"login_{payload.phone}", proxy=proxy)
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

    _pending_clients.pop(payload.phone, None)
    return await _finalize_login(db, user, client)


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

    _pending_clients.pop(payload.phone, None)
    return await _finalize_login(db, user, client)


def _qr_url(token: bytes) -> str:
    return "tg://login?token=" + base64.urlsafe_b64encode(token).decode().rstrip("=")


async def _export_login_token(client: Client):
    return await client.invoke(
        functions.auth.ExportLoginToken(
            api_id=settings.api_id, api_hash=settings.api_hash, except_ids=[]
        )
    )


@router.post("/qr/start", response_model=QrStartResponse)
async def qr_start(_user: User = Depends(get_current_user)) -> QrStartResponse:
    """Starts a Telegram QR login (`auth.exportLoginToken`). The frontend
    renders `qr_url` as a QR code for the user to scan with the official
    Telegram app; poll `/qr/{request_id}/poll` for the outcome."""
    request_id = uuid.uuid4().hex
    client = _new_client(f"qr_{request_id}")
    await client.connect()

    event = asyncio.Event()

    async def _on_raw_update(_: Client, update, __, ___) -> None:
        if isinstance(update, raw_types.UpdateLoginToken):
            event.set()

    client.add_handler(RawUpdateHandler(_on_raw_update))

    try:
        result = await _export_login_token(client)
    except Exception as exc:
        await client.disconnect()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    if not isinstance(result, raw_types.auth.LoginToken):
        await client.disconnect()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unexpected login token response")

    _qr_sessions[request_id] = {"client": client, "event": event}
    return QrStartResponse(request_id=request_id, qr_url=_qr_url(result.token))


@router.get("/qr/{request_id}/poll", response_model=QrPollResponse)
async def qr_poll(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QrPollResponse:
    session = _qr_sessions.get(request_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown or expired qr session")

    client: Client = session["client"]
    event: asyncio.Event = session["event"]

    if not event.is_set():
        return QrPollResponse(status="pending")
    event.clear()

    try:
        result = await _export_login_token(client)
    except Exception as exc:
        await client.disconnect()
        _qr_sessions.pop(request_id, None)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    if isinstance(result, raw_types.auth.LoginTokenSuccess):
        account = await _finalize_login(db, user, client)
        _qr_sessions.pop(request_id, None)
        return QrPollResponse(status="success", account=account)

    if isinstance(result, raw_types.auth.LoginTokenMigrateTo):
        # The account lives on a different data center than this client
        # connected to. Reliably re-homing an in-flight Pyrogram client to
        # another DC needs storage internals that vary by version, so we
        # take the safe route: drop this attempt and have the frontend
        # restart the QR flow (a fresh client picks the right DC itself
        # once it has seen this hint). Rare for accounts on the default DC.
        await client.disconnect()
        _qr_sessions.pop(request_id, None)
        return QrPollResponse(status="restart")

    # Still LoginToken: not confirmed yet, possibly refreshed — keep polling.
    _qr_sessions[request_id] = {"client": client, "event": event}
    return QrPollResponse(status="pending", qr_url=_qr_url(result.token))


async def _finalize_login(db: AsyncSession, user: User, client: Client) -> TelegramAccount:
    me = await client.get_me()
    session_string = await client.export_session_string()
    await client.disconnect()

    account = TelegramAccount(
        user_id=user.id,
        phone=me.phone_number or "",
        encrypted_session=encrypt_session(session_string),
        is_active=True,
        first_name=me.first_name,
        username=me.username,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account
