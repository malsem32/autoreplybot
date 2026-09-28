import asyncio
import base64
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pyrogram import Client, enums
from pyrogram import types as tg_types
from pyrogram.errors import RPCError, SessionPasswordNeeded
from pyrogram.raw import functions
from pyrogram.raw import types as raw_types
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.rate_limit import rate_limit
from backend.core.security import decrypt_secret, encrypt_session
from backend.core.telegram_errors import RETRYABLE_INPUT_ERRORS, error_id, to_http_error
from backend.core.uploads import delete_uploads
from backend.db.session import get_db
from backend.models.autoresponder_rule import AutoresponderEvent, AutoresponderRule
from backend.models.broadcast import BroadcastCampaign, BroadcastLog, FloodWaitEvent
from backend.models.lead import Lead
from backend.models.proxy import Proxy
from backend.models.snippet import Snippet
from backend.models.team import AccountMember, TeamInvite
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.auth import (
    CancelLoginRequest,
    CheckPasswordRequest,
    LoginResult,
    QrPasswordRequest,
    QrPollResponse,
    QrStartResponse,
    ResendCodeRequest,
    SendCodeRequest,
    SentCodeInfo,
    SignInRequest,
    TelegramAccountOut,
    TelegramAccountUpdate,
)
from backend.services import access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# A login flow (code or QR) that isn't finished within this window is
# dropped and its temporary client disconnected.
PENDING_LOGIN_TTL_SECONDS = 10 * 60

# Shown to Telegram as the name of the new session ("Devices" screen).
CLIENT_APP_VERSION = "1.0"
CLIENT_DEVICE_MODEL = "Автопилот"
CLIENT_SYSTEM_VERSION = "Web"

_LOGIN_EXPIRED = "Сессия входа устарела. Запросите код заново"

# Upper bound for a single MTProto step during login. Pyrogram keeps
# retrying a connection that can't be established; without this the Mini
# App would spin forever instead of telling the user something is wrong.
TELEGRAM_TIMEOUT_SECONDS = 25


async def _with_timeout(awaitable: Any) -> Any:
    return await asyncio.wait_for(awaitable, timeout=TELEGRAM_TIMEOUT_SECONDS)


@dataclass
class _PendingLogin:
    client: Client
    phone_code_hash: str
    expires_at: float = field(default_factory=lambda: time.monotonic() + PENDING_LOGIN_TTL_SECONDS)
    awaiting_password: bool = False


@dataclass
class _QrLogin:
    client: Client
    user_id: int
    token_expires_at: float
    token_updated: bool = False
    awaiting_password: bool = False
    expires_at: float = field(default_factory=lambda: time.monotonic() + PENDING_LOGIN_TTL_SECONDS)


# Temporary pyrogram clients alive only during a login flow. Code-flow
# entries are keyed by "<user.id>:<phone>" so two Mini App users can never
# pick up each other's half-finished login; QR entries by a random
# request_id plus an owner check. A single-process store — move it to a
# per-worker registry keyed via Redis before running more than one backend
# replica (uvicorn runs a single worker in docker-compose.yml).
_pending_logins: dict[str, _PendingLogin] = {}
_qr_logins: dict[str, _QrLogin] = {}


def normalize_phone(raw: str) -> str:
    """Reduces user input like "+7 (999) 123-45-67" to "79991234567".

    A Russian-style domestic "89XXXXXXXXX" typed without "+" is rewritten
    to "79XXXXXXXXX" — no country code starts with 89, so this can't
    misread a foreign number."""
    digits = re.sub(r"\D", "", raw)
    if "+" not in raw and len(digits) == 11 and digits.startswith("89"):
        digits = "7" + digits[1:]
    if not 7 <= len(digits) <= 15:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Неверный номер телефона. Укажите его в международном формате, например +79991234567",
        )
    return digits


def _normalize_code(raw: str) -> str:
    # Codes are often pasted as "12 345" or "12-345".
    return re.sub(r"[\s\-]", "", raw)


