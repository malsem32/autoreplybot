from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from backend.core.config import settings


def open_app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Автопилот",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )
