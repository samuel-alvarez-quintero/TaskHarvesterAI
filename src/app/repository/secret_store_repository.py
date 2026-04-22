from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import SecretStore
from app.repository.base import BaseRepository


class SecretStoreRepository(BaseRepository[SecretStore]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_name(self, secret_name: str) -> SecretStore | None:
        return (
            self.session.query(SecretStore)
            .filter(SecretStore.secret_name == secret_name)
            .first()
        )

    def get_by_id(self, secret_id: int) -> SecretStore | None:
        return self.get(SecretStore, secret_id)

    def upsert(
        self,
        secret_name: str,
        secret_type: str,
        encrypted_value: str,
        key_version: str = "v1",
    ) -> SecretStore:
        secret = self.get_by_name(secret_name)
        if secret is None:
            secret = SecretStore(
                secret_name=secret_name,
                secret_type=secret_type,
                encrypted_value=encrypted_value,
                key_version=key_version,
            )
            self.add(secret)
            self.session.flush()
            return secret

        secret.secret_type = secret_type
        secret.encrypted_value = encrypted_value
        secret.key_version = key_version
        secret.updated_at = datetime.now().astimezone()
        return secret
