from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.telegram_account import TelegramAccount


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    # Set on a successful Stars payment; the "tag random users" broadcast
    # feature is unlocked while this is in the future. Admins (see
    # ADMIN_TELEGRAM_IDS) get the feature regardless of this field.
    tag_feature_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    accounts: Mapped[list["TelegramAccount"]] = relationship(back_populates="user")
