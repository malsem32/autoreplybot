from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Update

from backend.core.config import settings


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    for channel in settings.required_channels_list:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ("left", "kicked"):
            return False
    return True


class SubscriptionMiddleware(BaseMiddleware):
    """Blocks any update from a user who hasn't joined every channel in
    REQUIRED_CHANNELS. See AGENTS.md section 1 (Gatekeeper Bot)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not settings.required_channels_list:
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        bot: Bot = data["bot"]
        if await is_subscribed(bot, user.id):
            return await handler(event, data)

        if isinstance(event, Update) and event.message:
            channels = ", ".join(settings.required_channels_list)
            await event.message.answer(
                f"Чтобы пользоваться ботом, подпишитесь на: {channels}, "
                "затем отправьте /start снова."
            )
        return None
