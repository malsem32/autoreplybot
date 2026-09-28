from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class AccountMember(Base):
    """A helper the owner shared one TelegramAccount with (Pro "Команда").
    Members manage rules, broadcasts and leads of that account; they never
    see the session, can't delete the account or invite others."""

    __tablename__ = "account_members"
    __table_args__ = (UniqueConstraint("account_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeamInvite(Base):
    """Single-use invite link `t.me/<bot>?start=team_<token>`, valid 24h."""

    __tablename__ = "team_invites"

    token: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
