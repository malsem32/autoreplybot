import html
import logging

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


def esc(value: str | None) -> str:
    return html.escape(value or "", quote=False)


async def notify_user(telegram_id: int, text: str) -> None:
    """Sends a message to the owner in the Gatekeeper bot chat (Pro
    notifications). Best effort: the owner may never have started the bot
    or may have blocked it — the autopilot keeps working either way.
    Never logs the text (it may contain someone's message)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                json={
                    "chat_id": telegram_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
        if resp.status_code != 200:
            logger.info("owner notification not delivered (status %s)", resp.status_code)
    except httpx.HTTPError:
        logger.info("owner notification failed")
