import asyncio

from aiogram import Bot, Dispatcher

from backend.core.config import settings
from backend.core.logging import configure_logging
from bot.handlers.payments import router as payments_router
from bot.handlers.start import router as start_router
from bot.middlewares.subscription import SubscriptionMiddleware


async def main() -> None:
    configure_logging()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.message.middleware(SubscriptionMiddleware())
    dp.include_router(start_router)
    dp.include_router(payments_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
