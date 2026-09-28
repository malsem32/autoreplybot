"""End-to-end tests of the login flows in backend/api/auth.py with a fake
MTProto client (the sandbox has no access to Telegram servers)."""

import pytest
from pyrogram import enums
from pyrogram import types as tg_types
from pyrogram.errors import FloodWait, PasswordHashInvalid, PhoneCodeInvalid, SessionPasswordNeeded
from pyrogram.raw import types as raw_types

from backend.api import auth
from backend.core.security import decrypt_session
from tests.helpers import auth_headers


class _FakeStorage:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def user_id(self, value=None):
        self.values["user_id"] = value

    async def is_bot(self, value=None):
        self.values["is_bot"] = value


class FakeClient:
    """Mimics the subset of pyrogram.Client used by the auth endpoints."""

    instances: list["FakeClient"] = []
    code = "12345"
    password: str | None = None
    sent_type = enums.SentCodeType.APP
    qr_results: list = []

    def __init__(self, name: str, proxy=None) -> None:
        self.name = name
        self.is_connected = False
        self.storage = _FakeStorage()
        self.phone_hash = "hash-1"
        self.signed_in = False
        FakeClient.instances.append(self)

    async def connect(self) -> None:
        self.is_connected = True

    async def disconnect(self) -> None:
        self.is_connected = False

    def _sent(self, sent_type) -> tg_types.SentCode:
        return tg_types.SentCode(
            type=sent_type,
            phone_code_hash=self.phone_hash,
            next_type=enums.NextCodeType.SMS,
            timeout=60,
        )

    async def send_code(self, phone: str) -> tg_types.SentCode:
        self.phone = phone
        return self._sent(FakeClient.sent_type)

    async def resend_code(self, phone: str, phone_code_hash: str) -> tg_types.SentCode:
        assert phone_code_hash == self.phone_hash
        self.phone_hash = "hash-2"
        return self._sent(enums.SentCodeType.SMS)

    async def sign_in(self, phone: str, phone_code_hash: str, code: str):
        assert phone_code_hash == self.phone_hash
        if code != FakeClient.code:
            raise PhoneCodeInvalid()
        if FakeClient.password is not None:
            raise SessionPasswordNeeded()
        self.signed_in = True
        return self._me()

    async def check_password(self, password: str):
        if password != FakeClient.password:
            raise PasswordHashInvalid()
        self.signed_in = True
        return self._me()

    async def get_password_hint(self) -> str:
        return "кот"

    def _me(self) -> tg_types.User:
        return tg_types.User(id=555, first_name="Иван", username="ivan", phone_number="79991234567")

    async def get_me(self) -> tg_types.User:
        return self._me()

    async def export_session_string(self) -> str:
        return f"session-of-{self.name}"

    async def invoke(self, query):
        return FakeClient.qr_results.pop(0)

    handle_updates = None


_REAL_NEW_CLIENT = auth._new_client


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    FakeClient.instances = []
    FakeClient.password = None
    FakeClient.sent_type = enums.SentCodeType.APP
    FakeClient.qr_results = []
    auth._pending_logins.clear()
    auth._qr_logins.clear()
    monkeypatch.setattr(auth, "_new_client", lambda name, proxy=None: FakeClient(name, proxy))
    return FakeClient


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+7 (999) 123-45-67", "79991234567"),
        ("89991234567", "79991234567"),
        ("+380 50 123 4567", "380501234567"),
        ("84912345678", "84912345678"),  # not rewritten: no country code starts with 89
    ],
)
def test_normalize_phone(raw, expected):
    assert auth.normalize_phone(raw) == expected


def test_normalize_phone_rejects_garbage():
    with pytest.raises(Exception) as exc:
        auth.normalize_phone("12")
    assert exc.value.status_code == 400


async def test_endpoints_require_valid_init_data(api):
    resp = await api.post("/api/auth/send_code", json={"phone": "+79991234567"})
    assert resp.status_code == 422  # Authorization header missing
    resp = await api.post(
        "/api/auth/send_code",
        json={"phone": "+79991234567"},
        headers={"Authorization": "tma auth_date=1&hash=bad"},
    )
    assert resp.status_code == 401


