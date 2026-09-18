from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.webapp import open_app_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Автопилот берёт на себя переписку: отвечает вашим клиентам, пока вы не на связи, "
        "и рассылает сообщения по вашим чатам с соблюдением лимитов Telegram.\n\n"
        "Подключите аккаунт и настройте правила в мини-приложении:",
        reply_markup=open_app_keyboard(),
    )