def _pending_key(user: User, phone: str) -> str:
    return f"{user.id}:{phone}"


def _new_client(name: str, proxy: Any = None) -> Client:
    return Client(
        name=name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        app_version=CLIENT_APP_VERSION,
        device_model=CLIENT_DEVICE_MODEL,
        system_version=CLIENT_SYSTEM_VERSION,
        lang_code="ru",
        system_lang_code="ru",
        in_memory=True,
        no_updates=False,
        proxy=proxy,
    )


async def _safe_disconnect(client: Client) -> None:
    try:
        if client.is_connected:
            await client.disconnect()
    except Exception:  # noqa: BLE001 - best-effort cleanup of a throwaway client
        logger.debug("failed to disconnect temporary login client", exc_info=True)


async def _sweep_expired_logins() -> None:
    now = time.monotonic()
    for key, pending in list(_pending_logins.items()):
        if pending.expires_at <= now:
            _pending_logins.pop(key, None)
            await _safe_disconnect(pending.client)
    for request_id, qr in list(_qr_logins.items()):
        if qr.expires_at <= now:
            _qr_logins.pop(request_id, None)
            await _safe_disconnect(qr.client)


async def _drop_pending(key: str) -> None:
    pending = _pending_logins.pop(key, None)
    if pending is not None:
        await _safe_disconnect(pending.client)


async def _drop_qr(request_id: str) -> None:
    qr = _qr_logins.pop(request_id, None)
    if qr is not None:
        await _safe_disconnect(qr.client)


async def _pick_send_code_proxy(db: AsyncSession) -> dict | None:
    """Picks a random active proxy for `/send_code` only (AGENTS.md 4.1/4.12):
    routing the code request through a proxy pool instead of always the
    VPS's own IP reduces anti-fraud SMS suppression on some numbers.
    Prefers proxies whose last liveness check passed."""
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


async def _connect_for_send_code(name: str, proxy: dict | None) -> Client:
    """Connects a fresh client for `/send_code`, falling back to a direct
    connection if a proxy from the pool fails: `Proxy.last_status` only
    reflects a bare TCP connect (AGENTS.md 4.12), so a proxy marked "alive"
    can still fail the real MTProto handshake — that shouldn't block every
    login until an admin notices and deactivates it."""
    if proxy is not None:
        client = _new_client(name, proxy=proxy)
        try:
            await _with_timeout(client.connect())
            return client
        except Exception:  # noqa: BLE001 - fall back to a direct connection
            logger.warning("send_code proxy failed, falling back to direct connection")
            await _safe_disconnect(client)
    client = _new_client(name)
    try:
        await _with_timeout(client.connect())
    except BaseException:
        await _safe_disconnect(client)
        raise
    return client


def _enum_name(value: Any) -> str | None:
    return value.name.lower() if value is not None else None


def _sent_code_info(phone: str, sent: tg_types.SentCode) -> SentCodeInfo:
    return SentCodeInfo(
        phone=phone,
        phone_code_hash=sent.phone_code_hash,
        code_type=_enum_name(sent.type) or "unknown",
        next_type=_enum_name(sent.next_type),
        timeout=sent.timeout,
    )


async def _password_hint(client: Client) -> str | None:
    try:
        return await client.get_password_hint() or None
    except Exception:  # noqa: BLE001 - the hint is optional
        return None


def _account_out(account: TelegramAccount, role: str) -> TelegramAccountOut:
    out = TelegramAccountOut.model_validate(account)
    out.role = role
    return out


@router.get("/accounts", response_model=list[TelegramAccountOut])
async def list_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TelegramAccountOut]:
    """Own accounts first, then accounts shared with the user by a team
    owner (AGENTS.md 4.16)."""
    result = await db.execute(
        select(TelegramAccount)
        .where(TelegramAccount.user_id == user.id)
        .order_by(TelegramAccount.id)
    )
    own = [_account_out(a, "owner") for a in result.scalars().all()]
    shared = [_account_out(a, "member") for a in await access.shared_accounts(db, user)]
    return own + shared


