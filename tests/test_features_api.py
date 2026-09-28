"""API-level checks of albums, Pro limits, referrals and account removal."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.core import uploads
from backend.core.config import settings
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from tests.helpers import auth_headers


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    return tmp_path


def _make_photo(upload_dir, n: int) -> str:
    name = f"{n:032x}.jpg"
    (upload_dir / name).write_bytes(b"jpeg")
    return name


async def _account(api, db_sessionmaker, telegram_id: int = 42, pro: bool = False) -> int:
    await api.get("/api/auth/accounts", headers=auth_headers(telegram_id))  # creates the User
    async with db_sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
        if pro:
            user.pro_expires_at = datetime.now(UTC) + timedelta(days=5)
        account = TelegramAccount(user_id=user.id, phone="7999", encrypted_session="x")
        db.add(account)
        await db.commit()
        return account.id


def _campaign(**overrides) -> dict:
    return {"title": "t", "text_template": "<b>hi</b>", "target_chats": ["@chat"], **overrides}


async def test_free_plan_allows_one_photo_and_pro_allows_albums(
    api, db_sessionmaker, upload_dir, monkeypatch
):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    photos = [_make_photo(upload_dir, i) for i in range(3)]
    free_id = await _account(api, db_sessionmaker, telegram_id=1)
    headers = auth_headers(1)

    resp = await api.post(
        f"/api/broadcasts/{free_id}/campaigns", json=_campaign(photos=photos), headers=headers
    )
    assert resp.status_code == 402

    resp = await api.post(
        f"/api/broadcasts/{free_id}/campaigns",
        json=_campaign(photos=[f"/api/uploads/{photos[0]}"]),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["photo_urls"] == [f"/api/uploads/{photos[0]}"]

    pro_id = await _account(api, db_sessionmaker, telegram_id=2, pro=True)
    resp = await api.post(
        f"/api/broadcasts/{pro_id}/campaigns",
        json=_campaign(photos=photos),
        headers=auth_headers(2),
    )
    assert resp.status_code == 201, resp.text
    assert len(resp.json()["photo_urls"]) == 3


async def test_arbitrary_file_paths_are_rejected(api, db_sessionmaker, upload_dir):
    account_id = await _account(api, db_sessionmaker)
    resp = await api.post(
        f"/api/autoresponder/{account_id}/rules",
        json={"response_text": "hi", "photos": ["/etc/passwd"]},
        headers=auth_headers(),
    )
    assert resp.status_code == 400


async def test_replacing_photos_deletes_the_old_files(api, db_sessionmaker, upload_dir):
    account_id = await _account(api, db_sessionmaker)
    old, new = _make_photo(upload_dir, 1), _make_photo(upload_dir, 2)
    rule = (
        await api.post(
            f"/api/autoresponder/{account_id}/rules",
            json={"response_text": "hi", "photos": [old]},
            headers=auth_headers(),
        )
    ).json()
    resp = await api.patch(
        f"/api/autoresponder/{account_id}/rules/{rule['id']}",
        json={"photos": [new]},
        headers=auth_headers(),
    )
    assert resp.json()["photo_urls"] == [f"/api/uploads/{new}"]
    assert not (upload_dir / old).exists()
    assert (upload_dir / new).exists()


async def test_free_plan_rule_limit(api, db_sessionmaker, upload_dir, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    account_id = await _account(api, db_sessionmaker)
    statuses = []
    for _ in range(4):
        resp = await api.post(
            f"/api/autoresponder/{account_id}/rules",
            json={"response_text": "hi"},
            headers=auth_headers(),
        )
        statuses.append(resp.status_code)
    assert statuses == [201, 201, 201, 402]


async def test_tags_and_forward_protection_need_pro(api, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    account_id = await _account(api, db_sessionmaker)
    for option in ("tag_random_users", "protect_content", "hide_signature"):
        resp = await api.post(
            f"/api/broadcasts/{account_id}/campaigns",
            json=_campaign(**{option: True}),
            headers=auth_headers(),
        )
        assert resp.status_code == 402, option


async def test_delete_account_removes_its_data(api, db_sessionmaker, upload_dir):
    account_id = await _account(api, db_sessionmaker)
    photo = _make_photo(upload_dir, 7)
    await api.post(
        f"/api/broadcasts/{account_id}/campaigns",
        json=_campaign(photos=[photo]),
        headers=auth_headers(),
    )
    resp = await api.delete(f"/api/auth/accounts/{account_id}", headers=auth_headers())
    assert resp.status_code == 204
    assert (await api.get("/api/auth/accounts", headers=auth_headers())).json() == []
    assert not (upload_dir / photo).exists()


async def test_foreign_account_is_not_accessible(api, db_sessionmaker):
    account_id = await _account(api, db_sessionmaker, telegram_id=1)
    resp = await api.delete(f"/api/auth/accounts/{account_id}", headers=auth_headers(2))
    assert resp.status_code == 404


async def test_referral_is_recorded_for_new_users_only(api, db_sessionmaker):
    await api.get("/api/referrals", headers=auth_headers(100))
    await api.get("/api/referrals", headers=auth_headers(200, start_param="ref_100"))
    await api.get("/api/referrals", headers=auth_headers(100, start_param="ref_200"))  # existing
    await api.get("/api/referrals", headers=auth_headers(300, start_param="ref_300"))  # self

    stats = (await api.get("/api/referrals", headers=auth_headers(100))).json()
    assert stats["invited_count"] == 1
    assert stats["link"].endswith("?start=ref_100")
    assert (await api.get("/api/referrals", headers=auth_headers(200))).json()["invited_count"] == 0
    assert (await api.get("/api/referrals", headers=auth_headers(300))).json()["invited_count"] == 0


async def test_referral_bonus_is_granted_once_to_both(api, db_sessionmaker):
    from backend.services import pro, referrals

    await api.get("/api/referrals", headers=auth_headers(100))
    await api.get("/api/referrals", headers=auth_headers(200, start_param="ref_100"))

    async with db_sessionmaker() as db:
        invitee = await pro.grant_access(db, 200, 30)
        reward = await referrals.reward_first_payment(db, invitee)
        assert reward is not None and reward[1] == 7
        assert await referrals.reward_first_payment(db, invitee) is None  # only once

        inviter = await db.scalar(select(User).where(User.telegram_id == 100))
        assert inviter.referral_days_earned == 7
        assert inviter.pro_expires_at is not None


async def test_admin_stats_and_pro_settings(api, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "999")
    await _account(api, db_sessionmaker)
    assert (await api.get("/api/admin/stats", headers=auth_headers(42))).status_code == 403

    stats = (await api.get("/api/admin/stats", headers=auth_headers(999))).json()
    assert stats["accounts_total"] == 1

    resp = await api.patch(
        "/api/admin/pro", json={"referral_bonus_days": 10}, headers=auth_headers(999)
    )
    assert resp.json()["referral_bonus_days"] == 10
