from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import MessageAttachment
from app.repository.base import BaseRepository


class MessageAttachmentRepository(BaseRepository[MessageAttachment]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_message_id(self, message_id: int) -> list[MessageAttachment]:
        return self.list(
            MessageAttachment, MessageAttachment.message_row_id == message_id
        )

    def create_message_attachment(
        self,
        message_id: int,
        part_index: int | None,
        content_id: str | None,
        filename: str | None,
        filename_normalized: str | None,
        mime_type: str,
        disposition: str | None,
        is_inline: int,
        size_bytes: int | None,
        extraction_method: str = "none",
        extraction_status: str = "pending",
    ) -> MessageAttachment:
        attachment = MessageAttachment(
            message_row_id=message_id,
            part_index=part_index,
            content_id=content_id,
            filename=filename,
            filename_normalized=filename_normalized,
            mime_type=mime_type,
            disposition=disposition,
            is_inline=is_inline,
            size_bytes=size_bytes,
            extraction_method=extraction_method,
            extraction_status=extraction_status,
        )
        return self.add(attachment)
