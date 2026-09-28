"""«Помощь»: users write to the admins (ADMIN_TELEGRAM_IDS) from the Mini App
or with /help in the bot; an admin answers by replying to the delivered
message in their chat with the bot (bot/handlers/support.py)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.support import SupportMessage
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro

MAX_TEXT = 2000
HELP_START_CODE = "help"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sender_line(telegram_id: int, name: str | None, username: str | None) -> str:
    who = esc(name or "Без имени")
    handle = f" (@{esc(username)})" if username else ""
    return (
        f'От: <a href="tg://user?id={telegram_id}">{who}</a>{handle}, id <code>{telegram_id}</code>'
    )


async def user_context(db: AsyncSession, telegram_id: int) -> str:
    """One line of context for the admin: plan and connected accounts."""
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        return "Ещё не открывал приложение"
    accounts = await db.scalar(
        select(func.count()).select_from(TelegramAccount).where(TelegramAccount.user_id == user.id)
    )
    plan = (
        f"Pro до {user.pro_expires_at:%d.%m.%Y}"
        if pro.has_access(user) and user.pro_expires_at
        else "Pro"
        if pro.has_access(user)
        else "без Pro"
    )
    return f"{plan} · аккаунтов: {accounts or 0}"


def ticket_text(sender: str, context: str, source: str, text: str | None) -> str:
    body = f"\n\n<blockquote>{esc(text[:MAX_TEXT])}</blockquote>" if text else ""
    return (
        f"🆘 <b>Обращение в поддержку</b> ({source})\n{sender}\n{context}{body}\n\n"
        "<i>Ответьте на это сообщение (Reply) — ответ уйдёт пользователю.</i>"
    )


def admin_ids() -> list[int]:
    return settings.admin_telegram_ids_list


async def remember(
    db: AsyncSession, admin_chat_id: int, admin_message_id: int, user_telegram_id: int
) -> None:
    db.add(
        SupportMessage(
            admin_chat_id=admin_chat_id,
            admin_message_id=admin_message_id,
            user_telegram_id=user_telegram_id,
        )
    )


async def recipient_for(db: AsyncSession, admin_chat_id: int, admin_message_id: int) -> int | None:
    return await db.scalar(
        select(SupportMessage.user_telegram_id).where(
            SupportMessage.admin_chat_id == admin_chat_id,
            SupportMessage.admin_message_id == admin_message_id,
        )
    )
