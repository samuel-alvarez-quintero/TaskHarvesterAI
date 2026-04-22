from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import WorkspaceSetting
from app.repository.base import BaseRepository


class WorkspaceSettingRepository(BaseRepository[WorkspaceSetting]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_key(self, setting_key: str) -> WorkspaceSetting | None:
        return (
            self.session.query(WorkspaceSetting)
            .filter(WorkspaceSetting.setting_key == setting_key)
            .first()
        )

    def upsert(self, setting_key: str, setting_value: str) -> WorkspaceSetting:
        setting = self.get_by_key(setting_key)
        if setting is None:
            setting = WorkspaceSetting(
                setting_key=setting_key,
                setting_value=setting_value,
            )
            self.add(setting)
            self.session.flush()
            return setting

        setting.setting_value = setting_value
        setting.updated_at = datetime.now().astimezone()
        return setting
