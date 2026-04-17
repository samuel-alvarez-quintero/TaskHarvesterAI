from __future__ import annotations
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Generic, Type, TypeVar
from sqlalchemy.orm import Session

from app.db.database import session_scope

"""Base repository for handling common database operations."""

ModelType = TypeVar("ModelType")


class BaseRepository(
    Generic[ModelType], AbstractContextManager["BaseRepository[ModelType]"]
):
    def __init__(self, session: Session | None = None) -> None:
        with session_scope() as s:
            self.session = session or s
            self._external_session = self.session is not None

    def __enter__(self) -> "BaseRepository[ModelType]":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type:
            self.rollback()
        elif not self._external_session:
            self.commit()
        self.close()

    def add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        return entity

    def get(self, model: type[ModelType], entity_id: int) -> ModelType | None:
        return self.session.get(model, entity_id)

    def list(self, model: type[ModelType], *criteria: Any) -> list[ModelType]:
        query = self.session.query(model)
        if criteria:
            query = query.filter(*criteria)
        return query.all()

    def delete(self, entity: ModelType) -> None:
        self.session.delete(entity)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        if not self._external_session:
            self.session.close()
