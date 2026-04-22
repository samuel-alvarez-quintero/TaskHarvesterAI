from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.mailbox_setting import MailboxSetting


class LlmProviderSetting(Base):
    __tablename__ = "llm_provider_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mailbox_id: Mapped[int] = mapped_column(
        ForeignKey("mailbox_settings.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    api_key_secret_id: Mapped[int | None] = mapped_column(
        ForeignKey("secret_store.id", ondelete="SET NULL")
    )
    request_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=120, server_default=text("120"), nullable=False
    )
    options_json: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    mailbox: Mapped["MailboxSetting"] = relationship(back_populates="llm_provider_settings")

    __table_args__ = (
        Index("idx_llm_provider_settings_mailbox_id", "mailbox_id"),
        Index("idx_llm_provider_settings_active", "is_active"),
    )
