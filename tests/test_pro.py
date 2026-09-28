from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.core.config import settings
from backend.services import pro


@dataclass
class _FakeUser:
    telegram_id: int
    pro_expires_at: datetime | None = None


def test_admin_has_access_without_a_purchase(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "777")
    assert pro.is_admin(_FakeUser(telegram_id=777))
    assert pro.has_access(_FakeUser(telegram_id=777, pro_expires_at=None))


def test_non_admin_without_a_purchase_has_no_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "777")
    assert not pro.has_access(_FakeUser(telegram_id=1, pro_expires_at=None))


def test_non_admin_with_expired_purchase_has_no_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    expired = datetime.now(UTC) - timedelta(days=1)
    assert not pro.has_access(_FakeUser(telegram_id=1, pro_expires_at=expired))


def test_non_admin_with_active_purchase_has_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    active = datetime.now(UTC) + timedelta(days=1)
    assert pro.has_access(_FakeUser(telegram_id=1, pro_expires_at=active))


def test_photo_limit_depends_on_plan(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    active = datetime.now(UTC) + timedelta(days=1)
    assert pro.max_photos(_FakeUser(telegram_id=1)) == pro.FREE_MAX_PHOTOS
    assert pro.max_photos(_FakeUser(telegram_id=1, pro_expires_at=active)) == pro.PRO_MAX_PHOTOS


def test_invoice_payload_roundtrip_and_legacy_prefix():
    assert pro.parse_invoice_payload(pro.invoice_payload(42, 30)) == (42, 30)
    assert pro.parse_invoice_payload("tag_broadcast:42:30") == (42, 30)
    assert pro.parse_invoice_payload("other:42:30") is None
    assert pro.parse_invoice_payload("pro:x:30") is None
