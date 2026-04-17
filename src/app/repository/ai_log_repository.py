from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import AiLog
from app.repository.base import BaseRepository


class AiLogRepository(BaseRepository[AiLog]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_id(self, ai_log_id: int) -> AiLog | None:
        return self.get(AiLog, ai_log_id)

    def create_ai_log(
        self,
        provider: str,
        model: str,
        operation: str,
        message_row_id: int,
        prompt: str | None = None,
        response: str | None = None,
        status: str = "pending",
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> AiLog:
        ai_log = AiLog(
            provider=provider,
            model=model,
            operation=operation,
            message_row_id=message_row_id,
            prompt=prompt,
            response=response,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        return self.add(ai_log)

    def update_ai_log(
        self,
        ai_log_id: int,
        http_status: str | None = None,
        status: str | None = None,
        response: str | None = None,
        response_payload: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        ai_log = self.get_by_id(ai_log_id)
        if ai_log:
            if http_status is not None:
                ai_log.http_status = http_status
            if status is not None:
                ai_log.status = status
            if response is not None:
                ai_log.response = response
            if response_payload is not None:
                ai_log.response_payload = response_payload
            if error_message is not None:
                ai_log.error_message = error_message
            if duration_ms is not None:
                ai_log.duration_ms = duration_ms
            ai_log.updated_at = text("CURRENT_TIMESTAMP")

    def get_ai_logs_by_message(self, message_id: int) -> list[AiLog]:
        return self.list(AiLog, AiLog.message_row_id == message_id)

    def get_ai_logs_by_provider_model(self, provider: str, model: str) -> list[AiLog]:
        from sqlalchemy import and_

        return self.list(AiLog, and_(AiLog.provider == provider, AiLog.model == model))

    def get_ai_logs_by_status(self, status: str) -> list[AiLog]:
        return self.list(AiLog, AiLog.status == status)
