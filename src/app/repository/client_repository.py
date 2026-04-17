from __future__ import annotations

from datetime import datetime
from typing import Any
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Client, TaskGroup
from app.repository.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_client_by_slug(self, name_slug: str) -> Client | None:
        return self.session.query(Client).filter(Client.name_slug == name_slug).first()

    def create_or_update_client(
        self,
        name: str,
        name_slug: str,
        primary_email: str | None = None,
        primary_phone: str | None = None,
    ) -> dict[str, Any]:
        client = self.get_client_by_slug(name_slug)
        if client:
            client.name = name
            if primary_email:
                client.primary_email = primary_email
            if primary_phone:
                client.primary_phone = primary_phone
            client.updated_at = datetime.now().astimezone()
            return self._to_dict(client)
        else:
            client = Client(
                name=name,
                name_slug=name_slug,
                primary_email=primary_email,
                primary_phone=primary_phone,
            )
            created = self.add(client)
            self.session.flush()
            return self._to_dict(created)

    def get_all_clients(self) -> list[dict[str, Any]]:
        clients = self.session.query(Client).all()
        return [self._to_dict(client) for client in clients]

    def get_client_count(self) -> int:
        return self.session.query(Client).count()

    def get_clients_for_context(self) -> list[dict[str, Any]]:
        clients = self.session.query(Client).filter(Client.status == "active").all()
        result: list[dict[str, Any]] = []
        for client in clients:
            client_data: dict[str, Any] = {
                "id": client.id,
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
            result.append(client_data)
        return result

    def _to_dict(self, client: Client) -> dict[str, Any]:
        return {
            "id": client.id,
            "name": client.name,
            "name_slug": client.name_slug,
            "status": client.status,
            "primary_email": client.primary_email,
            "primary_phone": client.primary_phone,
            "notes": client.notes,
            "created_at": client.created_at,
            "updated_at": client.updated_at,
        }
