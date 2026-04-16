from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.db.database import SessionLocal

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType], AbstractContextManager["BaseRepository[ModelType]"]):
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or SessionLocal()
        self._external_session = session is not None

    def __enter__(self) -> "BaseRepository[ModelType]":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
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

    def list(self, model: type[ModelType], *criteria) -> list[ModelType]:
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
