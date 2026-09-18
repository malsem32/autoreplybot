import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest

from backend.core.config import settings
from backend.core.security import InitDataError, parse_and_verify_init_data


def _build_init_data(user_id: int = 42, auth_date: int | None = None) -> str:
    auth_date = auth_date if auth_date is not None else int(time.time())
    pairs = {
        "user": f'{{"id":{user_id},"first_name":"Test"}}',
        "auth_date": str(auth_date),
        "query_id": "AAA",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


def test_valid_init_data_is_accepted():
    init_data = _build_init_data()
    result = parse_and_verify_init_data(init_data)
    assert result["auth_date"]


def test_tampered_hash_is_rejected():
    init_data = _build_init_data() + "0"
    with pytest.raises(InitDataError):
        parse_and_verify_init_data(init_data)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError):
        parse_and_verify_init_data("auth_date=123&user=%7B%7D")


def test_expired_init_data_is_rejected():
    stale = int(time.time()) - 25 * 60 * 60
    init_data = _build_init_data(auth_date=stale)
    with pytest.raises(InitDataError):
        parse_and_verify_init_data(init_data)
