import logging
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.models.user import User

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url)
    return _redis


async def hit(scope: str, user_id: int, limit: int, window_seconds: int) -> bool:
    """Fixed-window counter per (scope, user). Returns False once `limit` is
    exceeded within the window. Fails open when Redis is unreachable: a
    Redis outage must not lock every user out of logging in."""
    key = f"ratelimit:{scope}:{user_id}"
    try:
        redis = _get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except RedisError:
        logger.warning("rate limiter unavailable, allowing request (scope=%s)", scope)
        return True
    return count <= limit


def rate_limit(scope: str, limit: int, window_seconds: int) -> Callable[..., Awaitable[User]]:
    """Per-user rate limit for endpoints that trigger external actions
    (AGENTS.md 4.7). Use in place of `get_current_user` — it authenticates
    via initData too and returns the same User."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not await hit(scope, user.id, limit, window_seconds):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Слишком много запросов — подождите немного и попробуйте снова",
            )
        return user

    return dependency
