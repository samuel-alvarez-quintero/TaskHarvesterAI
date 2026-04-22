from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkspaceSetting(Base):
    __tablename__ = "workspace_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setting_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_workspace_settings_key", "setting_key", unique=True),
    )