async def test_code_login_happy_path(api):
    headers = auth_headers()
    resp = await api.post(
        "/api/auth/send_code", json={"phone": "+7 999 123-45-67"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    sent = resp.json()
    assert sent["phone"] == "79991234567"
    assert sent["code_type"] == "app"  # UI tells the user to look in the Telegram app
    assert sent["next_type"] == "sms"

    resp = await api.post(
        "/api/auth/sign_in",
        json={"phone": sent["phone"], "phone_code_hash": sent["phone_code_hash"], "code": "12 345"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["account"]["username"] == "ivan"
    assert not FakeClient.instances[0].is_connected  # temporary client cleaned up
    assert auth._pending_logins == {}

    resp = await api.get("/api/auth/accounts", headers=headers)
    assert [a["phone"] for a in resp.json()] == ["79991234567"]


async def test_wrong_code_can_be_retried(api):
    headers = auth_headers()
    sent = (
        await api.post("/api/auth/send_code", json={"phone": "+79991234567"}, headers=headers)
    ).json()
    payload = {"phone": sent["phone"], "phone_code_hash": sent["phone_code_hash"]}

    resp = await api.post("/api/auth/sign_in", json={**payload, "code": "00000"}, headers=headers)
    assert resp.status_code == 400
    assert "Неверный код" in resp.json()["detail"]

    resp = await api.post("/api/auth/sign_in", json={**payload, "code": "12345"}, headers=headers)
    assert resp.json()["status"] == "success"


async def test_resend_switches_to_sms_and_new_hash_is_used(api):
    headers = auth_headers()
    sent = (
        await api.post("/api/auth/send_code", json={"phone": "+79991234567"}, headers=headers)
    ).json()
    resent = (
        await api.post(
            "/api/auth/resend_code",
            json={"phone": sent["phone"], "phone_code_hash": sent["phone_code_hash"]},
            headers=headers,
        )
    ).json()
    assert resent["code_type"] == "sms"
    assert resent["phone_code_hash"] == "hash-2"

    # Even with the stale hash echoed back, the server uses the fresh one.
    resp = await api.post(
        "/api/auth/sign_in",
        json={"phone": sent["phone"], "phone_code_hash": sent["phone_code_hash"], "code": "12345"},
        headers=headers,
    )
    assert resp.json()["status"] == "success"


async def test_two_factor_flow_with_hint_and_retry(api, fake_client):
    fake_client.password = "secret"
    headers = auth_headers()
    sent = (
        await api.post("/api/auth/send_code", json={"phone": "+79991234567"}, headers=headers)
    ).json()
    resp = await api.post(
        "/api/auth/sign_in",
        json={"phone": sent["phone"], "phone_code_hash": sent["phone_code_hash"], "code": "12345"},
        headers=headers,
    )
    assert resp.json() == {"status": "password_required", "account": None, "password_hint": "кот"}

    resp = await api.post(
        "/api/auth/check_password", json={"phone": sent["phone"], "password": "x"}, headers=headers
    )
    assert resp.status_code == 400
    assert "пароль" in resp.json()["detail"]

    resp = await api.post(
        "/api/auth/check_password",
        json={"phone": sent["phone"], "password": "secret"},
        headers=headers,
    )
    assert resp.json()["status"] == "success"


async def test_pending_login_is_isolated_per_mini_app_user(api):
    sent = (
        await api.post(
            "/api/auth/send_code", json={"phone": "+79991234567"}, headers=auth_headers(1)
        )
    ).json()
    resp = await api.post(
        "/api/auth/sign_in",
        json={"phone": sent["phone"], "phone_code_hash": sent["phone_code_hash"], "code": "12345"},
        headers=auth_headers(2),
    )
    assert resp.status_code == 400


async def test_setup_email_required_suggests_qr(api, fake_client):
    fake_client.sent_type = enums.SentCodeType.SETUP_EMAIL_REQUIRED
    resp = await api.post(
        "/api/auth/send_code", json={"phone": "+79991234567"}, headers=auth_headers()
    )
    assert resp.status_code == 400
    assert "QR" in resp.json()["detail"]
    assert not FakeClient.instances[0].is_connected


async def test_flood_wait_is_reported_readably(api, monkeypatch):
    async def flood(self, phone):
        raise FloodWait(value=125)

    monkeypatch.setattr(FakeClient, "send_code", flood)
    resp = await api.post(
        "/api/auth/send_code", json={"phone": "+79991234567"}, headers=auth_headers()
    )
    assert resp.status_code == 429
    assert "2 мин" in resp.json()["detail"]


async def test_relogin_updates_existing_account_instead_of_duplicating(api):
    headers = auth_headers()
    for _ in range(2):
        sent = (
            await api.post("/api/auth/send_code", json={"phone": "+79991234567"}, headers=headers)
        ).json()
        await api.post(
            "/api/auth/sign_in",
            json={
                "phone": sent["phone"],
                "phone_code_hash": sent["phone_code_hash"],
                "code": "12345",
            },
            headers=headers,
        )
    accounts = (await api.get("/api/auth/accounts", headers=headers)).json()
    assert len(accounts) == 1


def _login_token(expires_in: int = 30) -> raw_types.auth.LoginToken:
    import time

    return raw_types.auth.LoginToken(expires=int(time.time()) + expires_in, token=b"tok")


async def test_qr_login_success_after_scan(api, fake_client, db_sessionmaker):
    headers = auth_headers()
    fake_client.qr_results = [_login_token()]
    start = (await api.post("/api/auth/qr/start", headers=headers)).json()
    assert start["qr_url"].startswith("tg://login?token=")

    poll = (await api.get(f"/api/auth/qr/{start['request_id']}/poll", headers=headers)).json()
    assert poll["status"] == "pending"

    # Telegram pushes updateLoginToken once the QR is confirmed on a phone.
    auth._qr_logins[start["request_id"]].token_updated = True
    fake_client.qr_results = [
        raw_types.auth.LoginTokenSuccess(authorization=raw_types.auth.Authorization(user=None))
    ]
    poll = (await api.get(f"/api/auth/qr/{start['request_id']}/poll", headers=headers)).json()
    assert poll["status"] == "success"
    # QR logins must record the user id before exporting the session.
    assert FakeClient.instances[0].storage.values["user_id"] == 555

    async with db_sessionmaker() as db:
        from sqlalchemy import select

        from backend.models.telegram_account import TelegramAccount

        account = (await db.execute(select(TelegramAccount))).scalar_one()
        assert decrypt_session(account.encrypted_session).startswith("session-of-qr_")


async def test_qr_token_is_refreshed_before_it_expires(api, fake_client):
    headers = auth_headers()
    fake_client.qr_results = [_login_token(expires_in=2)]
    start = (await api.post("/api/auth/qr/start", headers=headers)).json()
    fake_client.qr_results = [_login_token(expires_in=30)]
    poll = (await api.get(f"/api/auth/qr/{start['request_id']}/poll", headers=headers)).json()
    assert poll["status"] == "pending"
    assert poll["qr_url"]  # a fresh QR to redraw


async def test_qr_login_with_two_factor(api, fake_client, monkeypatch):
    fake_client.password = "secret"
    headers = auth_headers()
    fake_client.qr_results = [_login_token()]
    start = (await api.post("/api/auth/qr/start", headers=headers)).json()
    auth._qr_logins[start["request_id"]].token_updated = True

    async def needs_password(self, query):
        raise SessionPasswordNeeded()

    monkeypatch.setattr(FakeClient, "invoke", needs_password)
    poll = (await api.get(f"/api/auth/qr/{start['request_id']}/poll", headers=headers)).json()
    assert poll["status"] == "password_required"
    assert poll["password_hint"] == "кот"

    resp = await api.post(
        f"/api/auth/qr/{start['request_id']}/password", json={"password": "secret"}, headers=headers
    )
    assert resp.json()["status"] == "success"


async def test_qr_session_is_private_to_its_owner(api, fake_client):
    fake_client.qr_results = [_login_token()]
    start = (await api.post("/api/auth/qr/start", headers=auth_headers(1))).json()
    resp = await api.get(f"/api/auth/qr/{start['request_id']}/poll", headers=auth_headers(2))
    assert resp.status_code == 404


async def test_unreachable_telegram_fails_fast_instead_of_hanging(api, monkeypatch):
    import asyncio

    async def hang(self):
        await asyncio.sleep(3600)

    monkeypatch.setattr(FakeClient, "connect", hang)
    monkeypatch.setattr(auth, "TELEGRAM_TIMEOUT_SECONDS", 0.05)
    resp = await api.post(
        "/api/auth/send_code", json={"phone": "+79991234567"}, headers=auth_headers()
    )
    assert resp.status_code == 503
    assert "Telegram" in resp.json()["detail"]


async def test_worker_and_login_present_the_same_device(monkeypatch):
    """One session must not flip between "Автопилот" and "Pyrogram/CPython"
    on the account's Devices screen (login vs worker)."""
    from backend.api import auth
    from backend.core.telegram_client import CLIENT_IDENTITY
    from workers import client_manager as cm

    created: list[dict] = []

    class _Client:
        def __init__(self, **kwargs):
            created.append(kwargs)

        async def start(self):
            return None

    monkeypatch.setattr(cm, "Client", _Client)
    monkeypatch.setattr(cm, "decrypt_session", lambda _s: "session")
    await cm.ClientManager().start(1, "encrypted")

    monkeypatch.setattr(auth, "Client", _Client)
    _REAL_NEW_CLIENT("login")  # the autouse fixture replaces auth._new_client
    assert len(created) == 2
    for kwargs in created:
        for key, value in CLIENT_IDENTITY.items():
            assert kwargs[key] == value
