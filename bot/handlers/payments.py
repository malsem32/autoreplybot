import logging

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

from backend.db.session import SessionLocal
from backend.services.tag_feature import grant_access

logger = logging.getLogger(__name__)

router = Router(name="payments")


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    parts = payment.invoice_payload.split(":")
    if len(parts) != 3 or parts[0] != "tag_broadcast":
        logger.warning("unrecognized invoice payload: %s", payment.invoice_payload)
        return

    _, telegram_id, duration_days = parts
    async with SessionLocal() as db:
        user = await grant_access(db, int(telegram_id), int(duration_days))

    if user is None:
        logger.warning("successful_payment for unknown telegram_id %s", telegram_id)
        return

    await message.answer(
        "Оплата получена ⭐️ Теги случайных участников в рассылках доступны "
        f"до {user.tag_feature_expires_at:%d.%m.%Y %H:%M} (UTC)."
    )
