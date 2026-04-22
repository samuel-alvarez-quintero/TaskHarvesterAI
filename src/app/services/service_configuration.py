from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.db.database import session_scope
from app.repository import (
    LlmProviderSettingRepository,
    MailboxSettingRepository,
    SecretStoreRepository,
    WorkspaceSettingRepository,
)
from app.services.service_secret_vault import ServiceSecretVault


@dataclass(frozen=True)
class MailboxRuntimeConfig:
    account_id: str
    mailbox_name: str
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    polling_interval_seconds: int
    mailbox_id: int | None = None


@dataclass(frozen=True)
class LlmRuntimeConfig:
    provider_name: str
    base_url: str
    model_name: str
    api_key: str | None
    request_timeout_seconds: int
    mailbox_id: int | None = None


class ServiceConfiguration:
    def __init__(self) -> None:
        self._vault = ServiceSecretVault()

    def get_workspace_setting(self, key: str) -> str | None:
        with session_scope() as session:
            with WorkspaceSettingRepository(session) as repo:
                setting = repo.get_by_key(key)
                return setting.setting_value if setting else None

    def set_workspace_setting(self, key: str, value: str) -> None:
        with session_scope() as session:
            with WorkspaceSettingRepository(session) as repo:
                repo.upsert(setting_key=key, setting_value=value)

    def get_mailbox_runtime_config(
        self, account_id: str | None = None, mailbox_name: str | None = None
    ) -> MailboxRuntimeConfig:
        with session_scope() as session:
            with MailboxSettingRepository(session) as mailbox_repo:
                mailbox = None
                if account_id and mailbox_name:
                    mailbox = mailbox_repo.get_by_account_and_mailbox(account_id, mailbox_name)
                if mailbox is None:
                    mailbox = mailbox_repo.get_active()

                if mailbox is None or mailbox.imap_password_secret_id is None:
                    return MailboxRuntimeConfig(
                        account_id=settings.imap_user or "",
                        mailbox_name=settings.imap_mailbox,
                        imap_host=settings.imap_host or "",
                        imap_port=settings.imap_port,
                        imap_username=settings.imap_user or "",
                        imap_password=settings.imap_pass or "",
                        polling_interval_seconds=300,
                        mailbox_id=None,
                    )

            with SecretStoreRepository(session) as secret_repo:
                assert mailbox is not None
                secret = secret_repo.get_by_id(mailbox.imap_password_secret_id)
                if secret is None:
                    fallback_password = settings.imap_pass or ""
                else:
                    fallback_password = self._vault.decrypt(
                        secret.encrypted_value, secret.key_version
                    ).value

                return MailboxRuntimeConfig(
                    account_id=mailbox.account_id,
                    mailbox_name=mailbox.mailbox_name,
                    imap_host=mailbox.imap_host,
                    imap_port=mailbox.imap_port,
                    imap_username=mailbox.imap_username,
                    imap_password=fallback_password,
                    polling_interval_seconds=mailbox.polling_interval_seconds,
                    mailbox_id=mailbox.id,
                )

    def get_llm_runtime_config(
        self, account_id: str | None = None, mailbox_name: str | None = None
    ) -> LlmRuntimeConfig:
        mailbox_cfg = self.get_mailbox_runtime_config(
            account_id=account_id, mailbox_name=mailbox_name
        )
        if mailbox_cfg.mailbox_id is None:
            return LlmRuntimeConfig(
                provider_name=settings.llm_provider,
                base_url=settings.ollama_url
                if settings.llm_provider == "ollama"
                else settings.openai_url,
                model_name=settings.ollama_model
                if settings.llm_provider == "ollama"
                else settings.openai_model,
                api_key=settings.openai_api_key if settings.llm_provider == "openai" else None,
                request_timeout_seconds=120,
                mailbox_id=None,
            )

        with session_scope() as session:
            with LlmProviderSettingRepository(session) as llm_repo:
                provider = llm_repo.get_active_for_mailbox(mailbox_cfg.mailbox_id)
                if provider is None:
                    return LlmRuntimeConfig(
                        provider_name=settings.llm_provider,
                        base_url=settings.ollama_url
                        if settings.llm_provider == "ollama"
                        else settings.openai_url,
                        model_name=settings.ollama_model
                        if settings.llm_provider == "ollama"
                        else settings.openai_model,
                        api_key=(
                            settings.openai_api_key
                            if settings.llm_provider == "openai"
                            else None
                        ),
                        request_timeout_seconds=120,
                        mailbox_id=mailbox_cfg.mailbox_id,
                    )

            api_key: str | None = None
            if provider.api_key_secret_id is not None:
                with SecretStoreRepository(session) as secret_repo:
                    secret = secret_repo.get_by_id(provider.api_key_secret_id)
                    if secret:
                        api_key = self._vault.decrypt(
                            secret.encrypted_value, secret.key_version
                        ).value
            return LlmRuntimeConfig(
                provider_name=provider.provider_name,
                base_url=provider.base_url,
                model_name=provider.model_name,
                api_key=api_key,
                request_timeout_seconds=provider.request_timeout_seconds,
                mailbox_id=provider.mailbox_id,
            )

    def set_mailbox_and_provider_defaults(
        self,
        mailbox_payload: dict[str, Any],
        llm_payload: dict[str, Any],
    ) -> int:
        with session_scope() as session:
            with SecretStoreRepository(session) as secret_repo:
                password_cipher = self._vault.encrypt(mailbox_payload["imap_password"])
                password_secret = secret_repo.upsert(
                    secret_name=f"imap_password:{mailbox_payload['account_id']}:{mailbox_payload['mailbox_name']}",
                    secret_type="imap_password",
                    encrypted_value=password_cipher,
                    key_version=self._vault.key_version,
                )

                mailbox_id: int
                with MailboxSettingRepository(session) as mailbox_repo:
                    mailbox = mailbox_repo.create_or_update(
                        account_id=mailbox_payload["account_id"],
                        mailbox_name=mailbox_payload["mailbox_name"],
                        imap_host=mailbox_payload["imap_host"],
                        imap_port=mailbox_payload["imap_port"],
                        imap_username=mailbox_payload["imap_username"],
                        imap_password_secret_id=password_secret.id,
                        polling_interval_seconds=mailbox_payload.get(
                            "polling_interval_seconds", 300
                        ),
                        is_active=True,
                    )
                    mailbox_id = mailbox.id

                api_key_secret_id: int | None = None
                api_key = llm_payload.get("api_key")
                if isinstance(api_key, str) and api_key:
                    api_key_cipher = self._vault.encrypt(api_key)
                    api_key_secret = secret_repo.upsert(
                        secret_name=f"llm_api_key:{mailbox_id}:{llm_payload['provider_name']}",
                        secret_type="llm_api_key",
                        encrypted_value=api_key_cipher,
                        key_version=self._vault.key_version,
                    )
                    api_key_secret_id = api_key_secret.id

            with LlmProviderSettingRepository(session) as llm_repo:
                llm_repo.create_or_update(
                    mailbox_id=mailbox_id,
                    provider_name=llm_payload["provider_name"],
                    base_url=llm_payload["base_url"],
                    model_name=llm_payload["model_name"],
                    api_key_secret_id=api_key_secret_id,
                    request_timeout_seconds=llm_payload.get("request_timeout_seconds", 120),
                    options_json=llm_payload.get("options_json"),
                    is_active=True,
                )

            return mailbox_id
