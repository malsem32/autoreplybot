import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.models.lead import Lead
from backend.models.team import AccountMember
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="leads")

STATUS_TEXT = {"in_work": "🛠 Взято в работу", "done": "✅ Готово"}


async def _can_manage(db, account: TelegramAccount, telegram_id: int) -> bool:
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        return False
    if account.user_id == user.id:
        return True
    member = await db.scalar(
        select(AccountMember.id).where(
            AccountMember.account_id == account.id, AccountMember.user_id == user.id
        )
    )
    return member is not None


@router.callback_query(F.data.startswith("lead:"))
async def set_lead_status(query: CallbackQuery) -> None:
    """Status buttons under "new inquiry" notifications (workers/responder.py).
    Only the account owner or a team member may change the status."""
    parts = (query.data or "").split(":")
    if len(parts) != 3 or not parts[1].isdigit() or parts[2] not in STATUS_TEXT:
        await query.answer()
        return
    lead_id, new_status = int(parts[1]), parts[2]
    async with SessionLocal() as db:
        lead = await db.get(Lead, lead_id)
        account = await db.get(TelegramAccount, lead.account_id) if lead else None
        if (
            lead is None
            or account is None
            or not await _can_manage(db, account, query.from_user.id)
        ):
            await query.answer("Обращение не найдено", show_alert=True)
            return
        lead.status = new_status
        await db.commit()

    await query.answer(STATUS_TEXT[new_status])
    if isinstance(query.message, Message):
        # Keep only the "open dialog" link, drop the status buttons.
        markup = query.message.reply_markup
        rows = [
            row
            for row in (markup.inline_keyboard if markup else [])
            if not any((b.callback_data or "").startswith("lead:") for b in row)
        ]
        try:
            await query.message.edit_text(
                f"{query.message.html_text}\n\n<b>{STATUS_TEXT[new_status]}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None,
            )
        except Exception:  # noqa: BLE001 - the status is saved; editing is cosmetic
            logger.info("could not edit lead notification")
