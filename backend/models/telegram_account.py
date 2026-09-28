from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.user import User


class TelegramAccount(TimestampMixin, Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    phone: Mapped[str] = mapped_column(String(32))
    encrypted_session: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Vacation mode (backend/services/away.py): while away_until is in the
    # future, private messages get away_text instead of the rules.
    away_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    away_text: Mapped[str] = mapped_column(Text, default="")
    away_timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")

    # AI replies (Pro): what the assistant knows about the business and how
    # it talks. Used by rules with ai_reply=True (backend/services/ai.py).
    ai_knowledge: Mapped[str] = mapped_column(Text, default="")
    ai_tone: Mapped[str] = mapped_column(String(16), default="friendly")

    user: Mapped["User"] = relationship(back_populates="accounts")
