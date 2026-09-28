"""Pro automation: schedule, smart autoreply filters, broadcast auto-disable
and reports, per-chat stats, templates, plans and trial."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.core.config import settings
from backend.models.broadcast import BroadcastCampaign, BroadcastLog
from backend.models.feature_settings import ProSetting
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import pro
from backend.services.schedule import is_within_schedule
from tests.helpers import auth_headers
from workers.broadcaster import report_text, should_disable
from workers.responder import is_new_contact, owner_recently_active

WEEKDAYS = list(range(5))  # Mon–Fri


def _at(weekday: int, hh: int, mm: int = 0) -> datetime:
    # 2026-09-07 is a Monday; UTC keeps the math obvious.
    return datetime(2026, 9, 7 + weekday, hh, mm, tzinfo=UTC)


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (_at(0, 20), True),  # Monday evening, window started Monday
        (_at(1, 8, 59), True),  # Tuesday morning, window started Monday
        (_at(1, 9, 0), False),  # end is exclusive
        (_at(1, 12), False),  # working hours
        (_at(5, 8), True),  # Saturday morning: Friday's window still running
        (_at(5, 20), False),  # Saturday evening: no window starts on Saturday
        (_at(6, 8), False),  # Sunday morning
    ],
)
def test_overnight_schedule(moment, expected):
    assert is_within_schedule(WEEKDAYS, "19:00", "09:00", "UTC", moment) is expected


def test_daytime_schedule_and_timezone():
    # 10:00 UTC is 13:00 in Moscow: inside a 12:00–14:00 Moscow window.
    assert is_within_schedule([0], "12:00", "14:00", "Europe/Moscow", _at(0, 10))
    assert not is_within_schedule([0], "12:00", "14:00", "UTC", _at(0, 10))


def test_equal_start_and_end_means_whole_day():
    assert is_within_schedule([2], "00:00", "00:00", "UTC", _at(2, 15))
    assert not is_within_schedule([2], "00:00", "00:00", "UTC", _at(3, 15))


@dataclass
class _Msg:
    id: int
    outgoing: bool
    date: datetime


def test_owner_activity_and_new_contact_detection():
    # Pyrogram message dates are naive local time.
    now = datetime(2026, 9, 28, 12, 0, tzinfo=UTC).astimezone().replace(tzinfo=None)
    history = [_Msg(10, False, now), _Msg(9, True, now - timedelta(minutes=5))]
    assert owner_recently_active(history, 10, now)
    assert not owner_recently_active(history, 3, now)
    assert not owner_recently_active(history, 0, now)
    assert not is_new_contact(history, current_message_id=10)
    assert is_new_contact([_Msg(10, False, now)], current_message_id=10)


def test_auto_disable_needs_consecutive_failures():
    assert should_disable(["error", "error", "error"])
    assert not should_disable(["error", "error"])
    assert not should_disable(["error", "success", "error"])
    assert should_disable(["error", "error", "error", "success"])  # newest first


def test_report_escapes_titles_and_lists_disabled_chats():
    text = report_text("<Акция>", 5, 2, ["@dead_chat"])
    assert "&lt;Акция&gt;" in text
    assert "Доставлено: 5" in text
    assert "@dead_chat" in text


def test_plans_hide_zero_price_and_match_prices():
    row = ProSetting(
        stars_price=50, duration_days=30, quarter_stars_price=0, year_stars_price=450, trial_days=3
    )
    assert [p.id for p in pro.plans(row)] == ["month", "year"]
    assert pro.price_matches(row, 365, 450)
    assert not pro.price_matches(row, 365, 1)  # stale invoice after a price change


# --- API ----------------------------------------------------------------------


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


async def test_rule_pro_options_need_pro(api, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    free = await _account(api, db_sessionmaker, telegram_id=1)
    resp = await api.post(
        f"/api/autoresponder/{free}/rules",
        json={"response_text": "hi", "schedule_enabled": True},
        headers=auth_headers(1),
    )
    assert resp.status_code == 402

    paid = await _account(api, db_sessionmaker, telegram_id=2, pro_days=5)
    resp = await api.post(
        f"/api/autoresponder/{paid}/rules",
        json={
            "response_text": "hi",
            "schedule_enabled": True,
            "schedule_days": [4, 0, 0],
            "schedule_start": "19:00",
            "schedule_end": "09:00",
            "timezone": "Europe/Moscow",
            "typing_delay_seconds": 5,
            "notify_owner": True,
        },
        headers=auth_headers(2),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["schedule_days"] == [0, 4]
    assert body["replies_7d"] == 0


async def test_rule_rejects_bad_time_and_timezone(api, db_sessionmaker):
    account = await _account(api, db_sessionmaker, pro_days=5)
    for bad in ({"schedule_start": "25:00"}, {"timezone": "Mars/Olympus"}):
        resp = await api.post(
            f"/api/autoresponder/{account}/rules",
            json={"response_text": "hi", **bad},
            headers=auth_headers(),
        )
        assert resp.status_code == 422


async def test_campaign_stats_restore_and_pro_gate(api, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    account = await _account(api, db_sessionmaker, pro_days=5)
    created = (
        await api.post(
            f"/api/broadcasts/{account}/campaigns",
            json={
                "title": "t",
                "text_template": "x",
                "target_chats": ["@a", "@b"],
                "auto_disable_failing": True,
                "notify_report": True,
            },
            headers=auth_headers(),
        )
    ).json()
    async with db_sessionmaker() as db:
        now = datetime.now(UTC)
        for status, target in [("success", "@a"), ("error", "@b"), ("error", "@b")]:
            db.add(
                BroadcastLog(
                    campaign_id=created["id"], target=target, chat_id=1, sent_at=now, status=status
                )
            )
        campaign = await db.get(BroadcastCampaign, created["id"])
        campaign.disabled_targets = ["@b"]
        await db.commit()

    stats = (
        await api.get(
            f"/api/broadcasts/{account}/campaigns/{created['id']}/stats", headers=auth_headers()
        )
    ).json()
    by_target = {t["target"]: t for t in stats["targets"]}
    assert by_target["@a"]["sent"] == 1
    assert by_target["@b"]["failed"] == 2 and by_target["@b"]["disabled"]
    assert stats["sent"] == 1 and stats["failed"] == 2

    restored = await api.patch(
        f"/api/broadcasts/{account}/campaigns/{created['id']}",
        json={"disabled_targets": []},
        headers=auth_headers(),
    )
    assert restored.json()["disabled_targets"] == []

    # Without Pro: stats are locked.
    async with db_sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 42))
        user.pro_expires_at = None
        await db.commit()
    resp = await api.get(
        f"/api/broadcasts/{account}/campaigns/{created['id']}/stats", headers=auth_headers()
    )
    assert resp.status_code == 402


async def test_templates_builtin_for_all_saving_is_pro(api, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    await _account(api, db_sessionmaker, telegram_id=1)
    listing = (await api.get("/api/templates", headers=auth_headers(1))).json()
    assert listing and all(t["builtin"] for t in listing)

    resp = await api.post(
        "/api/templates", json={"title": "Мой", "text": "hi"}, headers=auth_headers(1)
    )
    assert resp.status_code == 402

    await _account(api, db_sessionmaker, telegram_id=2, pro_days=5)
    saved = (
        await api.post(
            "/api/templates", json={"title": "Мой", "text": "hi"}, headers=auth_headers(2)
        )
    ).json()
    listing = (await api.get("/api/templates", headers=auth_headers(2))).json()
    assert listing[0]["id"] == saved["id"] and not listing[0]["builtin"]
    # Someone else can't delete it.
    assert (
        await api.delete(f"/api/templates/{saved['id']}", headers=auth_headers(1))
    ).status_code == 404
    assert (
        await api.delete(f"/api/templates/{saved['id']}", headers=auth_headers(2))
    ).status_code == 204


async def test_trial_is_granted_once(api, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    status = (await api.get("/api/features/pro", headers=auth_headers(5))).json()
    assert status["trial_available"] and not status["has_access"]
    assert [p["id"] for p in status["plans"]] == ["month", "quarter", "year"]
    assert status["plans"][2]["discount_percent"] > 0

    started = await api.post("/api/features/pro/trial", headers=auth_headers(5))
    assert started.status_code == 200
    assert started.json()["has_access"] and not started.json()["trial_available"]
    again = await api.post("/api/features/pro/trial", headers=auth_headers(5))
    assert again.status_code == 400


async def test_admin_stats_include_autoreplies_and_flood_waits(api, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "999")
    stats = (await api.get("/api/admin/stats", headers=auth_headers(999))).json()
    for key in (
        "autoreplies_24h",
        "flood_waits_24h",
        "users_new_1d",
        "users_new_30d",
        "pro_active",
    ):
        assert key in stats
