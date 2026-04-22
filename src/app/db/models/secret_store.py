from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SecretStore(Base):
    __tablename__ = "secret_store"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    secret_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    secret_type: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[str] = mapped_column(
        String, default="v1", server_default=text("'v1'"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_secret_store_secret_type", "secret_type"),
    )
