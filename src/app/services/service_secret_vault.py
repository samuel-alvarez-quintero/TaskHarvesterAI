from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


@dataclass(frozen=True)
class DecryptedSecret:
    value: str
    key_version: str


class ServiceSecretVault:
    def __init__(self, key_version: str = "v1") -> None:
        self.key_version = key_version
        self._fernet = Fernet(self._build_fernet_key())

    def _build_fernet_key(self) -> bytes:
        raw_key = settings.app_secret_key
        if not raw_key:
            if settings.app_env.lower() != "development":
                raise ValueError(
                    "APP_SECRET_KEY must be set to use encrypted secret storage."
                )
            raw_key = "dev-only-insecure-key"
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_value: str, key_version: str) -> DecryptedSecret:
        if key_version != self.key_version:
            raise ValueError(
                f"Unsupported key_version '{key_version}'. Expected '{self.key_version}'."
            )
        try:
            decrypted = self._fernet.decrypt(encrypted_value.encode("utf-8")).decode(
                "utf-8"
            )
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt secret with current APP_SECRET_KEY.") from exc
        return DecryptedSecret(value=decrypted, key_version=key_version)
