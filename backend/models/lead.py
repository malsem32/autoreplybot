from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

LEAD_STATUSES = ("new", "in_work", "done")


class Lead(Base):
    """One person who wrote to the account in private messages (Pro
    "Обращения"): a tiny CRM so inquiries handled by the autopilot don't get
    lost. Collected only while the owner has Pro."""

    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("account_id", "peer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)
    peer_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(256), default="")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_text: Mapped[str] = mapped_column(String(500), default="")
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="new")  # new | in_work | done
    note: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
