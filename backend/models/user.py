from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.telegram_account import TelegramAccount


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    # Set on a successful Stars payment; the Pro subscription (see
    # backend/services/pro.py) is active while this is in the future.
    # Admins (ADMIN_TELEGRAM_IDS) have Pro regardless of this field.
    pro_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Referral program (backend/services/referrals.py): who invited this
    # user, whether the one-time bonus for their first Pro payment was
    # already granted, and bonus days this user earned by inviting others.
    referred_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    referral_rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_days_earned: Mapped[int] = mapped_column(Integer, default=0)

    accounts: Mapped[list["TelegramAccount"]] = relationship(back_populates="user")
