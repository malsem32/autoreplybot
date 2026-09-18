import json

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import InitDataError, parse_and_verify_init_data
from backend.db.session import get_db
from backend.models.user import User


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
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
