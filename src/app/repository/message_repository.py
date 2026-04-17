from __future__ import annotations

from datetime import datetime
from typing import Any
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.db.models import Message
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
    ) -> list[dict[str, Any]]:
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

        return [self._to_dict(message) for message in query.all()]

    def update_message_status(
        self,
        message_id: int,
        status: str,
        processed_at: datetime | None = None,
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
            message.updated_at = datetime.now().astimezone()

    def get_message_by_message_id_or_uid(
        self,
        message_id: str | None,
        account_id: str,
        mailbox: str,
        imap_uid: str,
    ) -> Message | None:
        return self.check_duplicate_message(
            message_id=message_id,
            account_id=account_id,
            mailbox=mailbox,
            imap_uid=imap_uid,
        )

    def get_messages_for_filtering(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        query = (
            self.session.query(Message)
            .filter(Message.status.in_(["pending", "processing", "error"]))
            .order_by(Message.received_on.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return [self._to_dict(message) for message in query.all()]

    def create_message(self, **kwargs: Any) -> dict[str, Any]:
        message = Message(**kwargs)
        created = self.add(message)
        self.session.flush()
        return self._to_dict(created)

    def _to_dict(self, message: Message) -> dict[str, Any]:
        return {
            "id": message.id,
            "source": message.source,
            "account_id": message.account_id,
            "mailbox": message.mailbox,
            "external_id": message.external_id,
            "message_id": message.message_id,
            "thread_key": message.thread_key,
            "in_reply_to": message.in_reply_to,
            "references_header": message.references_header,
            "from_name": message.from_name,
            "from_email": message.from_email,
            "subject": message.subject,
            "received_on": message.received_on,
            "message_date": message.message_date,
            "imap_internal_date": message.imap_internal_date,
            "importance": message.importance,
            "flags_json": message.flags_json,
            "has_attachments": message.has_attachments,
            "attachment_count": message.attachment_count,
            "size_bytes": message.size_bytes,
            "body_text_raw": message.body_text_raw,
            "body_html_raw": message.body_html_raw,
            "body_text_clean": message.body_text_clean,
            "headers_json": message.headers_json,
            "status": message.status,
            "processed_at": message.processed_at,
            "last_attempt_at": message.last_attempt_at,
            "error_count": message.error_count,
            "last_error": message.last_error,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
        }

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

    def get_messages_by_status(self) -> list[tuple[str, int]]:
        from sqlalchemy import func

        result = (
            self.session.query(Message.status, func.count(Message.id))
            .group_by(Message.status)
            .order_by(Message.status)
            .all()
        )
        return [(status, count) for status, count in result]
