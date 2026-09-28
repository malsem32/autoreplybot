import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from backend.db.session import SessionLocal
from backend.services import pro, referrals

logger = logging.getLogger(__name__)

router = Router(name="payments")


@router.message(Command("pro"))
async def buy_pro(message: Message) -> None:
    """Sells Pro right in the bot chat — the same invoice the Mini App opens."""
    if message.from_user is None:
        return
    async with SessionLocal() as db:
        row = await pro.get_settings(db)
    params = pro.invoice_params(
        row.stars_price,
        row.duration_days,
        pro.invoice_payload(message.from_user.id, row.duration_days),
    )
    await message.answer_invoice(
        title=params["title"],
        description=params["description"],
        payload=params["payload"],
        currency=params["currency"],
        prices=[LabeledPrice(**price) for price in params["prices"]],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    if pro.parse_invoice_payload(query.invoice_payload) is None:
        await query.answer(ok=False, error_message="Счёт устарел — запросите новый через /pro")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    parsed = pro.parse_invoice_payload(payment.invoice_payload)
    if parsed is None:
        logger.warning("unrecognized invoice payload")
        return

    telegram_id, duration_days = parsed
    async with SessionLocal() as db:
        user = await pro.grant_access(db, telegram_id, duration_days)
        reward = await referrals.reward_first_payment(db, user)
        await db.refresh(user)

    assert user.pro_expires_at is not None
    await message.answer(
        "Оплата получена ⭐️ <b>Автопилот Pro</b> активен "
        f"до {user.pro_expires_at:%d.%m.%Y %H:%M} (UTC)."
        + (f"\n🎁 +{reward[1]} дн. в подарок за приглашение друга." if reward else ""),
        parse_mode="HTML",
    )

    if reward is not None and message.bot is not None:
        inviter, bonus = reward
        try:
            await message.bot.send_message(
                inviter.telegram_id,
                f"🎁 Ваш друг оформил Pro — вам начислено +{bonus} дн. Pro. Спасибо!",
            )
        except TelegramAPIError:
            # The inviter may have blocked the bot; the bonus is granted anyway.
            logger.info("could not notify inviter about referral bonus")


@router.message(Command("invite"))
async def invite(message: Message) -> None:
    if message.from_user is None:
        return
    async with SessionLocal() as db:
        row = await pro.get_settings(db)
    await message.answer(
        "🎁 <b>Пригласите друга</b>\n\n"
        f"Когда друг оформит Pro, вы оба получите +{row.referral_bonus_days} дн. Pro.\n\n"
        f"Ваша ссылка:\n{referrals.referral_link(message.from_user.id)}",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
