from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import LlmProviderSetting
from app.repository.base import BaseRepository


class LlmProviderSettingRepository(BaseRepository[LlmProviderSetting]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_active_for_mailbox(self, mailbox_id: int) -> LlmProviderSetting | None:
        return (
            self.session.query(LlmProviderSetting)
            .filter(
                LlmProviderSetting.mailbox_id == mailbox_id,
                LlmProviderSetting.is_active == 1,
            )
            .order_by(LlmProviderSetting.id.asc())
            .first()
        )

    def create_or_update(
        self,
        mailbox_id: int,
        provider_name: str,
        base_url: str,
        model_name: str,
        api_key_secret_id: int | None,
        request_timeout_seconds: int,
        options_json: str | None = None,
        is_active: bool = True,
    ) -> LlmProviderSetting:
        record = self.get_active_for_mailbox(mailbox_id)
        if record is None:
            record = LlmProviderSetting(
                mailbox_id=mailbox_id,
                provider_name=provider_name,
                base_url=base_url,
                model_name=model_name,
                api_key_secret_id=api_key_secret_id,
                request_timeout_seconds=request_timeout_seconds,
                options_json=options_json,
                is_active=1 if is_active else 0,
            )
            self.add(record)
            self.session.flush()
            return record

        record.provider_name = provider_name
        record.base_url = base_url
        record.model_name = model_name
        record.api_key_secret_id = api_key_secret_id
        record.request_timeout_seconds = request_timeout_seconds
        record.options_json = options_json
        record.is_active = 1 if is_active else 0
        record.updated_at = datetime.now().astimezone()
        return record
