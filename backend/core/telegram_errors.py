import asyncio
import re

from fastapi import HTTPException, status
from pyrogram.errors import FloodWait, RPCError

# Telegram RPC error IDs → human-readable Russian messages for the Mini App.
# Raw Pyrogram messages ("Telegram says: [400 PHONE_CODE_INVALID] ...") are
# meaningless to end users, and the unknown remainder still gets its ID shown.
_MESSAGES: dict[str, str] = {
    "PHONE_NUMBER_INVALID": (
        "Неверный номер телефона. Укажите его в международном формате, например +79991234567"
    ),
    "PHONE_NUMBER_BANNED": "Этот номер заблокирован в Telegram",
    "PHONE_NUMBER_FLOOD": "Слишком много попыток входа для этого номера. Попробуйте позже",
    "PHONE_NUMBER_UNOCCUPIED": "Этот номер не зарегистрирован в Telegram",
    "PHONE_CODE_INVALID": "Неверный код. Проверьте и введите ещё раз",
    "PHONE_CODE_EMPTY": "Введите код из Telegram",
    "PHONE_CODE_EXPIRED": "Срок действия кода истёк. Запросите новый код",
    "PHONE_CODE_HASH_EMPTY": "Сессия входа устарела. Запросите новый код",
    "PHONE_PASSWORD_FLOOD": "Слишком много попыток. Попробуйте позже",
    "PASSWORD_HASH_INVALID": "Неверный пароль двухфакторной защиты",
    "SEND_CODE_UNAVAILABLE": (
        "Telegram больше не может отправить код этим способом. Подождите и начните заново"
    ),
    "API_ID_INVALID": "Неверные API_ID / API_HASH на сервере — обратитесь к администратору",
    "API_ID_PUBLISHED_FLOOD": (
        "Эти API_ID / API_HASH заблокированы Telegram — обратитесь к администратору"
    ),
    "UPDATE_APP_TO_LOGIN": "Telegram требует обновить клиент — обратитесь к администратору",
    "AUTH_RESTART": "Telegram попросил начать вход заново. Запросите новый код",
    "AUTH_TOKEN_EXPIRED": "QR-код устарел — обновите его",
    "AUTH_TOKEN_INVALID": "QR-код недействителен — обновите его",
    "AUTH_TOKEN_ALREADY_ACCEPTED": "Этот QR-код уже использован",
    "SESSION_PASSWORD_NEEDED": "Нужен пароль двухфакторной защиты",
    "USER_DEACTIVATED": "Этот аккаунт удалён или деактивирован",
    "USER_DEACTIVATED_BAN": "Этот аккаунт заблокирован Telegram",
}

# Errors after which the same login attempt can simply be retried with a
# different user input — the pending client must be kept alive for these.
RETRYABLE_INPUT_ERRORS = {"PHONE_CODE_INVALID", "PHONE_CODE_EMPTY", "PASSWORD_HASH_INVALID"}


def error_id(exc: BaseException) -> str | None:
    if not isinstance(exc, RPCError):
        return None
    if exc.ID:
        return exc.ID
    # Errors unknown to this Pyrogram build carry the ID only in `value`,
    # e.g. "[400 SOME_NEW_ERROR]".
    match = re.search(r"\[\d+ ([A-Z0-9_]+)", str(exc.value or ""))
    return match.group(1) if match else None


def flood_wait_seconds(exc: FloodWait) -> int:
    value = exc.value
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def _format_wait(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} сек."
    if seconds < 3600:
        return f"{seconds // 60} мин."
    return f"{seconds // 3600} ч. {seconds % 3600 // 60} мин."


def to_http_error(exc: BaseException) -> HTTPException:
    """Maps a Pyrogram/network exception to an HTTPException with a
    user-facing message. Never includes the phone, code or password."""
    if isinstance(exc, FloodWait):
        wait = flood_wait_seconds(exc)
        return HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Telegram временно ограничил попытки входа. Повторите через {_format_wait(wait)}",
        )
    rpc_id = error_id(exc)
    if rpc_id is not None:
        message = _MESSAGES.get(rpc_id, f"Ошибка Telegram: {rpc_id}")
        return HTTPException(status.HTTP_400_BAD_REQUEST, message)
    if isinstance(exc, (ConnectionError, OSError, TimeoutError, asyncio.TimeoutError)):
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Не удалось подключиться к серверам Telegram. Попробуйте ещё раз",
        )
    return HTTPException(status.HTTP_400_BAD_REQUEST, "Не удалось выполнить запрос к Telegram")