@router.patch("/accounts/{account_id}", response_model=TelegramAccountOut)
async def update_account(
    account_id: int,
    payload: TelegramAccountUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TelegramAccountOut:
    """Pauses/resumes an account. The worker picks the change up on its next
    tick and stops (or starts) the account's client (AGENTS.md 4.5). Team
    members may pause/resume too."""
    account = await access.get_account(db, user, account_id)
    if payload.is_active and not account.encrypted_session:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Сессия аккаунта утеряна — подключите его заново"
        )
    account.is_active = payload.is_active
    await db.commit()
    await db.refresh(account)
    return _account_out(account, "owner" if account.user_id == user.id else "member")


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Removes an account with its rules, campaigns and logs. The worker
    disconnects the account's client on its next tick (AGENTS.md 4.5).
    Owner only."""
    account = await access.get_account(db, user, account_id, owner_only=True)

    campaigns = list(
        (
            await db.execute(
                select(BroadcastCampaign).where(BroadcastCampaign.account_id == account.id)
            )
        ).scalars()
    )
    rules = list(
        (
            await db.execute(
                select(AutoresponderRule).where(AutoresponderRule.account_id == account.id)
            )
        ).scalars()
    )
    snippets = list(
        (await db.execute(select(Snippet).where(Snippet.account_id == account.id))).scalars()
    )
    campaign_ids = [c.id for c in campaigns]
    if campaign_ids:
        await db.execute(delete(BroadcastLog).where(BroadcastLog.campaign_id.in_(campaign_ids)))
    await db.execute(delete(AutoresponderEvent).where(AutoresponderEvent.account_id == account.id))
    await db.execute(delete(FloodWaitEvent).where(FloodWaitEvent.account_id == account.id))
    await db.execute(delete(Lead).where(Lead.account_id == account.id))
    await db.execute(delete(AccountMember).where(AccountMember.account_id == account.id))
    await db.execute(delete(TeamInvite).where(TeamInvite.account_id == account.id))
    for campaign in campaigns:
        delete_uploads(campaign.photo_paths)
        await db.delete(campaign)
    for rule in rules:
        delete_uploads(rule.photo_paths)
        await db.delete(rule)
    for snippet in snippets:
        delete_uploads(snippet.photo_paths)
        await db.delete(snippet)
    await db.flush()
    await db.delete(account)
    await db.commit()


# --- Login by code -----------------------------------------------------------


@router.post("/send_code", response_model=SentCodeInfo)
async def send_code(
    payload: SendCodeRequest,
    user: User = Depends(rate_limit("auth_code", limit=6, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> SentCodeInfo:
    await _sweep_expired_logins()
    phone = normalize_phone(payload.phone)
    key = _pending_key(user, phone)
    # A repeated request for the same number restarts the flow cleanly.
    await _drop_pending(key)

    proxy = await _pick_send_code_proxy(db)
    try:
        client = await _connect_for_send_code(f"login_{uuid.uuid4().hex}", proxy)
    except Exception as exc:
        raise to_http_error(exc) from exc

    try:
        sent = await _with_timeout(client.send_code(phone))
    except Exception as exc:
        await _safe_disconnect(client)
        raise to_http_error(exc) from exc

    if sent.type == enums.SentCodeType.SETUP_EMAIL_REQUIRED:
        # Telegram wants a login e-mail configured first, which only the
        # official apps can do. QR login sidesteps this entirely.
        await _safe_disconnect(client)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Telegram требует привязать e-mail для входа по коду. Войдите по QR-коду — "
            "это работает без e-mail",
        )

    _pending_logins[key] = _PendingLogin(client=client, phone_code_hash=sent.phone_code_hash)
    return _sent_code_info(phone, sent)


@router.post("/resend_code", response_model=SentCodeInfo)
async def resend_code(
    payload: ResendCodeRequest,
    user: User = Depends(rate_limit("auth_code", limit=6, window_seconds=600)),
) -> SentCodeInfo:
    """Asks Telegram to deliver the code via `next_type` (e.g. SMS when the
    first code went to the Telegram app)."""
    await _sweep_expired_logins()
    phone = normalize_phone(payload.phone)
    key = _pending_key(user, phone)
    pending = _pending_logins.get(key)
    if pending is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Сессия входа устарела. Запросите код заново"
        )

    try:
        sent = await _with_timeout(pending.client.resend_code(phone, pending.phone_code_hash))
    except Exception as exc:
        if error_id(exc) in {"PHONE_CODE_EXPIRED", "SEND_CODE_UNAVAILABLE", "AUTH_RESTART"}:
            await _drop_pending(key)
        raise to_http_error(exc) from exc

    pending.phone_code_hash = sent.phone_code_hash
    return _sent_code_info(phone, sent)


@router.post("/cancel", status_code=204)
async def cancel_login(
    payload: CancelLoginRequest,
    user: User = Depends(get_current_user),
) -> None:
    await _drop_pending(_pending_key(user, normalize_phone(payload.phone)))


@router.post("/sign_in", response_model=LoginResult)
async def sign_in(
    payload: SignInRequest,
    user: User = Depends(rate_limit("auth_sign_in", limit=15, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> LoginResult:
    await _sweep_expired_logins()
    phone = normalize_phone(payload.phone)
    key = _pending_key(user, phone)
    pending = _pending_logins.get(key)
    if pending is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Сессия входа устарела. Запросите код заново"
        )

    # The hash from the latest send/resend on the server wins over whatever
    # the client echoes back (it may still hold the pre-resend one).
    try:
        result = await pending.client.sign_in(
            phone, pending.phone_code_hash or payload.phone_code_hash, _normalize_code(payload.code)
        )
    except SessionPasswordNeeded:
        pending.awaiting_password = True
        return LoginResult(
            status="password_required", password_hint=await _password_hint(pending.client)
        )
    except Exception as exc:
        if error_id(exc) not in RETRYABLE_INPUT_ERRORS:
            await _drop_pending(key)
        raise to_http_error(exc) from exc

    if not isinstance(result, tg_types.User):
        # False / TermsOfService: the number has no Telegram account yet.
        await _drop_pending(key)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Этот номер не зарегистрирован в Telegram. "
            "Сначала создайте аккаунт в приложении Telegram",
        )

    _pending_logins.pop(key, None)
    account = await _finalize_login(db, user, pending.client)
    return LoginResult(status="success", account=TelegramAccountOut.model_validate(account))


@router.post("/check_password", response_model=LoginResult)
async def check_password(
    payload: CheckPasswordRequest,
    user: User = Depends(rate_limit("auth_password", limit=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> LoginResult:
    await _sweep_expired_logins()
    phone = normalize_phone(payload.phone)
    key = _pending_key(user, phone)
    pending = _pending_logins.get(key)
    if pending is None or not pending.awaiting_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Сессия входа устарела. Запросите код заново"
        )

    try:
        await pending.client.check_password(payload.password)
    except Exception as exc:
        if error_id(exc) not in RETRYABLE_INPUT_ERRORS:
            await _drop_pending(key)
        raise to_http_error(exc) from exc

    _pending_logins.pop(key, None)
    account = await _finalize_login(db, user, pending.client)
    return LoginResult(status="success", account=TelegramAccountOut.model_validate(account))


# --- Login by QR ---------------------------------------------------------------


def _qr_url(token: bytes) -> str:
    return "tg://login?token=" + base64.urlsafe_b64encode(token).decode().rstrip("=")


def _token_ttl(expires: int) -> float:
    """Converts LoginToken.expires (unix time) to a monotonic deadline."""
    return time.monotonic() + max(0, expires - int(time.time()))


async def _export_login_token(client: Client) -> Any:
    return await client.invoke(
        functions.auth.ExportLoginToken(
            api_id=settings.api_id, api_hash=settings.api_hash, except_ids=[]
        )
    )


def _watch_login_token_updates(client: Client, qr: "_QrLogin") -> None:
    """Flags `qr.token_updated` when Telegram pushes `updateLoginToken`
    (the QR was scanned and confirmed).

    A client that was only `connect()`-ed (never `start()`-ed) has no
    running dispatcher, so regular handlers would never fire — hook the
    raw update entry point on this instance instead."""
    original = client.handle_updates

    async def handle_updates(updates: Any) -> Any:
        if isinstance(updates, raw_types.UpdateShort) and isinstance(
            updates.update, raw_types.UpdateLoginToken
        ):
            qr.token_updated = True
            return None
        if isinstance(updates, (raw_types.Updates, raw_types.UpdatesCombined)) and any(
            isinstance(u, raw_types.UpdateLoginToken) for u in updates.updates
        ):
            qr.token_updated = True
        return await original(updates)

    client.handle_updates = handle_updates  # type: ignore[method-assign]


async def _migrate_and_import(client: Client, migrate: Any) -> Any:
    """Follows `auth.loginTokenMigrateTo`: reconnects this client to the
    account's home DC and imports the token there — the same DC-switch
    sequence Pyrogram itself uses for PHONE_MIGRATE in send_code."""
    dc_option = await client.get_dc_option(migrate.dc_id, ipv6=client.ipv6)
    assert client.session is not None
    await client.session.stop()
    client.session = await client.get_session(
        dc_id=migrate.dc_id,
        server_address=dc_option.ip_address,
        port=dc_option.port,
        export_authorization=False,
        temporary=True,
    )
    await client.storage.dc_id(migrate.dc_id)
    await client.storage.server_address(dc_option.ip_address)
    await client.storage.port(dc_option.port)
    await client.storage.auth_key(client.session.auth_key)  # type: ignore[union-attr]
    return await client.invoke(functions.auth.ImportLoginToken(token=migrate.token))


@router.post("/qr/start", response_model=QrStartResponse)
async def qr_start(
    user: User = Depends(rate_limit("auth_qr", limit=20, window_seconds=600)),
) -> QrStartResponse:
    """Starts a Telegram QR login (`auth.exportLoginToken`). The frontend
    renders `qr_url` as a QR code for the user to scan with the official
    Telegram app and polls `/qr/{request_id}/poll` for the outcome."""
    await _sweep_expired_logins()
    request_id = uuid.uuid4().hex
    client = _new_client(f"qr_{request_id}")
    try:
        await _with_timeout(client.connect())
    except Exception as exc:
        await _safe_disconnect(client)
        raise to_http_error(exc) from exc

    qr = _QrLogin(client=client, user_id=user.id, token_expires_at=0)
    _watch_login_token_updates(client, qr)

    try:
        result = await _with_timeout(_export_login_token(client))
    except Exception as exc:
        await _safe_disconnect(client)
        raise to_http_error(exc) from exc

    if not isinstance(result, raw_types.auth.LoginToken):
        await _safe_disconnect(client)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Неожиданный ответ Telegram, попробуйте ещё раз"
        )

    qr.token_expires_at = _token_ttl(result.expires)
    _qr_logins[request_id] = qr
    return QrStartResponse(
        request_id=request_id,
        qr_url=_qr_url(result.token),
        expires_in=max(0, result.expires - int(time.time())),
    )


def _get_owned_qr(request_id: str, user: User) -> _QrLogin:
    qr = _qr_logins.get(request_id)
    if qr is None or qr.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "QR-код устарел — обновите его")
    return qr


@router.get("/qr/{request_id}/poll", response_model=QrPollResponse)
async def qr_poll(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QrPollResponse:
    await _sweep_expired_logins()
    qr = _get_owned_qr(request_id, user)
    client = qr.client

    if qr.awaiting_password:
        return QrPollResponse(status="password_required")

    # Re-export when Telegram signalled a scan, or when the current token
    # is about to expire (the QR must be refreshed, otherwise the phone
    # reports it as expired).
    if not qr.token_updated and time.monotonic() < qr.token_expires_at - 3:
        return QrPollResponse(status="pending")
    qr.token_updated = False

    try:
        result = await _export_login_token(client)
        if isinstance(result, raw_types.auth.LoginTokenMigrateTo):
            result = await _migrate_and_import(client, result)
    except SessionPasswordNeeded:
        qr.awaiting_password = True
        return QrPollResponse(
            status="password_required", password_hint=await _password_hint(client)
        )
    except RPCError as exc:
        await _drop_qr(request_id)
        if error_id(exc) in {"AUTH_TOKEN_EXPIRED", "AUTH_TOKEN_INVALID"}:
            return QrPollResponse(status="restart")
        raise to_http_error(exc) from exc
    except Exception as exc:
        await _drop_qr(request_id)
        raise to_http_error(exc) from exc

    if isinstance(result, raw_types.auth.LoginTokenSuccess):
        _qr_logins.pop(request_id, None)
        account = await _finalize_login(db, user, client)
        return QrPollResponse(status="success", account=TelegramAccountOut.model_validate(account))

    if isinstance(result, raw_types.auth.LoginToken):
        qr.token_expires_at = _token_ttl(result.expires)
        return QrPollResponse(
            status="pending",
            qr_url=_qr_url(result.token),
            expires_in=max(0, result.expires - int(time.time())),
        )

    await _drop_qr(request_id)
    return QrPollResponse(status="restart")


@router.post("/qr/{request_id}/password", response_model=LoginResult)
async def qr_check_password(
    request_id: str,
    payload: QrPasswordRequest,
    user: User = Depends(rate_limit("auth_password", limit=10, window_seconds=600)),
    db: AsyncSession = Depends(get_db),
) -> LoginResult:
    """Finishes a QR login for an account with two-step verification."""
    await _sweep_expired_logins()
    qr = _get_owned_qr(request_id, user)
    if not qr.awaiting_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пароль сейчас не требуется")

    try:
        await qr.client.check_password(payload.password)
    except Exception as exc:
        if error_id(exc) not in RETRYABLE_INPUT_ERRORS:
            await _drop_qr(request_id)
        raise to_http_error(exc) from exc

    _qr_logins.pop(request_id, None)
    account = await _finalize_login(db, user, qr.client)
    return LoginResult(status="success", account=TelegramAccountOut.model_validate(account))


@router.post("/qr/{request_id}/cancel", status_code=204)
async def qr_cancel(request_id: str, user: User = Depends(get_current_user)) -> None:
    qr = _qr_logins.get(request_id)
    if qr is not None and qr.user_id == user.id:
        await _drop_qr(request_id)


async def _finalize_login(db: AsyncSession, user: User, client: Client) -> TelegramAccount:
    """Exports the now-authorized session, encrypts it (AGENTS.md 4.1) and
    stores it. Re-connecting the same Telegram account refreshes the
    existing row instead of creating a duplicate."""
    try:
        me = await client.get_me()
        # QR logins never go through sign_in(), which is what normally
        # records the user id in storage — export_session_string needs it.
        await client.storage.user_id(me.id)
        await client.storage.is_bot(False)
        session_string = await client.export_session_string()
    except Exception as exc:
        raise to_http_error(exc) from exc
    finally:
        await _safe_disconnect(client)

    phone = me.phone_number or ""
    account = None
    if phone:
        account = await db.scalar(
            select(TelegramAccount).where(
                TelegramAccount.user_id == user.id, TelegramAccount.phone == phone
            )
        )
    if account is None:
        account = TelegramAccount(user_id=user.id, phone=phone)
        db.add(account)

    account.encrypted_session = encrypt_session(session_string)
    account.is_active = True
    account.first_name = me.first_name
    account.username = me.username
    await db.commit()
    await db.refresh(account)
    return account
