from __future__ import annotations

from typing import Any
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from app.db.models import Client, Task, TaskGroup
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
            task.completed_at = text("CURRENT_TIMESTAMP")
            task.updated_at = text("CURRENT_TIMESTAMP")
            return True
        return False

    def get_client_by_slug(self, name_slug: str) -> Client | None:
        return self.session.query(Client).filter(Client.name_slug == name_slug).first()

    def get_task_group_by_slug(self, name_slug: str) -> TaskGroup | None:
        return (
            self.session.query(TaskGroup)
            .filter(TaskGroup.name_slug == name_slug)
            .first()
        )

    def create_or_update_client(
        self,
        name: str,
        name_slug: str,
        primary_email: str | None = None,
        primary_phone: str | None = None,
    ) -> Client:
        client = self.get_client_by_slug(name_slug)
        if client:
            client.name = name
            if primary_email:
                client.primary_email = primary_email
            if primary_phone:
                client.primary_phone = primary_phone
            client.updated_at = text("CURRENT_TIMESTAMP")
            return client
        else:
            client = Client(
                name=name,
                name_slug=name_slug,
                primary_email=primary_email,
                primary_phone=primary_phone,
            )
            return self.add(client)

    def create_or_update_task_group(
        self,
        name: str,
        name_slug: str,
        client_id: int | None,
        status: str = "pending",
        requested_on: str | None = None,
        expected_delivery_date: str | None = None,
        priority: str | None = None,
        source_message_id: int | None = None,
    ) -> TaskGroup:
        task_group = self.get_task_group_by_slug(name_slug)
        if task_group:
            task_group.name = name
            task_group.status = status
            task_group.requested_on = requested_on
            task_group.expected_delivery_date = expected_delivery_date
            task_group.priority = priority
            if client_id:
                task_group.client_id = client_id
            task_group.updated_at = text("CURRENT_TIMESTAMP")
            return task_group
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
            return self.add(task_group)

    def create_task(
        self,
        content: str,
        source_message_id: int,
        task_group_id: int | None = None,
        status: str = "pending",
        priority: str | None = None,
        requested_on: str | None = None,
        expected_delivery_date: str | None = None,
        ai_log_id: int | None = None,
        extracted_confidence: float | None = None,
        notes: str | None = None,
    ) -> Task:
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
            existing_task.updated_at = text("CURRENT_TIMESTAMP")
            return existing_task
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
            return self.add(task)

    def get_clients_for_context(self) -> list[dict[str, Any]]:
        clients = self.session.query(Client).filter(Client.status == "active").all()
        result = []
        for client in clients:
            client_data = {
                "name": client.name,
                "name_slug": client.name_slug,
                "status": client.status,
                "emails": [client.primary_email] if client.primary_email else [],
                "phone_numbers": [client.primary_phone] if client.primary_phone else [],
                "notes": client.notes,
                "task_groups": {},
            }
            task_groups = (
                self.session.query(TaskGroup)
                .filter(
                    and_(
                        TaskGroup.client_id == client.id,
                        TaskGroup.status != "completed",
                    )
                )
                .all()
            )
            for tg in task_groups:
                client_data["task_groups"][tg.id] = {
                    "name": tg.name,
                    "name_slug": tg.name_slug,
                    "status": tg.status,
                    "requested_on": tg.requested_on,
                    "expected_delivery_date": tg.expected_delivery_date,
                    "priority": tg.priority,
                    "tasks": [],
                }
                tasks = (
                    self.session.query(Task)
                    .filter(
                        and_(
                            Task.task_group_id == tg.id,
                            Task.status != "completed",
                        )
                    )
                    .all()
                )
                for task in tasks:
                    client_data["task_groups"][tg.id]["tasks"].append(
                        {
                            "content": task.content,
                            "status": task.status,
                            "priority": task.priority,
                        }
                    )
            result.append(client_data)
        return result

    def get_task_status_counts(self) -> list[tuple[str, int]]:
        from sqlalchemy import func

        result = (
            self.session.query(Task.status, func.count(Task.id))
            .group_by(Task.status)
            .order_by(Task.status)
            .all()
        )
        return result

    def get_client_count(self) -> int:
        from sqlalchemy import func

        return self.session.query(func.count(Client.id)).scalar()

    def get_task_group_count(self) -> int:
        from sqlalchemy import func

        return self.session.query(func.count(TaskGroup.id)).scalar()
