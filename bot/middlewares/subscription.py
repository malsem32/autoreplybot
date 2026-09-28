import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, TelegramObject, Update

from backend.core.config import settings

logger = logging.getLogger(__name__)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    for channel in settings.required_channels_list:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        except TelegramAPIError:
            # Misconfigured channel (bot not a member/admin there) — don't
            # lock every user out of the bot because of it.
            logger.warning("cannot check membership in a required channel")
            continue
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

        # A completed Stars payment must always be processed, subscribed or not.
        if isinstance(event, Message) and event.successful_payment is not None:
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        bot: Bot = data["bot"]
        if await is_subscribed(bot, user.id):
            return await handler(event, data)

        message = event.message if isinstance(event, Update) else event
        if isinstance(message, Message):
            channels = ", ".join(settings.required_channels_list)
            await message.answer(
                f"Чтобы пользоваться ботом, подпишитесь на: {channels}, "
                "затем отправьте /start снова."
            )
        return None
