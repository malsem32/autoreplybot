from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.webapp import open_app_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "🚀 <b>Автопилот</b>\n\n"
        "Отвечает клиентам за вас 24/7 и ведёт рассылки по вашим чатам — "
        "без банов, с соблюдением лимитов Telegram.\n\n"
        "Подключите аккаунт и настройте правила за 2 минуты 👇",
        reply_markup=open_app_keyboard(),
        parse_mode="HTML",
    )
