from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.models.user import User
from backend.services import referrals
from bot.keyboards.webapp import open_app_keyboard

router = Router(name="start")


async def _register_referral(telegram_id: int, start_arg: str | None) -> None:
    """Creates the User on first /start and records the inviter from a
    "ref_<id>" deep link. Existing users are never re-attributed."""
    inviter_id = referrals.parse_referral_code(start_arg)
    if inviter_id is None:
        return
    async with SessionLocal() as db:
        exists = await db.scalar(select(User.id).where(User.telegram_id == telegram_id))
        if exists is not None:
            return
        user = User(telegram_id=telegram_id)
        db.add(user)
        await db.flush()
        await referrals.attach_referrer(db, user, inviter_id)
        await db.commit()


@router.message(CommandStart())
async def start(message: Message, command: CommandObject) -> None:
    if message.from_user is not None:
        await _register_referral(message.from_user.id, command.args)

    await message.answer(
        "🚀 <b>Автопилот</b>\n\n"
        "Отвечает клиентам за вас 24/7 и ведёт рассылки по вашим чатам — "
        "без банов, с соблюдением лимитов Telegram.\n\n"
        "Подключите аккаунт и настройте правила за 2 минуты 👇\n\n"
        "⭐️ /pro — рабочие часы и умные автоответы, уведомления, статистика рассылок, "
        "альбомы и безлимит.\n"
        "🎁 /invite — пригласите друга и получите дни Pro бесплатно.",
        reply_markup=open_app_keyboard(),
        parse_mode="HTML",
    )
