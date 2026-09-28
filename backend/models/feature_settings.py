from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ProSetting(Base):
    """Singleton row (id=1) holding the admin-editable Pro plans, paid for
    with Telegram Stars (see backend/services/pro.py:plans)."""

    __tablename__ = "pro_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Base plan ("month").
    stars_price: Mapped[int] = mapped_column(Integer, default=50)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    # Longer plans at a discount; 0 hides the plan.
    quarter_stars_price: Mapped[int] = mapped_column(Integer, default=130)
    year_stars_price: Mapped[int] = mapped_column(Integer, default=450)
    # One-time free trial length; 0 disables the trial.
    trial_days: Mapped[int] = mapped_column(Integer, default=3)
    # Granted to both the inviter and the invitee on the invitee's first
    # Pro payment (backend/services/referrals.py).
    referral_bonus_days: Mapped[int] = mapped_column(Integer, default=7)
