from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import RawMessage
from app.repository.base import BaseRepository


class RawMessageRepository(BaseRepository[RawMessage]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_message_id(self, message_id: int) -> RawMessage | None:
        return (
            self.session.query(RawMessage)
            .filter(RawMessage.message_row_id == message_id)
            .first()
        )

    def create_raw_message(
        self, message_id: int, raw_rfc822: bytes, raw_headers: str
    ) -> RawMessage:
        raw_message = RawMessage(
            message_row_id=message_id,
            raw_rfc822=raw_rfc822,
            raw_headers=raw_headers,
        )
        return self.add(raw_message)
