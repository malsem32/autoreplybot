from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String
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

    schedule_type: Mapped[str] = mapped_column(String(16), default="recurring")  # recurring | once
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="active")  # active | paused | finished


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("broadcast_campaigns.id"), index=True)

    chat_id: Mapped[int] = mapped_column(BigInteger)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))  # success | error
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
