from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.ai_log import AiLog
    from app.db.models.message import Message
    from app.db.models.task_group import TaskGroup


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="pending", server_default=text("'pending'"), nullable=False
    )
    priority: Mapped[str | None] = mapped_column(String)
    requested_on: Mapped[datetime | None] = mapped_column(DateTime)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    task_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("task_groups.id", ondelete="SET NULL")
    )
    source_message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_log.id", ondelete="SET NULL")
    )
    extracted_confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    task_group: Mapped["TaskGroup | None"] = relationship(back_populates="tasks")
    source_message: Mapped["Message"] = relationship(back_populates="source_tasks")
    ai_log: Mapped["AiLog | None"] = relationship(back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_task_group_id", "task_group_id"),
        Index("idx_tasks_source_message_id", "source_message_id"),
        Index("idx_tasks_ai_log_id", "ai_log_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_expected_delivery_date", "expected_delivery_date"),
    )
