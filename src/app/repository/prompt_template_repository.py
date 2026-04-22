from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import PromptTemplate, PromptTemplateVersion
from app.repository.base import BaseRepository


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_active_for_mailbox(
        self, mailbox_id: int, operation: str
    ) -> PromptTemplate | None:
        return (
            self.session.query(PromptTemplate)
            .filter(
                PromptTemplate.mailbox_id == mailbox_id,
                PromptTemplate.operation == operation,
                PromptTemplate.is_active == 1,
            )
            .order_by(PromptTemplate.id.asc())
            .first()
        )

    def create_or_update(
        self,
        mailbox_id: int,
        operation: str,
        instructions: str,
        language_hint: str,
        json_response_schema: str,
        context_template: str,
        message_template: str,
        is_active: bool = True,
    ) -> PromptTemplate:
        template = self.get_active_for_mailbox(mailbox_id, operation)
        if template is None:
            template = PromptTemplate(
                mailbox_id=mailbox_id,
                operation=operation,
                instructions=instructions,
                language_hint=language_hint,
                json_response_schema=json_response_schema,
                context_template=context_template,
                message_template=message_template,
                is_active=1 if is_active else 0,
            )
            self.add(template)
            self.session.flush()
            return template

        template.instructions = instructions
        template.language_hint = language_hint
        template.json_response_schema = json_response_schema
        template.context_template = context_template
        template.message_template = message_template
        template.is_active = 1 if is_active else 0
        template.updated_at = datetime.now().astimezone()
        return template

    def create_version_snapshot(
        self,
        prompt_template_id: int,
        version_label: str,
        language_hint: str,
        instructions: str,
    ) -> PromptTemplateVersion:
        version = PromptTemplateVersion(
            prompt_template_id=prompt_template_id,
            version_label=version_label,
            language_hint=language_hint,
            instructions=instructions,
        )
        self.session.add(version)
        self.session.flush()
        return version
