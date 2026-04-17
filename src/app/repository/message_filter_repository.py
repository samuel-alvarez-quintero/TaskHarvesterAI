from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import MessageFilter
from app.repository.base import BaseRepository


class MessageFilterRepository(BaseRepository[MessageFilter]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_message_id(self, message_id: int) -> list[MessageFilter]:
        return self.list(MessageFilter, MessageFilter.message_row_id == message_id)

    def create_message_filter(
        self,
        message_id: int,
        filter_name: str,
        filter_value: bool,
        confidence: float | None = None,
        reason: str | None = None,
    ) -> MessageFilter:
        filter_entry = MessageFilter(
            message_row_id=message_id,
            filter_name=filter_name,
            filter_value=1 if filter_value else 0,
            confidence=confidence,
            reason=reason,
        )
        return self.add(filter_entry)

    def create_or_update_filter(
        self,
        message_id: int,
        filter_name: str,
        filter_value: bool,
        confidence: float | None = None,
        reason: str | None = None,
    ) -> MessageFilter:
        existing_filter = (
            self.session.query(MessageFilter)
            .filter(
                MessageFilter.message_row_id == message_id,
                MessageFilter.filter_name == filter_name,
            )
            .first()
        )
        if existing_filter:
            existing_filter.filter_value = 1 if filter_value else 0
            existing_filter.confidence = confidence
            existing_filter.reason = reason
            return existing_filter

        return self.create_message_filter(
            message_id=message_id,
            filter_name=filter_name,
            filter_value=filter_value,
            confidence=confidence,
            reason=reason,
        )
