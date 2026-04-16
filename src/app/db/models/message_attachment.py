from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_row_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )

    part_index: Mapped[int | None] = mapped_column(Integer)
    content_id: Mapped[str | None] = mapped_column(String)
    filename: Mapped[str | None] = mapped_column(String)
    filename_normalized: Mapped[str | None] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    disposition: Mapped[str | None] = mapped_column(String)
    is_inline: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    size_bytes: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String)
    storage_path: Mapped[str | None] = mapped_column(String)

    extracted_text: Mapped[str | None] = mapped_column(Text)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str | None] = mapped_column(String)
    extraction_status: Mapped[str] = mapped_column(
        String, default="pending", server_default=text("'pending'"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    message: Mapped["Message"] = relationship(back_populates="attachments")

    __table_args__ = (
        Index("idx_message_attachments_message_row_id", "message_row_id"),
        Index("idx_message_attachments_content_hash", "content_hash"),
        Index("idx_message_attachments_extraction_status", "extraction_status"),
    )
