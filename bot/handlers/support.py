"""«Помощь» in the bot chat: /help (or the ?start=help deep link) → the
user's next message goes to every admin (ADMIN_TELEGRAM_IDS); an admin's
Reply to that message is sent back to the user."""

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from backend.db.session import SessionLocal
from backend.services import support

logger = logging.getLogger(__name__)

router = Router(name="support")


class SupportStates(StatesGroup):
    waiting = State()


def _name(message: Message) -> str | None:
    sender = message.from_user
    if sender is None:
        return None
    return " ".join(p for p in (sender.first_name, sender.last_name) if p) or None


async def ask_for_problem(message: Message, state: FSMContext) -> None:
    if not support.admin_ids():
        await message.answer("Поддержка пока не настроена. Попробуйте позже.")
        return
    await state.set_state(SupportStates.waiting)
    await message.answer(
        "🆘 <b>Помощь</b>\n\nОпишите проблему одним сообщением — можно приложить скриншот. "
        "Что делали, что ожидали и что произошло.\n\nОтменить: /cancel",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await ask_for_problem(message, state)


@router.message(Command("cancel"), StateFilter(SupportStates.waiting))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@router.message(StateFilter(SupportStates.waiting))
async def forward_problem(message: Message, state: FSMContext, bot: Bot) -> None:
    sender = message.from_user
    if sender is None:
        return
    await state.clear()
    async with SessionLocal() as db:
        header = support.ticket_text(
            support.sender_line(sender.id, _name(message), sender.username),
            await support.user_context(db, sender.id),
            "из бота",
            message.text,
        )
        delivered = False
        for admin_id in support.admin_ids():
            try:
                sent = await bot.send_message(admin_id, header, parse_mode="HTML")
                await support.remember(db, admin_id, sent.message_id, sender.id)
                if message.text is None:
                    # Screenshot / file / voice: deliver the original too.
                    copy = await message.copy_to(admin_id, reply_to_message_id=sent.message_id)
                    await support.remember(db, admin_id, copy.message_id, sender.id)
                delivered = True
            except TelegramAPIError:
                logger.info("support request not delivered to an admin")
        await db.commit()
    await message.answer(
        "✅ Отправлено! Ответ придёт сюда, в этот чат."
        if delivered
        else "Не получилось доставить сообщение. Попробуйте позже."
    )


@router.message(F.reply_to_message, F.from_user.id.in_(support.admin_ids()))
async def admin_reply(message: Message, bot: Bot) -> None:
    replied = message.reply_to_message
    if replied is None:
        return
    async with SessionLocal() as db:
        user_id = await support.recipient_for(db, message.chat.id, replied.message_id)
    if user_id is None:
        return
    try:
        await bot.send_message(user_id, "💬 <b>Ответ поддержки</b>", parse_mode="HTML")
        await message.copy_to(user_id)
    except TelegramAPIError:
        await message.reply("Не доставлено: пользователь заблокировал бота.")
        return
    await message.reply("✅ Ответ отправлен")
