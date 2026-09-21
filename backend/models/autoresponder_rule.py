from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class AutoresponderRule(TimestampMixin, Base):
    __tablename__ = "autoresponder_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(16), default="all")  # "all" | "keywords"
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    response_text: Mapped[str] = mapped_column(String)
    photo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=3600)
