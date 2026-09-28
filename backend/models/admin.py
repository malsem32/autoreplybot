from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class Payment(TimestampMixin, Base):
    """One successful Stars payment for Pro (bot/handlers/payments.py) —
    feeds revenue in the admin section."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stars: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    charge_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)


class AdminAuditLog(TimestampMixin, Base):
    """Who did what to whom from the admin section (AGENTS.md 4.6: actions
    with consequences for users are always audited)."""

    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(32))  # pro_grant | pro_revoke
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    details: Mapped[str] = mapped_column(String(255), default="")
