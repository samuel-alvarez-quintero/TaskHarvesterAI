from __future__ import annotations

from app.config import settings
from app.services.service_configuration import ServiceConfiguration
from app.services.service_prompt_template import ServicePromptTemplate


class ServiceFirstRunSetup:
    def __init__(self) -> None:
        self._config = ServiceConfiguration()
        self._prompts = ServicePromptTemplate()

    def ensure_setup(self) -> None:
        setup_complete = self._config.get_workspace_setting("setup_complete")
        if setup_complete == "true":
            return

        if not settings.imap_user or not settings.imap_host:
            # Setup remains incomplete until user provides runtime values externally.
            return

        mailbox_id = self._config.set_mailbox_and_provider_defaults(
            mailbox_payload={
                "account_id": settings.imap_user,
                "mailbox_name": settings.imap_mailbox,
                "imap_host": settings.imap_host,
                "imap_port": settings.imap_port,
                "imap_username": settings.imap_user,
                "imap_password": settings.imap_pass or "",
                "polling_interval_seconds": 300,
            },
            llm_payload={
                "provider_name": settings.llm_provider,
                "base_url": settings.ollama_url
                if settings.llm_provider == "ollama"
                else settings.openai_url,
                "model_name": settings.ollama_model
                if settings.llm_provider == "ollama"
                else settings.openai_model,
                "api_key": settings.openai_api_key if settings.llm_provider == "openai" else None,
                "request_timeout_seconds": 120,
            },
        )

        self._prompts.create_or_update_template(
            mailbox_id=mailbox_id,
            operation="extract_tasks",
            instructions="Extract actionable tasks and return only valid JSON.",
            language_hint="English",
        )
        self._prompts.create_or_update_template(
            mailbox_id=mailbox_id,
            operation="classify_message",
            instructions="Classify message indicators and return only valid JSON.",
            language_hint="English",
        )
        self._config.set_workspace_setting("setup_complete", "true")
