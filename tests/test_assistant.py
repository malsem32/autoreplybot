"""Vacation mode, quick phrases and AI replies (AGENTS.md 4.17)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

from backend.core import rate_limit
from backend.core.config import settings
from backend.models.snippet import Snippet
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import ai, away
from backend.services.snippets import parse_trigger
from tests.helpers import auth_headers
from workers import snippets as snippet_worker


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None

    async def get(self, key: str) -> int | None:
        return self.values.get(key)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    monkeypatch.setattr(settings, "ai_provider", "")
    monkeypatch.setattr(settings, "ai_api_key", "")
    monkeypatch.setattr(settings, "ai_model", "")
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit, "get_redis", lambda: fake)


async def _account(api, db_sessionmaker, telegram_id: int = 42, pro_days: int = 0) -> int:
    await api.get("/api/auth/accounts", headers=auth_headers(telegram_id))
    async with db_sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
        if pro_days:
            user.pro_expires_at = datetime.now(UTC) + timedelta(days=pro_days)
        account = TelegramAccount(user_id=user.id, phone="7999", encrypted_session="x")
        db.add(account)
        await db.commit()
        return account.id


# --- Vacation mode ------------------------------------------------------------------


def test_away_text_fills_return_date():
    until = datetime(2026, 10, 11, 22, 0, tzinfo=UTC)  # 12 Oct 01:00 in Moscow
    text = away.render_away_text("Вернусь {дата}!", until, "Europe/Moscow")
    assert text == "Вернусь 12 октября!"


async def test_away_mode_lifecycle(api, db_sessionmaker):
    account_id = await _account(api, db_sessionmaker)
    until = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    resp = await api.put(
        f"/api/away/{account_id}",
        json={"until": until, "text": "В отпуске до {дата}", "timezone": "Europe/Moscow"},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] and "{дата}" not in body["preview"]

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    too_far = (datetime.now(UTC) + timedelta(days=120)).isoformat()
    for bad in (past, too_far):
        resp = await api.put(
            f"/api/away/{account_id}", json={"until": bad, "text": "x"}, headers=auth_headers()
        )
        assert resp.status_code == 400

    # Someone else's account is invisible.
    assert (await api.get(f"/api/away/{account_id}", headers=auth_headers(7))).status_code == 404

    stopped = await api.delete(f"/api/away/{account_id}", headers=auth_headers())
    assert stopped.json()["active"] is False


def test_is_away_expires_by_itself():
    account = TelegramAccount(away_until=datetime.now(UTC) - timedelta(minutes=1))
    assert not away.is_away(account, datetime.now(UTC))
    account.away_until = datetime.now(UTC) + timedelta(minutes=1)
    assert away.is_away(account, datetime.now(UTC))


# --- Quick phrases ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("!цена", "цена"), ("!Price_1", "price_1"), ("!цена сейчас", None), ("цена", None)],
)
def test_parse_trigger(text, expected):
    assert parse_trigger(text) == expected


async def test_snippet_limits_and_validation(api, db_sessionmaker):
    account_id = await _account(api, db_sessionmaker)
    url = f"/api/snippets/{account_id}"
    for i in range(3):
        resp = await api.post(url, json={"shortcut": f"!s{i}", "text": "t"}, headers=auth_headers())
        assert resp.status_code == 201
        assert resp.json()["shortcut"] == f"s{i}"  # the "!" is stripped
    over = await api.post(url, json={"shortcut": "s9", "text": "t"}, headers=auth_headers())
    assert over.status_code == 402

    assert (
        await api.post(url, json={"shortcut": "два слова", "text": "t"}, headers=auth_headers())
    ).status_code == 422
    listed = (await api.get(url, headers=auth_headers())).json()
    assert listed["limit"] == 3 and len(listed["snippets"]) == 3


async def test_snippet_duplicates_and_pro_lifts_limit(api, db_sessionmaker):
    account_id = await _account(api, db_sessionmaker, pro_days=5)
    url = f"/api/snippets/{account_id}"
    for i in range(4):
        await api.post(url, json={"shortcut": f"s{i}", "text": "t"}, headers=auth_headers())
    dup = await api.post(url, json={"shortcut": "s1", "text": "t"}, headers=auth_headers())
    assert dup.status_code == 409
    assert (await api.get(url, headers=auth_headers())).json()["limit"] is None


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.chat = SimpleNamespace(id=100)
        self.reply_to_message_id = None
        self.edited: str | None = None

    async def edit_text(self, text: str) -> None:
        self.edited = text


async def test_worker_expands_snippet_in_place(db_sessionmaker, monkeypatch):
    monkeypatch.setattr(snippet_worker, "SessionLocal", db_sessionmaker)
    async with db_sessionmaker() as db:
        user = User(telegram_id=5)
        db.add(user)
        await db.flush()
        account = TelegramAccount(user_id=user.id, phone="1", encrypted_session="x")
        db.add(account)
        await db.flush()
        db.add(Snippet(account_id=account.id, shortcut="цена", text="Стоимость — 100 ₽"))
        await db.commit()
        account_id = account.id

    message = _FakeMessage("!цена")
    assert await snippet_worker.expand(object(), account_id, message)  # type: ignore[arg-type]
    assert message.edited == "Стоимость — 100 ₽"

    unknown = _FakeMessage("!нет")
    assert not await snippet_worker.expand(object(), account_id, unknown)  # type: ignore[arg-type]
    assert unknown.edited is None


# --- AI ----------------------------------------------------------------------------


def test_sanitize_reply_is_safe_plain_text():
    assert ai.sanitize_reply("**Привет** <b>друг</b> `x`") == "Привет &lt;b&gt;друг&lt;/b&gt; x"
    assert ai.sanitize_reply("   ") is None
    long = ai.sanitize_reply("Предложение. " * 100)
    assert long is not None and len(long) <= ai.MAX_REPLY_CHARS + 1


def test_system_prompt_keeps_client_text_out_of_instructions():
    prompt = ai.build_system_prompt("Доставка 300 ₽", "formal", "Здравствуйте!")
    assert "Доставка 300 ₽" in prompt and "<message>" in prompt
    assert "официально" in prompt


async def test_generate_reply_off_or_failing_returns_none(monkeypatch):
    assert await ai.generate_reply("k", "friendly", "fallback", "Сколько стоит?") is None

    monkeypatch.setattr(settings, "ai_provider", "openai_compat")
    monkeypatch.setattr(settings, "ai_api_key", "key")
    monkeypatch.setattr(settings, "ai_model", "some/model:free")

    async def broken(system, user):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(ai, "_openai_compat", broken)
    assert await ai.generate_reply("k", "friendly", "fallback", "Сколько стоит?") is None

    async def works(system, user):
        assert "<message>" in user
        return "**Доставка** 300 ₽"

    monkeypatch.setattr(ai, "_openai_compat", works)
    assert await ai.generate_reply("k", "friendly", "f", "Сколько?") == "Доставка 300 ₽"


class _FakeAnthropic:
    def __init__(self, stop_reason: str) -> None:
        self.kwargs: dict = {}
        self.stop_reason = stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="text", text="Здравствуйте!")],
        )


async def test_anthropic_provider_uses_fallbacks_and_handles_refusal(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr(settings, "ai_api_key", "key")
    fake = _FakeAnthropic("end_turn")
    monkeypatch.setattr(ai, "_get_anthropic", lambda: fake)
    assert await ai.generate_reply("k", "friendly", "f", "Привет") == "Здравствуйте!"
    assert fake.kwargs["model"] == "claude-opus-5"
    assert fake.kwargs["fallbacks"] == "default"

    refusing = _FakeAnthropic("refusal")
    monkeypatch.setattr(ai, "_get_anthropic", lambda: refusing)
    assert await ai.generate_reply("k", "friendly", "f", "Привет") is None


async def test_daily_quota(monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_limit", 2)
    redis = _FakeRedis()
    results = [await ai.take_quota(redis, 1) for _ in range(3)]  # type: ignore[arg-type]
    assert results == [True, True, False]
    assert await ai.used_today(redis, 1) == 2  # type: ignore[arg-type]


async def test_ai_preview_needs_pro_and_provider(api, db_sessionmaker, monkeypatch):
    free = await _account(api, db_sessionmaker, telegram_id=10)
    resp = await api.post(f"/api/ai/{free}/preview", json={"text": "?"}, headers=auth_headers(10))
    assert resp.status_code == 402

    paid = await _account(api, db_sessionmaker, telegram_id=11, pro_days=3)
    resp = await api.post(f"/api/ai/{paid}/preview", json={"text": "?"}, headers=auth_headers(11))
    assert resp.status_code == 503  # no provider configured

    monkeypatch.setattr(settings, "ai_provider", "openai_compat")
    monkeypatch.setattr(settings, "ai_api_key", "key")
    monkeypatch.setattr(settings, "ai_model", "m:free")

    async def fake_generate(knowledge, tone, fallback, incoming):
        assert knowledge == "Доставка 300 ₽"
        return "Доставка стоит 300 ₽"

    monkeypatch.setattr(ai, "generate_reply", fake_generate)
    saved = await api.put(
        f"/api/ai/{paid}",
        json={"knowledge": "Доставка 300 ₽", "tone": "friendly"},
        headers=auth_headers(11),
    )
    assert saved.json()["available"] is True
    resp = await api.post(
        f"/api/ai/{paid}/preview", json={"text": "Доставка?"}, headers=auth_headers(11)
    )
    assert resp.json() == {"answer": "Доставка стоит 300 ₽", "used_today": 1}


async def test_rule_ai_reply_is_pro(api, db_sessionmaker):
    account_id = await _account(api, db_sessionmaker)
    resp = await api.post(
        f"/api/autoresponder/{account_id}/rules",
        json={"response_text": "Скоро отвечу", "ai_reply": True},
        headers=auth_headers(),
    )
    assert resp.status_code == 402
