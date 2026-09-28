from pyrogram import Client, types
from pyrogram.errors import UserAlreadyParticipant


def _strip_tme_prefix(raw: str) -> str:
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if raw.startswith(prefix):
            return raw[len(prefix) :]
    return raw


async def resolve_target(client: Client, raw: str) -> int:
    """Turns a broadcast target — a numeric chat id, `@username`, a
    `t.me/<username>` link, or a `t.me/+<hash>` / `t.me/joinchat/<hash>`
    invite link — into a numeric chat id (needed both to call Pyrogram and
    to record `BroadcastLog.chat_id`).

    Invite links require actually joining the chat first; public usernames
    are resolved via `get_chat`. Raises on invalid/expired input so the
    caller (workers/broadcaster.py) can log it as a per-target send
    failure.
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("empty broadcast target")

    if raw.lstrip("-").isdigit():
        return int(raw)

    cleaned = _strip_tme_prefix(raw)

    if cleaned.startswith("addlist/"):
        # Chat-folder invite links (t.me/addlist/...) need Telegram's
        # chatlists.checkChatlistInvite / chatlists.joinChatlistInvite raw
        # methods to expand into individual chats. Not implemented: their
        # exact response schema couldn't be verified against a live
        # Pyrogram install/Telegram server from the dev sandbox this was
        # written in (see AGENTS.md 4.1 for the same caveat on QR login).
        # Add each chat from the folder individually for now.
        raise ValueError(
            "ссылки на папку чатов (t.me/addlist/...) пока не поддерживаются — "
            "добавьте чаты из папки по отдельности (ID, @username или t.me/+ ссылкой)"
        )

    if cleaned.startswith("+") or cleaned.startswith("joinchat/"):
        invite_link = raw if raw.startswith("http") else f"https://t.me/{cleaned}"
        return await _join_by_invite(client, invite_link)

    chat = await client.get_chat(f"@{cleaned.lstrip('@')}")
    if chat is None or chat.id is None:
        raise ValueError(f"чат {raw} недоступен")
    return chat.id


async def _join_by_invite(client: Client, invite_link: str) -> int:
    try:
        result = await client.join_chat(invite_link)
    except UserAlreadyParticipant:
        # Recurring campaigns hit this on every run after the first join:
        # resolving the link of an already-joined chat yields the chat.
        chat = await client.get_chat(invite_link)
        chat_id = getattr(chat, "id", None)
        if not isinstance(chat_id, int):
            raise ValueError("не удалось определить чат по ссылке-приглашению") from None
        return chat_id

    if isinstance(result, types.ChatJoinResultSuccess) and result.chat.id is not None:
        return result.chat.id
    raise ValueError("заявка на вступление отправлена — дождитесь одобрения администратором чата")
