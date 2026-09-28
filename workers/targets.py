from dataclasses import dataclass, field

from pyrogram import Client, types, utils
from pyrogram import raw as tg_raw
from pyrogram.errors import UserAlreadyParticipant

FOLDER_PREFIX = "addlist/"


def _strip_tme_prefix(raw: str) -> str:
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if raw.startswith(prefix):
            return raw[len(prefix) :]
    return raw


def folder_slug(target: str) -> str | None:
    """The slug of a chat-folder link (`t.me/addlist/<slug>`), else None."""
    cleaned = _strip_tme_prefix(target.strip())
    if not cleaned.startswith(FOLDER_PREFIX):
        return None
    slug = cleaned[len(FOLDER_PREFIX) :].split("?")[0].strip("/")
    return slug or None


@dataclass
class FolderChat:
    chat_id: int
    title: str


@dataclass
class FolderExpansion:
    chats: list[FolderChat] = field(default_factory=list)  # the account is a member
    missing: int = 0  # chats of the folder the account hasn't joined


def _is_member(chat: object) -> bool:
    forbidden = (tg_raw.types.ChannelForbidden, tg_raw.types.ChatForbidden)
    return not isinstance(chat, forbidden) and not getattr(chat, "left", False)


async def expand_folder(client: Client, target: str) -> FolderExpansion:
    """Turns a chat-folder link into the chats it contains
    (`chatlists.checkChatlistInvite`, schema checked against kurigram's
    layer). Only chats the account is already a member of are returned:
    joining a whole folder of chats automatically would be a mass-join,
    which Telegram treats as spam-like. The owner adds the folder in
    Telegram once, then every chat in it is covered."""
    slug = folder_slug(target)
    if slug is None:
        raise ValueError("это не ссылка на папку")
    result = await client.invoke(tg_raw.functions.chatlists.CheckChatlistInvite(slug=slug))

    if isinstance(result, tg_raw.types.chatlists.ChatlistInviteAlready):
        joined_peers = list(result.already_peers)
        missing = len(result.missing_peers)
        member_check = False
    elif isinstance(result, tg_raw.types.chatlists.ChatlistInvite):
        joined_peers = list(result.peers)
        missing = 0
        member_check = True
    else:
        raise ValueError("не удалось прочитать папку")

    chats_by_id = {getattr(c, "id", None): c for c in result.chats}
    expansion = FolderExpansion()
    for peer in joined_peers:
        if isinstance(peer, tg_raw.types.PeerUser):
            continue  # folders shared by link hold chats and channels only
        chat = chats_by_id.get(_raw_id(peer))
        if chat is None or (member_check and not _is_member(chat)):
            missing += 1
            continue
        expansion.chats.append(
            FolderChat(chat_id=utils.get_peer_id(peer), title=getattr(chat, "title", "") or "")
        )
    expansion.missing = missing
    return expansion


def _raw_id(peer: object) -> int | None:
    return getattr(peer, "channel_id", None) or getattr(peer, "chat_id", None)


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

    if cleaned.startswith(FOLDER_PREFIX):
        # Expanded into its chats before sending (workers/broadcaster.py).
        raise ValueError("ссылку на папку нужно развернуть в чаты (expand_folder)")

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
