from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class BroadcastCampaign(TimestampMixin, Base):
    __tablename__ = "broadcast_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)

    title: Mapped[str] = mapped_column(String(255))
    text_template: Mapped[str] = mapped_column(String)
    # Up to 10 photos under backend/core/uploads.UPLOAD_DIR; 2+ go out as an album.
    photo_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Each entry: numeric chat id as a string, "@username", or a t.me/... link
    # (including invite links) — resolved at send time, see workers/targets.py.
    target_chats: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Pro: invisible mentions of 5 random members of each target chat are
    # appended to the message (workers/broadcaster.py, AGENTS.md 4.13).
    tag_random_users: Mapped[bool] = mapped_column(Boolean, default=False)

    # Send options. protect_content (no forwarding/saving) is Pro-only.
    disable_notification: Mapped[bool] = mapped_column(Boolean, default=False)
    protect_content: Mapped[bool] = mapped_column(Boolean, default=False)
    disable_link_preview: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pro: targets that failed AUTO_DISABLE_AFTER_FAILURES times in a row are
    # moved to `disabled_targets` and skipped until the owner restores them.
    auto_disable_failing: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled_targets: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Pro: the bot sends the owner a delivery report after every run.
    notify_report: Mapped[bool] = mapped_column(Boolean, default=False)
    # Pro: drop the "Отправлено через @bot" signature (AGENTS.md 4.3).
    hide_signature: Mapped[bool] = mapped_column(Boolean, default=False)

    schedule_type: Mapped[str] = mapped_column(String(16), default="recurring")  # recurring | once
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="active")  # active | paused | finished


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("broadcast_campaigns.id"), index=True)

    # The entry of target_chats this attempt was for (per-chat statistics).
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))  # success | error
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)


class FloodWaitEvent(Base):
    """A FloodWait received by a worker — the admin "approaching Telegram
    limits" signal (AGENTS.md 4.6)."""

    __tablename__ = "flood_wait_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)
    seconds: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # broadcast | autoreply | snippet
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
