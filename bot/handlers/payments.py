import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from backend.db.session import SessionLocal
from backend.services import pro, referrals

logger = logging.getLogger(__name__)

router = Router(name="payments")


PLAN_CALLBACK = "pro_plan:"


@router.callback_query(F.data == "pro_menu")
async def pro_menu_button(query: CallbackQuery) -> None:
    """ "Продлить" button under the Pro expiry reminder (workers/digests.py)."""
    if isinstance(query.message, Message):
        await buy_pro(query.message)
    await query.answer()


@router.message(Command("pro"))
async def buy_pro(message: Message) -> None:
    """Sells Pro right in the bot chat: pick a plan, get the same invoice the
    Mini App opens."""
    async with SessionLocal() as db:
        row = await pro.get_settings(db)
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{plan.title} — {plan.stars} ⭐️", callback_data=f"{PLAN_CALLBACK}{plan.id}"
            )
        ]
        for plan in pro.plans(row)
    ]
    features = "\n".join(f"• {item}" for item in pro.PRO_FEATURES)
    await message.answer(
        f"⭐️ <b>Автопилот Pro</b>\n\n{features}\n\nВыберите срок:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith(PLAN_CALLBACK))
async def send_plan_invoice(query: CallbackQuery) -> None:
    async with SessionLocal() as db:
        row = await pro.get_settings(db)
    plan = pro.find_plan(row, (query.data or "").removeprefix(PLAN_CALLBACK))
    if plan is None or not isinstance(query.message, Message):
        await query.answer("Тариф недоступен, отправьте /pro ещё раз", show_alert=True)
        return
    params = pro.invoice_params(
        plan.stars, plan.days, pro.invoice_payload(query.from_user.id, plan.days)
    )
    await query.message.answer_invoice(
        title=params["title"],
        description=params["description"],
        payload=params["payload"],
        currency=params["currency"],
        prices=[LabeledPrice(**price) for price in params["prices"]],
    )
    await query.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    parsed = pro.parse_invoice_payload(query.invoice_payload)
    if parsed is not None:
        async with SessionLocal() as db:
            row = await pro.get_settings(db)
        # The price may have changed since the invoice was issued.
        if pro.price_matches(row, parsed[1], query.total_amount):
            await query.answer(ok=True)
            return
    await query.answer(ok=False, error_message="Счёт устарел — запросите новый через /pro")


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
