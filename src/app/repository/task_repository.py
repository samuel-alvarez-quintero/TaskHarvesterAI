from __future__ import annotations

from datetime import datetime
from typing import Any
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Task, TaskGroup
from app.repository.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_task_by_id(self, task_id: int) -> Task | None:
        return self.get(Task, task_id)

    def list_tasks(
        self,
        status: str | None = None,
        limit: int | None = None,
        client_id: int | None = None,
        task_group_id: int | None = None,
    ) -> list[Task]:
        query = self.session.query(Task)

        if status and status != "all":
            query = query.filter(Task.status == status)

        if client_id:
            query = query.join(TaskGroup).filter(TaskGroup.client_id == client_id)

        if task_group_id:
            query = query.filter(Task.task_group_id == task_group_id)

        query = query.order_by(Task.created_at.desc(), Task.id.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def complete_task(self, task_id: int) -> bool:
        task = self.get_task_by_id(task_id)
        if task:
            task.status = "completed"
            task.completed_at = datetime.now().astimezone()
            task.updated_at = datetime.now().astimezone()
            self.session.flush()
            return True
        return False

    def get_tasks_by_task_group(self, task_group_id: int) -> list[dict[str, Any]]:
        tasks = (
            self.session.query(Task).filter(Task.task_group_id == task_group_id).all()
        )
        return [self._to_dict(task) for task in tasks]

    def get_task_status_counts(self) -> list[tuple[str, int]]:
        from sqlalchemy import func

        result = (
            self.session.query(Task.status, func.count(Task.id))
            .group_by(Task.status)
            .order_by(Task.status)
            .all()
        )
        return [(status, count) for status, count in result]

    def create_task(
        self,
        content: str,
        source_message_id: int,
        task_group_id: int | None = None,
        status: str = "pending",
        priority: str | None = None,
        requested_on: datetime | None = None,
        expected_delivery_date: datetime | None = None,
        ai_log_id: int | None = None,
        extracted_confidence: float | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        # Check for existing task
        query = self.session.query(Task).filter(
            and_(
                Task.source_message_id == source_message_id,
                Task.content == content,
                Task.task_group_id == task_group_id,
            )
        )
        existing_task = query.first()
        if existing_task:
            existing_task.status = status
            existing_task.priority = priority
            existing_task.requested_on = requested_on
            existing_task.expected_delivery_date = expected_delivery_date
            existing_task.ai_log_id = ai_log_id
            existing_task.updated_at = datetime.now().astimezone()
            return self._to_dict(existing_task)
        else:
            task = Task(
                content=content,
                status=status,
                priority=priority,
                requested_on=requested_on,
                expected_delivery_date=expected_delivery_date,
                task_group_id=task_group_id,
                source_message_id=source_message_id,
                ai_log_id=ai_log_id,
                extracted_confidence=extracted_confidence,
                notes=notes,
            )
            created = self.add(task)
            self.session.flush()
            return self._to_dict(created)

    def _to_dict(self, task: Task) -> dict[str, Any]:
        return {
            "id": task.id,
            "content": task.content,
            "status": task.status,
            "priority": task.priority,
            "requested_on": task.requested_on,
            "expected_delivery_date": task.expected_delivery_date,
            "completed_at": task.completed_at,
            "task_group_id": task.task_group_id,
            "source_message_id": task.source_message_id,
            "ai_log_id": task.ai_log_id,
            "extracted_confidence": task.extracted_confidence,
            "notes": task.notes,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
