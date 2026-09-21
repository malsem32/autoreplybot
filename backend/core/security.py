import hashlib
import hmac
import time
from urllib.parse import parse_qsl

from cryptography.fernet import Fernet

from backend.core.config import settings

_fernet = Fernet(settings.encryption_key.encode())

INIT_DATA_MAX_AGE_SECONDS = 24 * 60 * 60


def encrypt_session(session_string: str) -> str:
    return _fernet.encrypt(session_string.encode()).decode()


def decrypt_session(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


class InitDataError(Exception):
    pass


def parse_and_verify_init_data(init_data: str) -> dict:
    """Validate Telegram Mini App initData per
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    Returns the parsed key/value pairs on success, raises InitDataError otherwise.
    """
    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    auth_date = pairs.get("auth_date")
    if not auth_date or not auth_date.isdigit():
        raise InitDataError("missing or invalid auth_date")
    if time.time() - int(auth_date) > INIT_DATA_MAX_AGE_SECONDS:
        raise InitDataError("init_data expired")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("invalid hash")

    return pairs
