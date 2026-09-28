import re
from dataclasses import dataclass

from pyrogram import Client, types

# Telegram limit for a media caption (non-Premium senders). Longer text is
# sent as a separate message right after the photo(s).
CAPTION_LIMIT = 1024

_TAG_RE = re.compile(r"<[^>]+>")


def visible_length(text: str) -> int:
    """Approximate rendered length: HTML formatting tags don't count."""
    return len(_TAG_RE.sub("", text))


@dataclass(frozen=True)
class SendOptions:
    disable_notification: bool = False
    protect_content: bool = False
    disable_link_preview: bool = False
    reply_to_message_id: int | None = None


async def send_content(
    client: Client,
    chat_id: int,
    text: str,
    photo_paths: list[str],
    options: SendOptions | None = None,
) -> None:
    """Sends text with 0, 1 or 2-10 photos (album), honoring the send
    options. Text is parsed with Pyrogram's default mode (HTML + Markdown),
    which is what the Mini App formatting toolbar produces.

    FloodWait is deliberately not handled here — callers own the retry
    policy (AGENTS.md 4.3)."""
    options = options or SendOptions()
    silent = options.disable_notification or None
    protect = options.protect_content or None
    reply = (
        types.ReplyParameters(message_id=options.reply_to_message_id)
        if options.reply_to_message_id
        else None
    )

    caption_fits = visible_length(text) <= CAPTION_LIMIT
    caption = text if caption_fits else ""

    if len(photo_paths) == 1:
        await client.send_photo(
            chat_id,
            photo_paths[0],
            caption=caption,
            reply_parameters=reply,
            disable_notification=silent,
            protect_content=protect,
        )
    elif len(photo_paths) > 1:
        media: list[
            types.InputMediaPhoto
            | types.InputMediaVideo
            | types.InputMediaAudio
            | types.InputMediaDocument
        ] = [
            types.InputMediaPhoto(path, caption=caption if index == 0 else "")
            for index, path in enumerate(photo_paths)
        ]
        await client.send_media_group(
            chat_id,
            media,
            reply_parameters=reply,
            disable_notification=silent,
            protect_content=protect,
        )

    if not photo_paths or not caption_fits:
        await client.send_message(
            chat_id,
            text,
            link_preview_options=types.LinkPreviewOptions(is_disabled=True)
            if options.disable_link_preview
            else None,
            reply_parameters=reply if not photo_paths else None,
            disable_notification=silent,
            protect_content=protect,
        )
