from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PromptTemplateVersion(Base):
    __tablename__ = "prompt_template_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_template_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_label: Mapped[str] = mapped_column(String, nullable=False)
    language_hint: Mapped[str] = mapped_column(String, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    template = relationship("PromptTemplate", back_populates="versions")

    __table_args__ = (
        Index(
            "idx_prompt_template_versions_template_id",
            "prompt_template_id",
        ),
    )
