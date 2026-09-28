"""Admin section: users, gifting Pro (audited), charts."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.api.admin import mask_phone
from backend.core.config import settings
from backend.models.admin import AdminAuditLog, Payment
from backend.models.autoresponder_rule import AutoresponderEvent, AutoresponderRule
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.services import bot_api
from tests.helpers import auth_headers

ADMIN = 999


@pytest.fixture(autouse=True)
def _admin(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", str(ADMIN))


def test_phone_is_masked():
    assert mask_phone("+7 999 123-45-67") == "+7999•••••67"
    assert mask_phone("12") == "•••"


async def _seed(db_sessionmaker) -> int:
    async with db_sessionmaker() as db:
        user = User(telegram_id=5, first_name="Анна", username="anna_shop")
        db.add_all([user, User(telegram_id=6, first_name="Борис")])
        await db.flush()
        account = TelegramAccount(
            user_id=user.id, phone="79991234567", encrypted_session="x", is_active=True
        )
        db.add(account)
        await db.flush()
        rule = AutoresponderRule(account_id=account.id, response_text="hi")
        db.add(rule)
        await db.flush()
        db.add(AutoresponderEvent(rule_id=rule.id, account_id=account.id))
        db.add(Payment(user_id=user.id, stars=450, days=365))
        await db.commit()
        return user.id


async def test_admin_endpoints_require_admin(api):
    for path in ("/api/admin/users", "/api/admin/timeseries"):
        assert (await api.get(path, headers=auth_headers(5))).status_code == 403


async def test_user_list_search_and_detail(api, db_sessionmaker):
    user_id = await _seed(db_sessionmaker)
    all_users = (await api.get("/api/admin/users", headers=auth_headers(ADMIN))).json()
    assert all_users["total"] >= 2

    found = (await api.get("/api/admin/users?q=@anna", headers=auth_headers(ADMIN))).json()["users"]
    assert [u["telegram_id"] for u in found] == [5]
    assert found[0]["accounts"] == 1

    with_accounts = (
        await api.get("/api/admin/users?filter=accounts", headers=auth_headers(ADMIN))
    ).json()["users"]
    assert [u["telegram_id"] for u in with_accounts] == [5]

    by_id = (await api.get("/api/admin/users?q=6", headers=auth_headers(ADMIN))).json()
    assert [u["first_name"] for u in by_id["users"]] == ["Борис"]

    detail = (await api.get(f"/api/admin/users/{user_id}", headers=auth_headers(ADMIN))).json()
    account = detail["account_list"][0]
    assert account["phone"] == "+7999•••••67"  # never the full number
    assert account["rules"] == 1 and account["autoreplies_7d"] == 1
    assert detail["payments"][0]["stars"] == 450


async def test_gift_and_revoke_pro_are_audited(api, db_sessionmaker, monkeypatch):
    user_id = await _seed(db_sessionmaker)
    notified: list[int] = []

    async def fake_send(telegram_id, text, reply_markup=None):
        notified.append(telegram_id)
        return True

    monkeypatch.setattr(bot_api, "send_message", fake_send)
    resp = await api.post(
        f"/api/admin/users/{user_id}/pro", json={"days": 30}, headers=auth_headers(ADMIN)
    )
    assert resp.status_code == 200
    assert resp.json()["has_pro"] is True
    assert notified == [5]

    revoked = await api.delete(f"/api/admin/users/{user_id}/pro", headers=auth_headers(ADMIN))
    assert revoked.json()["has_pro"] is False
    actions = [e["action"] for e in revoked.json()["audit"]]
    assert actions == ["pro_revoke", "pro_grant"]

    async with db_sessionmaker() as db:
        rows = (await db.execute(select(AdminAuditLog))).scalars().all()
        assert {r.admin_telegram_id for r in rows} == {ADMIN}

    bad = await api.post(
        f"/api/admin/users/{user_id}/pro", json={"days": 0}, headers=auth_headers(ADMIN)
    )
    assert bad.status_code == 422


async def test_timeseries_counts_per_day(api, db_sessionmaker):
    await _seed(db_sessionmaker)
    data = (await api.get("/api/admin/timeseries", headers=auth_headers(ADMIN))).json()
    assert len(data["days"]) == 30
    assert data["days"][-1] == datetime.now(UTC).date().isoformat()
    assert data["stars"][-1] == 450 and data["stars_30d"] == 450
    assert data["autoreplies"][-1] == 1
    assert data["users"][-1] >= 2


async def test_mini_app_keeps_profile_and_last_seen(api, db_sessionmaker):
    await api.get("/api/auth/accounts", headers=auth_headers(77))
    async with db_sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 77))
        assert user.first_name == "Test"
        assert user.last_seen_at is not None
        user.last_seen_at = datetime.now(UTC) - timedelta(hours=1)
        await db.commit()
    await api.get("/api/auth/accounts", headers=auth_headers(77))
    async with db_sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 77))
        seen = (
            user.last_seen_at.replace(tzinfo=UTC)
            if user.last_seen_at.tzinfo is None
            else user.last_seen_at
        )
        assert datetime.now(UTC) - seen < timedelta(minutes=1)
