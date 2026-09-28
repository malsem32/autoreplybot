import json
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import InitDataError, parse_and_verify_init_data
from backend.db.session import get_db
from backend.models.user import User
from backend.services import referrals


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates `Authorization: tma <initData>` per AGENTS.md 4.2 and
    returns the User row, creating it on first sight of a telegram_id."""
    scheme, _, init_data = authorization.partition(" ")
    if scheme.lower() != "tma" or not init_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid authorization scheme")

    try:
        pairs = parse_and_verify_init_data(init_data)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user_payload = json.loads(pairs.get("user", "{}"))
    telegram_id = user_payload.get("id")
    if not telegram_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "init_data missing user")

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id)
        _apply_profile(user, user_payload)
        db.add(user)
        await db.flush()
        # Mini App opened via t.me/<bot>/<app>?startapp=ref_<id>.
        await referrals.attach_referrer(
            db, user, referrals.parse_referral_code(pairs.get("start_param"))
        )
        await db.commit()
        await db.refresh(user)
    elif _apply_profile(user, user_payload):
        await db.commit()

    return user


# Writing last_seen_at on every request would turn each read into a write.
_SEEN_RESOLUTION = timedelta(minutes=10)


def _apply_profile(user: User, payload: dict) -> bool:
    """Keeps name/@username (for the admin section) and last visit fresh.
    Returns True if something changed."""
    first_name = (payload.get("first_name") or "")[:128] or None
    username = (payload.get("username") or "")[:64] or None
    now = datetime.now(UTC)
    last_seen = user.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    changed = False
    if user.first_name != first_name or user.username != username:
        user.first_name, user.username = first_name, username
        changed = True
    if last_seen is None or now - last_seen > _SEEN_RESOLUTION:
        user.last_seen_at = now
        changed = True
    return changed
