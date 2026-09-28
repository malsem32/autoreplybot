"""Chat-folder links (t.me/addlist/...) in broadcasts."""

from datetime import UTC, datetime, timedelta

import pytest
from pyrogram import raw
from sqlalchemy import select

from backend.core.config import settings
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from workers import broadcaster
from workers.targets import expand_folder, folder_slug


def _channel(cid: int, title: str, left: bool = False) -> raw.types.Channel:
    return raw.types.Channel(
        id=cid, title=title, photo=raw.types.ChatPhotoEmpty(), date=0, access_hash=1, left=left
    )


def _group(cid: int, title: str) -> raw.types.Chat:
    return raw.types.Chat(
        id=cid,
        title=title,
        photo=raw.types.ChatPhotoEmpty(),
        participants_count=3,
        date=0,
        version=1,
    )


class _FolderClient:
    def __init__(self, result) -> None:
        self.result = result
        self.slugs: list[str] = []

    async def invoke(self, query):
        self.slugs.append(query.slug)
        return self.result


@pytest.mark.parametrize(
    ("link", "slug"),
    [
        ("https://t.me/addlist/AbC123", "AbC123"),
        ("t.me/addlist/AbC123?x=1", "AbC123"),
        ("@channel", None),
        ("t.me/+invite", None),
    ],
)
def test_folder_slug(link, slug):
    assert folder_slug(link) == slug


async def test_already_added_folder_uses_joined_chats():
    result = raw.types.chatlists.ChatlistInviteAlready(
        filter_id=2,
        missing_peers=[raw.types.PeerChannel(channel_id=30)],
        already_peers=[raw.types.PeerChannel(channel_id=10), raw.types.PeerChat(chat_id=20)],
        chats=[_channel(10, "Новости"), _group(20, "Клиенты"), _channel(30, "Чужой")],
        users=[],
    )
    client = _FolderClient(result)
    folder = await expand_folder(client, "https://t.me/addlist/AbC123")  # type: ignore[arg-type]
    assert client.slugs == ["AbC123"]
    assert [(c.chat_id, c.title) for c in folder.chats] == [
        (-1000000000010, "Новости"),
        (-20, "Клиенты"),
    ]
    assert folder.missing == 1


async def test_not_added_folder_keeps_only_chats_the_account_is_in():
    result = raw.types.chatlists.ChatlistInvite(
        title=raw.types.TextWithEntities(text="Папка", entities=[]),
        peers=[raw.types.PeerChannel(channel_id=10), raw.types.PeerChannel(channel_id=11)],
        chats=[_channel(10, "Мой канал"), _channel(11, "Не вступил", left=True)],
        users=[],
    )
    folder = await expand_folder(_FolderClient(result), "t.me/addlist/x")  # type: ignore[arg-type]
    assert [c.title for c in folder.chats] == ["Мой канал"]
    assert folder.missing == 1


async def test_campaign_sends_to_each_chat_of_a_folder(db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    sent_to: list[str] = []

    async def fake_expand(_client, target):
        from workers.targets import FolderChat, FolderExpansion

        return FolderExpansion(
            chats=[FolderChat(-1001, "Новости"), FolderChat(-1002, "Клиенты")], missing=2
        )

    async def fake_resolve(_client, ref):
        sent_to.append(ref)
        return int(ref)

    async def fake_send(*_args, **_kwargs):
        return None

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(broadcaster, "expand_folder", fake_expand)
    monkeypatch.setattr(broadcaster, "resolve_target", fake_resolve)
    monkeypatch.setattr(broadcaster, "send_content", fake_send)
    monkeypatch.setattr(broadcaster.asyncio, "sleep", no_sleep)

    async with db_sessionmaker() as db:
        user = User(telegram_id=1, pro_expires_at=datetime.now(UTC) + timedelta(days=1))
        db.add(user)
        await db.flush()
        account = TelegramAccount(user_id=user.id, phone="1", encrypted_session="x")
        db.add(account)
        await db.flush()
        folder = "https://t.me/addlist/AbC"
        campaign = BroadcastCampaign(
            account_id=account.id, title="t", text_template="Привет", target_chats=[folder]
        )
        db.add(campaign)
        await db.commit()
        await broadcaster.run_campaign(object(), db, campaign)  # type: ignore[arg-type]

        logs = (await db.execute(select(BroadcastLog).order_by(BroadcastLog.id))).scalars().all()

    assert sent_to == ["-1001", "-1002"]
    by_target = {log.target: log for log in logs}
    assert by_target[f"{folder} → Новости"].status == "success"
    assert by_target[f"{folder} → Клиенты"].chat_id == -1002
    note = by_target[folder]
    assert note.status == "error" and "2 чат" in (note.error_message or "")
