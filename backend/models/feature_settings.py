from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ProSetting(Base):
    """Singleton row (id=1) holding the admin-editable price/duration of the
    Pro subscription, paid for with Telegram Stars."""

    __tablename__ = "pro_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    stars_price: Mapped[int] = mapped_column(Integer, default=50)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    # Granted to both the inviter and the invitee on the invitee's first
    # Pro payment (backend/services/referrals.py).
    referral_bonus_days: Mapped[int] = mapped_column(Integer, default=7)
