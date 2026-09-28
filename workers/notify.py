import html

from backend.services.bot_api import send_message


def esc(value: str | None) -> str:
    return html.escape(value or "", quote=False)


async def notify_user(telegram_id: int, text: str, reply_markup: dict | None = None) -> None:
    """Sends a message to the owner in the Gatekeeper bot chat (Pro
    notifications). Best effort — the autopilot keeps working either way."""
    await send_message(telegram_id, text, reply_markup)
