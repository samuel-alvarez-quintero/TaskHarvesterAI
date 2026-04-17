from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.task import Task


class AiLog(Base):
    __tablename__ = "ai_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str] = mapped_column(
        String,
        default="extract_tasks",
        server_default=text("'extract_tasks'"),
        nullable=False,
    )
    message_row_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )

    prompt: Mapped[str | None] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)
    request_payload: Mapped[str | None] = mapped_column(Text)
    response_payload: Mapped[str | None] = mapped_column(Text)

    http_status: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        String, default="pending", server_default=text("'pending'"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    message: Mapped["Message"] = relationship(back_populates="ai_logs")
    tasks: Mapped[list["Task"]] = relationship(back_populates="ai_log")

    __table_args__ = (
        Index("idx_ai_log_message_row_id", "message_row_id"),
        Index("idx_ai_log_status", "status"),
        Index("idx_ai_log_provider_model", "provider", "model"),
    )
