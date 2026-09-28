"""Minimal Bot API calls made from the backend/worker on behalf of the
Gatekeeper bot (messages and files to a user's chat with the bot)."""

import csv
import io
import logging
from collections.abc import Sequence

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


def _url(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.bot_token}/{method}"


async def send_message(telegram_id: int, text: str, reply_markup: dict | None = None) -> bool:
    """Best effort: the user may never have started the bot or may have
    blocked it. Never logs the text."""
    return await post_message(telegram_id, text, reply_markup) is not None


async def post_message(telegram_id: int, text: str, reply_markup: dict | None = None) -> int | None:
    """Like send_message, but returns the sent message id (None on failure)."""
    payload: dict = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(_url("sendMessage"), json=payload)
        if resp.status_code != 200:
            logger.info("bot message not delivered (status %s)", resp.status_code)
            return None
        message_id = resp.json().get("result", {}).get("message_id")
        return int(message_id) if message_id is not None else None
    except (httpx.HTTPError, ValueError):
        logger.info("bot message failed")
        return None


def build_csv(headers: list[str], rows: Sequence[Sequence[object]]) -> bytes:
    """CSV that opens correctly in Excel (UTF-8 BOM, `;` separator)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


async def send_document(telegram_id: int, filename: str, content: bytes, caption: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _url("sendDocument"),
                data={"chat_id": str(telegram_id), "caption": caption},
                files={"document": (filename, content, "text/csv")},
            )
        return resp.status_code == 200
    except httpx.HTTPError:
        logger.info("bot document failed")
        return False
