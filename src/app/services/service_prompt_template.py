from __future__ import annotations

from dataclasses import dataclass

from app.db.database import session_scope
from app.repository import PromptTemplateRepository
from app.services.prompt_defaults import (
    EXTRACT_CONTEXT_TEMPLATE,
    EXTRACT_DEFAULT_INSTRUCTIONS,
    EXTRACT_JSON_SCHEMA,
    EXTRACT_MESSAGE_TEMPLATE,
    FILTER_CONTEXT_TEMPLATE,
    FILTER_DEFAULT_INSTRUCTIONS,
    FILTER_JSON_SCHEMA,
    FILTER_MESSAGE_TEMPLATE,
)


@dataclass(frozen=True)
class PromptSections:
    instructions: str
    language_hint: str
    json_response_schema: str
    context_template: str
    message_template: str


class ServicePromptTemplate:
    def _fallback_for_operation(self, operation: str) -> PromptSections:
        if operation == "classify_message":
            return PromptSections(
                instructions=FILTER_DEFAULT_INSTRUCTIONS,
                language_hint="English",
                json_response_schema=FILTER_JSON_SCHEMA,
                context_template=FILTER_CONTEXT_TEMPLATE,
                message_template=FILTER_MESSAGE_TEMPLATE,
            )
        return PromptSections(
            instructions=EXTRACT_DEFAULT_INSTRUCTIONS,
            language_hint="English",
            json_response_schema=EXTRACT_JSON_SCHEMA,
            context_template=EXTRACT_CONTEXT_TEMPLATE,
            message_template=EXTRACT_MESSAGE_TEMPLATE,
        )

    def get_sections(self, mailbox_id: int | None, operation: str) -> PromptSections:
        if mailbox_id is None:
            return self._fallback_for_operation(operation)

        with session_scope() as session:
            with PromptTemplateRepository(session) as repo:
                template = repo.get_active_for_mailbox(mailbox_id, operation)
                if template is None:
                    return self._fallback_for_operation(operation)
                return PromptSections(
                    instructions=template.instructions,
                    language_hint=template.language_hint,
                    json_response_schema=template.json_response_schema,
                    context_template=template.context_template,
                    message_template=template.message_template,
                )

    def create_or_update_template(
        self,
        mailbox_id: int,
        operation: str,
        instructions: str,
        language_hint: str,
    ) -> None:
        default_sections = self._fallback_for_operation(operation)
        with session_scope() as session:
            with PromptTemplateRepository(session) as repo:
                template = repo.create_or_update(
                    mailbox_id=mailbox_id,
                    operation=operation,
                    instructions=instructions,
                    language_hint=language_hint,
                    json_response_schema=default_sections.json_response_schema,
                    context_template=default_sections.context_template,
                    message_template=default_sections.message_template,
                    is_active=True,
                )
                repo.create_version_snapshot(
                    prompt_template_id=template.id,
                    version_label="v1",
                    language_hint=language_hint,
                    instructions=instructions,
                )
