from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message


class MessageAddress(Base):
    __tablename__ = "message_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_row_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    address_role: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String)
    email_address: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    message: Mapped["Message"] = relationship(back_populates="addresses")

    __table_args__ = (
        Index("idx_message_addresses_message_row_id", "message_row_id"),
        Index("idx_message_addresses_email_address", "email_address"),
        Index("idx_message_addresses_role", "address_role"),
    )
