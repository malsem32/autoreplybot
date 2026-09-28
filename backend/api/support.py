"""«Помощь» from the Mini App: the message goes to the admins' chats with
the bot; their reply comes back to the user in the bot chat."""

import json
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core import rate_limit
from backend.db.session import get_db
from backend.models.user import User
from backend.services import bot_api, support

router = APIRouter(prefix="/api/support", tags=["support"])


class SupportIn(BaseModel):
    text: str = Field(min_length=3, max_length=support.MAX_TEXT)


class SupportOut(BaseModel):
    delivered: bool


def _display_profile(authorization: str) -> tuple[str | None, str | None]:
    """Name and @username from initData for the admin's convenience. The
    signature is verified by get_current_user in the same request."""
    raw = parse_qs(authorization.partition(" ")[2]).get("user", ["{}"])[0]
    try:
        data = json.loads(raw)
    except ValueError:
        return None, None
    name = " ".join(p for p in (data.get("first_name"), data.get("last_name")) if p) or None
    return name, data.get("username")


@router.post("", response_model=SupportOut)
async def contact_support(
    payload: SupportIn,
    authorization: str = Header(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportOut:
    name, username = _display_profile(authorization)
    admins = support.admin_ids()
    if not admins:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Поддержка пока не настроена")
    if not await rate_limit.hit("support", user.id, limit=5, window_seconds=600):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Сообщение уже отправлено — подождите ответа, пожалуйста",
        )
    text = support.ticket_text(
        support.sender_line(user.telegram_id, name, username),
        await support.user_context(db, user.telegram_id),
        "из приложения",
        payload.text,
    )
    delivered = False
    for admin_id in admins:
        message_id = await bot_api.post_message(admin_id, text)
        if message_id is not None:
            await support.remember(db, admin_id, message_id, user.telegram_id)
            delivered = True
    await db.commit()
    if not delivered:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Не удалось доставить — напишите /help в чате с ботом",
        )
    return SupportOut(delivered=True)
