from sqlalchemy import BigInteger, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class SupportMessage(TimestampMixin, Base):
    """Links a support request delivered to an admin's chat with the bot to
    the user who sent it, so the admin's reply (Reply to that message) is
    routed back (bot/handlers/support.py). Stores no message text."""

    __tablename__ = "support_messages"
    __table_args__ = (UniqueConstraint("admin_chat_id", "admin_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_chat_id: Mapped[int] = mapped_column(BigInteger)
    admin_message_id: Mapped[int] = mapped_column(Integer)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
