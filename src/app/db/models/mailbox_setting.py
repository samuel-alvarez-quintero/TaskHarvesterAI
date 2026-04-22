from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.llm_provider_setting import LlmProviderSetting
    from app.db.models.prompt_template import PromptTemplate


class MailboxSetting(Base):
    __tablename__ = "mailbox_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    mailbox_name: Mapped[str] = mapped_column(
        String, default="INBOX", server_default=text("'INBOX'"), nullable=False
    )
    imap_host: Mapped[str] = mapped_column(String, nullable=False)
    imap_port: Mapped[int] = mapped_column(
        Integer, default=993, server_default=text("993"), nullable=False
    )
    imap_username: Mapped[str] = mapped_column(String, nullable=False)
    imap_password_secret_id: Mapped[int | None] = mapped_column(
        ForeignKey("secret_store.id", ondelete="SET NULL")
    )
    polling_interval_seconds: Mapped[int] = mapped_column(
        Integer, default=300, server_default=text("300"), nullable=False
    )
    is_active: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    llm_provider_settings: Mapped[list["LlmProviderSetting"]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )
    prompt_templates: Mapped[list["PromptTemplate"]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_mailbox_settings_account_mailbox", "account_id", "mailbox_name"),
        Index("idx_mailbox_settings_active", "is_active"),
    )
