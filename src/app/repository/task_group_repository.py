from __future__ import annotations

from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session

from app.db.models import TaskGroup
from app.repository.base import BaseRepository


class TaskGroupRepository(BaseRepository[TaskGroup]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_task_group_by_slug(self, name_slug: str) -> TaskGroup | None:
        return (
            self.session.query(TaskGroup)
            .filter(TaskGroup.name_slug == name_slug)
            .first()
        )

    def create_or_update_task_group(
        self,
        name: str,
        name_slug: str,
        client_id: int | None,
        status: str = "pending",
        requested_on: datetime | None = None,
        expected_delivery_date: datetime | None = None,
        priority: str | None = None,
        source_message_id: int | None = None,
    ) -> dict[str, Any]:
        task_group = self.get_task_group_by_slug(name_slug)
        if task_group:
            task_group.name = name
            task_group.status = status
            task_group.requested_on = requested_on
            task_group.expected_delivery_date = expected_delivery_date
            task_group.priority = priority
            if client_id:
                task_group.client_id = client_id
            task_group.updated_at = datetime.now().astimezone()
            return self._to_dict(task_group)
        else:
            task_group = TaskGroup(
                name=name,
                name_slug=name_slug,
                status=status,
                requested_on=requested_on,
                expected_delivery_date=expected_delivery_date,
                priority=priority,
                client_id=client_id,
                source_message_id=source_message_id,
            )
            created = self.add(task_group)
            self.session.flush()
            return self._to_dict(created)

    def get_task_groups_by_client(self, client_id: int) -> list[dict[str, Any]]:
        task_groups = (
            self.session.query(TaskGroup).filter(TaskGroup.client_id == client_id).all()
        )
        return [self._to_dict(task_group) for task_group in task_groups]

    def get_task_group_count(self) -> int:
        return self.session.query(TaskGroup).count()

    def _to_dict(self, task_group: TaskGroup) -> dict[str, Any]:
        return {
            "id": task_group.id,
            "name": task_group.name,
            "name_slug": task_group.name_slug,
            "status": task_group.status,
            "requested_on": task_group.requested_on,
            "expected_delivery_date": task_group.expected_delivery_date,
            "priority": task_group.priority,
            "client_id": task_group.client_id,
            "source_message_id": task_group.source_message_id,
            "created_at": task_group.created_at,
            "updated_at": task_group.updated_at,
        }
