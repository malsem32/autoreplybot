import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from backend.core.config import settings


def build_init_data(user_id: int = 42, start_param: str | None = None) -> str:
    """Signs Mini App initData the way Telegram does (AGENTS.md 4.2)."""
    pairs = {
        "user": json.dumps({"id": user_id, "first_name": "Test"}),
        "auth_date": str(int(time.time())),
        "query_id": "AAA",
    }
    if start_param:
        pairs["start_param"] = start_param
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


def auth_headers(user_id: int = 42, start_param: str | None = None) -> dict[str, str]:
    return {"Authorization": f"tma {build_init_data(user_id, start_param)}"}
