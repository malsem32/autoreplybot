from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class TagFeatureSetting(Base):
    """Singleton row (id=1) holding the admin-editable price/duration of the
    "tag random users" broadcast feature, paid for with Telegram Stars."""

    __tablename__ = "tag_feature_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    stars_price: Mapped[int] = mapped_column(Integer, default=50)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
