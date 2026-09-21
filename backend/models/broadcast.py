from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class BroadcastCampaign(TimestampMixin, Base):
    __tablename__ = "broadcast_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)

    title: Mapped[str] = mapped_column(String(255))
    text_template: Mapped[str] = mapped_column(String)
    photo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    # Each entry: numeric chat id as a string, "@username", or a t.me/... link
    # (including invite links) — resolved at send time, see workers/targets.py.
    target_chats: Mapped[list[str]] = mapped_column(JSON, default=list)

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
