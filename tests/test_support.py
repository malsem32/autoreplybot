"""«Помощь»: requests reach the admins, admin replies reach the user."""

from types import SimpleNamespace

import pytest

from backend.core import rate_limit
from backend.core.config import settings
from backend.services import bot_api, support
from bot.handlers import support as support_handlers
from tests.helpers import auth_headers


@pytest.fixture(autouse=True)
def _admins(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "900,901")


async def test_support_request_reaches_admins_and_maps_replies(api, db_sessionmaker, monkeypatch):
    sent: list[tuple[int, str]] = []

    async def fake_post(chat_id, text, reply_markup=None):
        sent.append((chat_id, text))
        return 1000 + len(sent)

    monkeypatch.setattr(bot_api, "post_message", fake_post)
    resp = await api.post(
        "/api/support", json={"text": "Не приходит <код>"}, headers=auth_headers(42)
    )
    assert resp.status_code == 200 and resp.json() == {"delivered": True}
    assert [chat for chat, _ in sent] == [900, 901]
    assert "Не приходит &lt;код&gt;" in sent[0][1]  # escaped for HTML
    assert "id <code>42</code>" in sent[0][1]

    async with db_sessionmaker() as db:
        assert await support.recipient_for(db, 900, 1001) == 42
        assert await support.recipient_for(db, 901, 1002) == 42
        assert await support.recipient_for(db, 900, 999) is None


async def test_support_needs_admins_and_is_rate_limited(api, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    resp = await api.post("/api/support", json={"text": "помогите"}, headers=auth_headers())
    assert resp.status_code == 503

    monkeypatch.setattr(settings, "admin_telegram_ids", "900")

    async def fake_post(chat_id, text, reply_markup=None):
        return 1

    async def limited(*_args, **_kwargs):
        return False

    monkeypatch.setattr(bot_api, "post_message", fake_post)
    monkeypatch.setattr(rate_limit, "hit", limited)
    resp = await api.post("/api/support", json={"text": "помогите"}, headers=auth_headers())
    assert resp.status_code == 429


async def test_undeliverable_support_request(api, monkeypatch):
    async def fail(chat_id, text, reply_markup=None):
        return None

    monkeypatch.setattr(bot_api, "post_message", fail)
    resp = await api.post("/api/support", json={"text": "помогите"}, headers=auth_headers())
    assert resp.status_code == 503


class _FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))
        return SimpleNamespace(message_id=500 + len(self.sent))


class _FakeMessage:
    def __init__(self, chat_id: int, text: str | None, reply_to=None) -> None:
        self.chat = SimpleNamespace(id=chat_id)
        self.text = text
        self.from_user = SimpleNamespace(
            id=chat_id, first_name="Анна", last_name=None, username="anna"
        )
        self.reply_to_message = reply_to
        self.answers: list[str] = []
        self.replies: list[str] = []
        self.copied_to: list[int] = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)

    async def reply(self, text, **kwargs):
        self.replies.append(text)

    async def copy_to(self, chat_id, **kwargs):
        self.copied_to.append(chat_id)
        return SimpleNamespace(message_id=700)


class _FakeState:
    def __init__(self) -> None:
        self.cleared = False

    async def clear(self):
        self.cleared = True


async def test_bot_forwards_problem_and_routes_admin_reply(db_sessionmaker, monkeypatch):
    monkeypatch.setattr(support_handlers, "SessionLocal", db_sessionmaker)
    bot = _FakeBot()

    problem = _FakeMessage(42, None)  # a screenshot without caption
    state = _FakeState()
    await support_handlers.forward_problem(problem, state, bot)  # type: ignore[arg-type]
    assert state.cleared
    assert [chat for chat, _ in bot.sent] == [900, 901]
    assert problem.copied_to == [900, 901]  # the screenshot itself is delivered too
    assert problem.answers[-1].startswith("✅")

    admin_msg = _FakeMessage(900, "Проверьте номер", reply_to=SimpleNamespace(message_id=501))
    await support_handlers.admin_reply(admin_msg, bot)  # type: ignore[arg-type]
    assert bot.sent[-1][0] == 42
    assert admin_msg.copied_to == [42]
    assert admin_msg.replies == ["✅ Ответ отправлен"]

    stray = _FakeMessage(900, "просто reply", reply_to=SimpleNamespace(message_id=12345))
    await support_handlers.admin_reply(stray, bot)  # type: ignore[arg-type]
    assert stray.replies == [] and stray.copied_to == []


def test_rate_limit_getter_is_public():
    assert callable(rate_limit.get_redis)
