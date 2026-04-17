from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message


class MessageFilter(Base):
    __tablename__ = "message_filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_row_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    filter_name: Mapped[str] = mapped_column(String, nullable=False)
    filter_value: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    message: Mapped["Message"] = relationship(back_populates="filters")

    __table_args__ = (
        Index("idx_message_filters_message_row_id", "message_row_id"),
        Index("idx_message_filters_filter_name", "filter_name"),
        Index(
            "idx_message_filters_message_filter",
            "message_row_id",
            "filter_name",
            unique=True,
        ),
    )
