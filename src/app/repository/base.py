from __future__ import annotations
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Generic, Self, Type, TypeVar
from contextlib import _GeneratorContextManager
from sqlalchemy.orm import Session

from app.db.database import session_scope

"""Base repository for handling common database operations."""

ModelType = TypeVar("ModelType")


class BaseRepository(
    Generic[ModelType], AbstractContextManager["BaseRepository[ModelType]"]
):
    def __init__(self, session: Session | None = None) -> None:
        self._provided_session = session
        self.session: Session
        self._session_context: _GeneratorContextManager[Session, None, None] | None = None

    def __enter__(self: Self) -> Self:
        if self._provided_session:
            self.session = self._provided_session
        else:
            self._session_context = session_scope()
            self.session = self._session_context.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._provided_session:
            # If external session, don't commit/close
            pass
        else:
            # Use the context manager to commit/close
            if self._session_context:
                self._session_context.__exit__(exc_type, exc_value, traceback)

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
