from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.client import Client
    from app.db.models.message import Message
    from app.db.models.task import Task


class TaskGroup(Base):
    __tablename__ = "task_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="pending", server_default=text("'pending'"), nullable=False
    )
    requested_on: Mapped[datetime | None] = mapped_column(DateTime)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    priority: Mapped[str | None] = mapped_column(String)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("client.id", ondelete="SET NULL")
    )
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    client: Mapped["Client | None"] = relationship(back_populates="task_groups")
    source_message: Mapped["Message | None"] = relationship(
        back_populates="source_task_groups"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="task_group")

    __table_args__ = (
        Index("idx_task_groups_client_id", "client_id"),
        Index("idx_task_groups_status", "status"),
        Index("idx_task_groups_priority", "priority"),
        Index("idx_task_groups_source_message_id", "source_message_id"),
    )
