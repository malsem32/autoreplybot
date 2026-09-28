from pyrogram.errors import FloodWait, PhoneCodeInvalid
from redis.exceptions import ConnectionError as RedisConnectionError

from backend.core import rate_limit
from backend.core.telegram_errors import error_id, to_http_error


class _FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttl: dict[str, int] = {}

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        self.ttl[key] = seconds


async def test_rate_limit_blocks_after_limit_per_user(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit, "get_redis", lambda: fake)
    results = [await rate_limit.hit("auth_code", 1, limit=2, window_seconds=60) for _ in range(3)]
    assert results == [True, True, False]
    assert await rate_limit.hit("auth_code", 2, limit=2, window_seconds=60)  # other user
    assert fake.ttl["ratelimit:auth_code:1"] == 60


async def test_rate_limit_fails_open_without_redis(monkeypatch):
    class _Broken:
        async def incr(self, key):
            raise RedisConnectionError("down")

    monkeypatch.setattr(rate_limit, "get_redis", lambda: _Broken())
    assert await rate_limit.hit("auth_code", 1, limit=1, window_seconds=60)


def test_known_telegram_error_gets_russian_message():
    exc = to_http_error(PhoneCodeInvalid())
    assert exc.status_code == 400
    assert "Неверный код" in exc.detail


def test_flood_wait_maps_to_429_with_wait_time():
    exc = to_http_error(FloodWait(value=3700))
    assert exc.status_code == 429
    assert "1 ч." in exc.detail


def test_unknown_error_id_is_extracted_from_value():
    from pyrogram.errors import BadRequest

    exc = BadRequest(value="[400 SOME_NEW_ERROR]")
    assert error_id(exc) == "SOME_NEW_ERROR"
    assert "SOME_NEW_ERROR" in to_http_error(exc).detail


def test_network_errors_are_503():
    assert to_http_error(ConnectionError("x")).status_code == 503
