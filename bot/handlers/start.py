from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.webapp import open_app_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Привет! 👋 Я — Автопилот.\n\n"
        "Беру на себя рутину в Telegram: отвечаю вашим клиентам, пока вы заняты, "
        "и аккуратно рассылаю сообщения по чатам, бережно соблюдая лимиты Telegram.\n\n"
        "Подключить аккаунт и настроить всё под себя — пара минут в мини-приложении:",
        reply_markup=open_app_keyboard(),
    )
