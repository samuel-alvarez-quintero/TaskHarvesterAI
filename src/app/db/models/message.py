from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.ai_log import AiLog
    from app.db.models.message_address import MessageAddress
    from app.db.models.message_attachment import MessageAttachment
    from app.db.models.raw_message import RawMessage
    from app.db.models.task import Task
    from app.db.models.task_group import TaskGroup


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    source: Mapped[str] = mapped_column(
        String, default="email", server_default=text("'email'"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    mailbox: Mapped[str] = mapped_column(
        String, default="INBOX", server_default=text("'INBOX'"), nullable=False
    )
    imap_uid: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String)
    message_id: Mapped[str | None] = mapped_column(String, unique=True)
    thread_key: Mapped[str | None] = mapped_column(String)

    in_reply_to: Mapped[str | None] = mapped_column(String)
    references_header: Mapped[str | None] = mapped_column(Text)

    from_name: Mapped[str | None] = mapped_column(String)
    from_email: Mapped[str | None] = mapped_column(String)
    subject: Mapped[str | None] = mapped_column(String)

    received_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    message_date: Mapped[datetime | None] = mapped_column(DateTime)
    imap_internal_date: Mapped[datetime | None] = mapped_column(DateTime)

    importance: Mapped[str | None] = mapped_column(String)
    flags_json: Mapped[str | None] = mapped_column(Text)
    has_attachments: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    attachment_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    size_bytes: Mapped[int | None] = mapped_column(Integer)

    body_text_raw: Mapped[str | None] = mapped_column(Text)
    body_html_raw: Mapped[str | None] = mapped_column(Text)
    body_text_clean: Mapped[str | None] = mapped_column(Text)
    body_hash: Mapped[str | None] = mapped_column(String)
    clean_body_hash: Mapped[str | None] = mapped_column(String)
    headers_json: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String, default="pending", server_default=text("'pending'"), nullable=False
    )
    error_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    raw_message: Mapped["RawMessage | None"] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=False,
    )
    addresses: Mapped[list["MessageAddress"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )
    ai_logs: Mapped[list["AiLog"]] = relationship(back_populates="message")
    source_task_groups: Mapped[list["TaskGroup"]] = relationship(
        back_populates="source_message"
    )
    source_tasks: Mapped[list["Task"]] = relationship(back_populates="source_message")

    __table_args__ = (
        Index(
            "idx_messages_account_mailbox_uid",
            "account_id",
            "mailbox",
            "imap_uid",
            unique=True,
        ),
        Index("idx_messages_message_id", "message_id", unique=True),
        Index("idx_messages_status_received_on", "status", "received_on"),
        Index("idx_messages_from_email", "from_email"),
        Index("idx_messages_thread_key", "thread_key"),
    )
