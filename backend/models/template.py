from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class MessageTemplate(TimestampMixin, Base):
    """A user's saved message text (Pro), reusable in autoreplies and
    broadcasts. The built-in library lives in backend/services/templates.py."""

    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(String)
