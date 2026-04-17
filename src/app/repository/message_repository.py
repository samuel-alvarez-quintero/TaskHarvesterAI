from __future__ import annotations

from typing import Any
from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.db.models import (
    Message,
    MessageAddress,
    MessageAttachment,
    MessageFilter,
    RawMessage,
)
from app.repository.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_id(self, message_id: int) -> Message | None:
        return self.get(Message, message_id)

    def get_unprocessed_messages(
        self,
        limit: int | None = None,
        status_filters: list[str] | None = None,
        retry_processing_after_minutes: int | None = None,
    ) -> list[Message]:
        if status_filters is None:
            status_filters = ["pending"]

        query = self.session.query(Message).filter(Message.status.in_(status_filters))

        if retry_processing_after_minutes is not None:
            from datetime import datetime, timedelta

            cutoff = datetime.now().astimezone() - timedelta(
                minutes=retry_processing_after_minutes
            )
            query = query.filter(
                or_(
                    Message.status != "processing",
                    Message.last_attempt_at <= cutoff,
                )
            )
        else:
            query = query.filter(Message.status != "processing")

        query = query.order_by(Message.received_on.desc())

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def update_message_status(
        self,
        message_id: int,
        status: str,
        processed_at: str | None = None,
        last_error: str | None = None,
        error_count: int | None = None,
    ) -> None:
        message = self.get_by_id(message_id)
        if message:
            message.status = status
            if processed_at:
                message.processed_at = processed_at
            if last_error is not None:
                message.last_error = last_error
            if error_count is not None:
                message.error_count = error_count
            message.updated_at = text("CURRENT_TIMESTAMP")

    def add_raw_message(
        self, message_id: int, raw_rfc822: bytes, raw_headers: str
    ) -> None:
        raw_message = RawMessage(
            message_row_id=message_id,
            raw_rfc822=raw_rfc822,
            raw_headers=raw_headers,
        )
        self.add(raw_message)

    def add_message_address(
        self,
        message_id: int,
        address_role: str,
        display_name: str | None,
        email_address: str,
    ) -> None:
        address = MessageAddress(
            message_row_id=message_id,
            address_role=address_role,
            display_name=display_name,
            email_address=email_address,
        )
        self.add(address)

    def add_message_attachment(
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
    ) -> None:
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
        self.add(attachment)

    def add_message_filter(
        self,
        message_id: int,
        filter_name: str,
        filter_value: bool,
        confidence: float | None = None,
        reason: str | None = None,
    ) -> None:
        filter_entry = MessageFilter(
            message_row_id=message_id,
            filter_name=filter_name,
            filter_value=1 if filter_value else 0,
            confidence=confidence,
            reason=reason,
        )
        self.add(filter_entry)

    def get_message_filters(self, message_id: int) -> list[MessageFilter]:
        return self.list(MessageFilter, MessageFilter.message_row_id == message_id)

    def get_messages_by_status(self, status: str) -> list[tuple[str, int]]:
        from sqlalchemy import func

        result = (
            self.session.query(Message.status, func.count(Message.id))
            .group_by(Message.status)
            .order_by(Message.status)
            .all()
        )
        return result

    def check_duplicate_message(
        self, message_id: str | None, account_id: str, mailbox: str, imap_uid: str
    ) -> Message | None:
        if message_id:
            return (
                self.session.query(Message)
                .filter(
                    or_(
                        Message.message_id == message_id,
                        and_(
                            Message.account_id == account_id,
                            Message.mailbox == mailbox,
                            Message.imap_uid == imap_uid,
                        ),
                    )
                )
                .first()
            )
        else:
            return (
                self.session.query(Message)
                .filter(
                    and_(
                        Message.account_id == account_id,
                        Message.mailbox == mailbox,
                        Message.imap_uid == imap_uid,
                    )
                )
                .first()
            )

    def create_message(self, **kwargs: Any) -> Message:
        message = Message(**kwargs)
        return self.add(message)
