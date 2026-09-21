from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.core.config import settings
from backend.services import tag_feature


@dataclass
class _FakeUser:
    telegram_id: int
    tag_feature_expires_at: datetime | None = None


def test_admin_has_access_without_a_purchase(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "777")
    assert tag_feature.is_admin(_FakeUser(telegram_id=777))
    assert tag_feature.has_access(_FakeUser(telegram_id=777, tag_feature_expires_at=None))


def test_non_admin_without_a_purchase_has_no_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "777")
    assert not tag_feature.has_access(_FakeUser(telegram_id=1, tag_feature_expires_at=None))


def test_non_admin_with_expired_purchase_has_no_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    expired = datetime.now(UTC) - timedelta(days=1)
    assert not tag_feature.has_access(_FakeUser(telegram_id=1, tag_feature_expires_at=expired))


def test_non_admin_with_active_purchase_has_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_telegram_ids", "")
    active = datetime.now(UTC) + timedelta(days=1)
    assert tag_feature.has_access(_FakeUser(telegram_id=1, tag_feature_expires_at=active))
