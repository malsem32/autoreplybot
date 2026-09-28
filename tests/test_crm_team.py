"""Leads mini-CRM, team access, group scope, match modes, rule tester,
CSV export, weekly digest and Pro reminders."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.core.config import settings
from backend.models.lead import Lead
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import team
from backend.services.rule_match import keyword_hit, matched_keyword
from tests.helpers import auth_headers
from workers import digests, responder


@pytest.fixture(autouse=True)
def _no_admins(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")


@pytest.mark.parametrize(
    ("keyword", "text", "mode", "expected"),
    [
        ("цена", "Какая ЦЕНА?", "contains", True),
        ("цен", "бесценные советы", "contains", True),
        ("цен", "бесценные советы", "word", False),
        ("цена", "а цена какая", "word", True),
        ("ёлка", "Елка есть?", "word", True),  # ё == е
        ("привет", "Привет!", "exact", False),
        ("привет", "  привет ", "exact", True),
    ],
)
def test_match_modes(keyword, text, mode, expected):
    assert keyword_hit(keyword, text, mode) is expected


def test_matched_keyword_reports_which_fired():
    assert matched_keyword("all", [], "contains", "что угодно") == ""
    assert matched_keyword("keywords", ["доставка", "цена"], "word", "а цена?") == "цена"
    assert matched_keyword("keywords", ["цена"], "word", "бесценно") is None


@dataclass
class _Rule:
    scope: str


def test_group_scope_is_pro():
    assert responder.scope_allows(_Rule("private"), in_group=False, has_pro=False)
    assert not responder.scope_allows(_Rule("groups"), in_group=False, has_pro=True)
    assert responder.scope_allows(_Rule("groups"), in_group=True, has_pro=True)
    assert not responder.scope_allows(_Rule("all"), in_group=True, has_pro=False)


def test_parse_team_code():
    assert team.parse_team_code("team_abc123") == "abc123"
    assert team.parse_team_code("ref_1") is None
    assert team.parse_team_code("team_../x") is None


def test_digest_text_skips_empty_weeks():
    empty = {"autoreplies": 0, "new_leads": 0, "open_leads": 0, "sent": 0, "failed": 0}
    assert digests.digest_text(empty) is None
    text = digests.digest_text({**empty, "autoreplies": 4, "sent": 9, "failed": 1})
    assert "Автоответов: 4" in text and "90% доставлено" in text


# --- API ----------------------------------------------------------------------


async def _user(db_sessionmaker, api, telegram_id: int, pro_days: int = 0) -> User:
    await api.get("/api/auth/accounts", headers=auth_headers(telegram_id))
    async with db_sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
        user.pro_expires_at = datetime.now(UTC) + timedelta(days=pro_days) if pro_days else None
        await db.commit()
        return user


async def _account(db_sessionmaker, user: User) -> int:
    async with db_sessionmaker() as db:
        account = TelegramAccount(
            user_id=user.id, phone="7999", encrypted_session="x", first_name="Магазин"
        )
        db.add(account)
        await db.commit()
        return account.id


async def test_rule_tester_explains_verdicts(api, db_sessionmaker):
    owner = await _user(db_sessionmaker, api, 1, pro_days=5)
    account = await _account(db_sessionmaker, owner)
    h = auth_headers(1)
    price = (
        await api.post(
            f"/api/autoresponder/{account}/rules",
            json={
                "response_text": "Прайс",
                "trigger_type": "keywords",
                "keywords": ["цена"],
                "match_mode": "word",
            },
            headers=h,
        )
    ).json()
    groups = (
        await api.post(
            f"/api/autoresponder/{account}/rules",
            json={"response_text": "В группе", "scope": "groups"},
            headers=h,
        )
    ).json()
    fallback = (
        await api.post(
            f"/api/autoresponder/{account}/rules", json={"response_text": "Привет"}, headers=h
        )
    ).json()

    res = (
        await api.post(f"/api/autoresponder/{account}/test", json={"text": "а цена?"}, headers=h)
    ).json()
    assert res["answer_rule_id"] == price["id"]

    res = (
        await api.post(f"/api/autoresponder/{account}/test", json={"text": "бесценно"}, headers=h)
    ).json()
    assert res["answer_rule_id"] == fallback["id"]
    by_id = {v["rule_id"]: v for v in res["verdicts"]}
    assert not by_id[price["id"]]["matched"]
    assert by_id[groups["id"]]["blocked_by"] == "scope"

    res = (
        await api.post(
            f"/api/autoresponder/{account}/test",
            json={"text": "эй", "in_group": True},
            headers=h,
        )
    ).json()
    assert res["answer_rule_id"] == groups["id"]


async def test_group_scope_needs_pro(api, db_sessionmaker):
    owner = await _user(db_sessionmaker, api, 1)
    account = await _account(db_sessionmaker, owner)
    resp = await api.post(
        f"/api/autoresponder/{account}/rules",
        json={"response_text": "x", "scope": "groups"},
        headers=auth_headers(1),
    )
    assert resp.status_code == 402


async def test_team_invite_accept_and_permissions(api, db_sessionmaker):
    owner = await _user(db_sessionmaker, api, 1, pro_days=5)
    account = await _account(db_sessionmaker, owner)

    # Without an invite a stranger sees nothing.
    assert (
        await api.get(f"/api/autoresponder/{account}/rules", headers=auth_headers(2))
    ).status_code == 404

    invite = (await api.post(f"/api/team/{account}/invite", headers=auth_headers(1))).json()
    token = team.parse_team_code(invite["link"].rsplit("start=", 1)[1])
    async with db_sessionmaker() as db:
        outcome, _ = await team.accept_invite(db, token, 2, "Помощник")
        assert outcome == "joined"
        again, _ = await team.accept_invite(db, token, 3, "Чужой")
        assert again == "invalid"  # single use

    accounts = (await api.get("/api/auth/accounts", headers=auth_headers(2))).json()
    assert [(a["id"], a["role"]) for a in accounts] == [(account, "member")]

    # The member manages rules within the owner's Pro...
    resp = await api.post(
        f"/api/autoresponder/{account}/rules",
        json={"response_text": "hi", "notify_owner": True},
        headers=auth_headers(2),
    )
    assert resp.status_code == 201
    # ...but can't delete the account or see the team.
    assert (
        await api.delete(f"/api/auth/accounts/{account}", headers=auth_headers(2))
    ).status_code == 404
    assert (await api.get(f"/api/team/{account}", headers=auth_headers(2))).status_code == 404

    team_list = (await api.get(f"/api/team/{account}", headers=auth_headers(1))).json()
    assert [m["display_name"] for m in team_list["members"]] == ["Помощник"]

    # When the owner's Pro ends, shared access pauses.
    async with db_sessionmaker() as db:
        o = await db.get(User, owner.id)
        o.pro_expires_at = None
        await db.commit()
    assert (await api.get("/api/auth/accounts", headers=auth_headers(2))).json() == []
    assert (
        await api.get(f"/api/autoresponder/{account}/rules", headers=auth_headers(2))
    ).status_code == 404


async def test_team_invite_needs_pro(api, db_sessionmaker):
    owner = await _user(db_sessionmaker, api, 1)
    account = await _account(db_sessionmaker, owner)
    resp = await api.post(f"/api/team/{account}/invite", headers=auth_headers(1))
    assert resp.status_code == 402


async def test_leads_list_update_and_export(api, db_sessionmaker, monkeypatch):
    owner = await _user(db_sessionmaker, api, 1, pro_days=5)
    account = await _account(db_sessionmaker, owner)
    async with db_sessionmaker() as db:
        db.add(
            Lead(account_id=account, peer_id=10, name="Анна", last_text="цена?", messages_count=1)
        )
        db.add(Lead(account_id=account, peer_id=11, name="Борис", status="done", messages_count=2))
        await db.commit()

    data = (await api.get(f"/api/leads/{account}", headers=auth_headers(1))).json()
    assert data["counts"] == {"new": 1, "in_work": 0, "done": 1}
    anna = next(lead for lead in data["leads"] if lead["name"] == "Анна")

    updated = await api.patch(
        f"/api/leads/{account}/{anna['id']}",
        json={"status": "in_work", "note": "перезвонить"},
        headers=auth_headers(1),
    )
    assert updated.json()["status"] == "in_work"

    sent: dict = {}

    async def fake_send(telegram_id, filename, content, caption):
        sent.update(telegram_id=telegram_id, filename=filename, content=content)
        return True

    monkeypatch.setattr("backend.api.crm.send_document", fake_send)
    resp = await api.post(f"/api/export/leads/{account}", headers=auth_headers(1))
    assert resp.status_code == 202 and resp.json()["rows"] == 2
    assert sent["telegram_id"] == 1
    csv_text = sent["content"].decode("utf-8-sig")
    assert "Анна" in csv_text and "перезвонить" in csv_text and "В работе" in csv_text


async def test_leads_are_pro(api, db_sessionmaker):
    owner = await _user(db_sessionmaker, api, 1)
    account = await _account(db_sessionmaker, owner)
    assert (await api.get(f"/api/leads/{account}", headers=auth_headers(1))).status_code == 402


async def test_weekly_digest_opt_out(api):
    assert (await api.get("/api/me", headers=auth_headers(1))).json() == {"weekly_digest": True}
    resp = await api.patch("/api/me", json={"weekly_digest": False}, headers=auth_headers(1))
    assert resp.json() == {"weekly_digest": False}


# --- Worker-side jobs ------------------------------------------------------------


@dataclass
class _Sender:
    id: int
    first_name: str = "Анна"
    last_name: str | None = None
    username: str | None = "anna"


@dataclass
class _Message:
    from_user: _Sender
    text: str = "Сколько стоит?"
    caption: str | None = None
    extra: dict = field(default_factory=dict)


async def test_upsert_lead_counts_and_reopens(db_sessionmaker, api, monkeypatch):
    owner = await _user(db_sessionmaker, api, 1, pro_days=5)
    account = await _account(db_sessionmaker, owner)
    monkeypatch.setattr(responder, "SessionLocal", db_sessionmaker)

    lead = await responder.upsert_lead(account, _Message(_Sender(id=50)))
    assert lead.messages_count == 1 and lead.status == "new"
    async with db_sessionmaker() as db:
        stored = await db.get(Lead, lead.id)
        stored.status = "done"
        await db.commit()
    again = await responder.upsert_lead(account, _Message(_Sender(id=50), text="ещё вопрос"))
    assert again.id == lead.id and again.messages_count == 2
    assert again.status == "new" and again.last_text == "ещё вопрос"

    keyboard = responder.lead_keyboard(again, "anna")
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == f"lead:{lead.id}:in_work"
    assert keyboard["inline_keyboard"][1][0]["url"] == "https://t.me/anna"


async def test_pro_reminder_sent_once_per_expiry(db_sessionmaker, api, monkeypatch):
    await _user(db_sessionmaker, api, 1, pro_days=2)
    await _user(db_sessionmaker, api, 2, pro_days=20)
    monkeypatch.setattr(digests, "SessionLocal", db_sessionmaker)
    messages: list = []

    async def fake_send(telegram_id, text, reply_markup=None):
        messages.append((telegram_id, reply_markup))
        return True

    monkeypatch.setattr(digests, "send_message", fake_send)
    assert await digests.send_pro_reminders() == 1
    assert (
        messages[0][0] == 1
        and messages[0][1]["inline_keyboard"][0][0]["callback_data"] == "pro_menu"
    )
    assert await digests.send_pro_reminders() == 0


async def test_weekly_digest_only_on_monday_and_only_with_activity(
    db_sessionmaker, api, monkeypatch
):
    owner = await _user(db_sessionmaker, api, 1, pro_days=30)
    account = await _account(db_sessionmaker, owner)
    monkeypatch.setattr(digests, "SessionLocal", db_sessionmaker)
    messages: list = []

    async def fake_send(telegram_id, text, reply_markup=None):
        messages.append(text)
        return True

    monkeypatch.setattr(digests, "send_message", fake_send)
    tuesday = datetime(2026, 9, 29, 12, tzinfo=UTC)
    monday = datetime(2026, 9, 28, 12, tzinfo=UTC)
    assert await digests.send_weekly_digests(tuesday) == 0

    async with db_sessionmaker() as db:
        db.add(
            Lead(account_id=account, peer_id=1, name="Анна", created_at=monday - timedelta(days=1))
        )
        await db.commit()
    assert await digests.send_weekly_digests(monday) == 1
    assert "Новых обращений: 1" in messages[0]
    assert await digests.send_weekly_digests(monday) == 0  # once a week
