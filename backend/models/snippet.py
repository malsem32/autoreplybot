from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class Snippet(TimestampMixin, Base):
    """Quick phrase: the owner types `!shortcut` in any chat and the worker
    replaces that message with the saved text (workers/snippets.py)."""

    __tablename__ = "snippets"
    __table_args__ = (UniqueConstraint("account_id", "shortcut"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id"), index=True)
    shortcut: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    photo_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
