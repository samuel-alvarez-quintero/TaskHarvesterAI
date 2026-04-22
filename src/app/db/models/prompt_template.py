from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.mailbox_setting import MailboxSetting
    from app.db.models.prompt_template_version import PromptTemplateVersion


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mailbox_id: Mapped[int] = mapped_column(
        ForeignKey("mailbox_settings.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(String, nullable=False)
    language_hint: Mapped[str] = mapped_column(
        String, default="English", server_default=text("'English'"), nullable=False
    )
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    json_response_schema: Mapped[str] = mapped_column(Text, nullable=False)
    context_template: Mapped[str] = mapped_column(Text, nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    mailbox: Mapped["MailboxSetting"] = relationship(back_populates="prompt_templates")
    versions: Mapped[list["PromptTemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_prompt_templates_mailbox_operation", "mailbox_id", "operation"),
        Index("idx_prompt_templates_active", "is_active"),
    )
