from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.models.user import User
from backend.services import referrals, support, team
from bot.handlers.support import ask_for_problem
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


async def _join_team(message: Message, token: str) -> None:
    sender = message.from_user
    assert sender is not None
    name = " ".join(p for p in (sender.first_name, sender.last_name) if p) or (
        f"@{sender.username}" if sender.username else "Без имени"
    )
    async with SessionLocal() as db:
        outcome, account = await team.accept_invite(db, token, sender.id, name)
        owner = await db.get(User, account.user_id) if account else None
    title = (account.first_name or account.username or "аккаунту") if account else ""
    texts = {
        "joined": f"🤝 Вы в команде! Теперь вы можете управлять аккаунтом «{title}» "
        "в приложении Автопилот: автоответы, рассылки и обращения.",
        "already": f"Вы уже в команде аккаунта «{title}».",
        "own": "Это ваш собственный аккаунт — приглашение не нужно.",
        "full": "В команде этого аккаунта уже максимум участников.",
        "invalid": "Ссылка-приглашение устарела или уже использована. Попросите новую.",
    }
    await message.answer(texts[outcome], reply_markup=open_app_keyboard())
    if outcome == "joined" and owner is not None and message.bot is not None:
        try:
            await message.bot.send_message(
                owner.telegram_id, f"🤝 {name} присоединился к команде аккаунта «{title}»."
            )
        except TelegramAPIError:
            pass


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext) -> None:
    if command.args == support.HELP_START_CODE:
        await ask_for_problem(message, state)
        return
    token = team.parse_team_code(command.args)
    if token and message.from_user is not None:
        await _join_team(message, token)
        return
    if message.from_user is not None:
        await _register_referral(message.from_user.id, command.args)

    await message.answer(
        "🚀 <b>Автопилот</b>\n\n"
        "Отвечает клиентам за вас 24/7 и ведёт рассылки по вашим чатам — "
        "без банов, с соблюдением лимитов Telegram.\n\n"
        "Подключите аккаунт и настройте правила за 2 минуты 👇\n\n"
        "⭐️ /pro — рабочие часы и умные автоответы, уведомления, статистика рассылок, "
        "альбомы и безлимит.\n"
        "🎁 /invite — пригласите друга и получите дни Pro бесплатно.\n"
        "🆘 /help — написать в поддержку.",
        reply_markup=open_app_keyboard(),
        parse_mode="HTML",
    )
