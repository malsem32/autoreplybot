from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class AutoresponderRule(TimestampMixin, Base):
    __tablename__ = "autoresponder_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(16), default="all")  # "all" | "keywords"
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    # How keywords match (backend/services/rule_match.py): contains | word | exact.
    match_mode: Mapped[str] = mapped_column(String(16), default="contains")
    # Where the rule answers: private | groups (Pro: mentions/replies to the
    # owner in groups) | all.
    scope: Mapped[str] = mapped_column(String(16), default="private")
    response_text: Mapped[str] = mapped_column(String)
    # Up to 10 photos under backend/core/uploads.UPLOAD_DIR; 2+ go out as an album.
    photo_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=3600)

    # --- Pro options (AGENTS.md 4.13), enforced again by workers/responder.py ---
    # Working hours: reply only on `schedule_days` (0 = Monday) between
    # `schedule_start` and `schedule_end` ("HH:MM", may wrap past midnight)
    # in the owner's `timezone` (IANA name from the Mini App).
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_days: Mapped[list[int]] = mapped_column(JSON, default=lambda: list(range(7)))
    schedule_start: Mapped[str] = mapped_column(String(5), default="19:00")
    schedule_end: Mapped[str] = mapped_column(String(5), default="09:00")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    # Reply only to people writing for the first time.
    new_contacts_only: Mapped[bool] = mapped_column(Boolean, default=False)
    # Stay silent if the owner themselves wrote in this chat within N minutes
    # (0 = off): the autopilot doesn't butt into a live conversation.
    skip_if_owner_active_minutes: Mapped[int] = mapped_column(Integer, default=0)
    # "Typing…" for N seconds before the reply (0 = off).
    typing_delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    # Ping the owner in the bot chat whenever this rule answers someone.
    notify_owner: Mapped[bool] = mapped_column(Boolean, default=False)


class AutoresponderEvent(Base):
    """One row per autoreply actually sent — feeds per-rule counters in the
    Mini App and the admin "autoresponder triggers" stat (AGENTS.md 4.6).
    Stores no message content and no peer identity."""

    __tablename__ = "autoresponder_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("autoresponder_rules.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
