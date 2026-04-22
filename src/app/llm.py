import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import session_scope
from app.llm_clients.ollama_client import OllamaClient
from app.llm_clients.openai_client import OpenAIClient
from app.llm_clients.llm_client_interface import LLMClientInterface
from app.repository import ClientRepository, TaskGroupRepository, TaskRepository
from app.services import ServiceConfiguration, ServicePromptTemplate

logger = logging.getLogger(__name__)


def get_llm(account_id: str | None = None, mailbox_name: str | None = None) -> LLMClientInterface:
    runtime = ServiceConfiguration().get_llm_runtime_config(
        account_id=account_id,
        mailbox_name=mailbox_name,
    )
    llm_provider = runtime.provider_name.lower()
    logger.info("Using LLM provider: %s", llm_provider)

    match llm_provider:
        case "openai":
            return OpenAIClient(
                base_url=runtime.base_url,
                model_name=runtime.model_name,
                api_key=runtime.api_key,
                timeout_seconds=runtime.request_timeout_seconds,
            )
        case "ollama":
            return OllamaClient(
                base_url=runtime.base_url,
                model_name=runtime.model_name,
                timeout_seconds=runtime.request_timeout_seconds,
            )
        case _:
            raise ValueError("LLM not supported")


def extract_tasks(
    msg_id: int,
    msg_content: str,
    sender: str,
    subject: str,
    account_id: str | None = None,
    mailbox_name: str | None = None,
    session: Session | None = None,
) -> dict[str, Any] | None:
    current_context_json: dict[str, Any] = {"clients": {}}
    runtime_cfg = ServiceConfiguration().get_llm_runtime_config(
        account_id=account_id,
        mailbox_name=mailbox_name,
    )
    prompt_sections = ServicePromptTemplate().get_sections(
        mailbox_id=runtime_cfg.mailbox_id,
        operation="extract_tasks",
    )

    with session_scope() as s:
        with ClientRepository(session or s) as client_repo:
            clients = client_repo.get_all_clients()
            for client in clients:
                client_id = client["id"]
                current_context_json["clients"][client_id] = {
                    "name": client["name"],
                    "name_slug": client["name_slug"],
                    "status": client["status"],
                    "emails": [client["primary_email"]]
                    if client["primary_email"]
                    else [],
                    "phone_numbers": [client["primary_phone"]]
                    if client["primary_phone"]
                    else [],
                    "notes": client.get("notes"),
                    "task_groups": {},
                }

                with TaskGroupRepository(session or s) as task_group_repo:
                    task_groups = task_group_repo.get_task_groups_by_client(client_id)
                    for task_group in task_groups:
                        task_group_id = task_group["id"]
                        current_context_json["clients"][client_id]["task_groups"][
                            task_group_id
                        ] = {
                            "name": task_group["name"],
                            "name_slug": task_group["name_slug"],
                            "status": task_group["status"],
                            "requested_on": task_group["requested_on"],
                            "expected_delivery_date": task_group[
                                "expected_delivery_date"
                            ],
                            "priority": task_group["priority"],
                            "tasks": [],
                        }

                        with TaskRepository(session or s) as task_repo:
                            tasks = task_repo.get_tasks_by_task_group(task_group_id)
                            for task in tasks:
                                current_context_json["clients"][client_id][
                                    "task_groups"
                                ][task_group_id]["tasks"].append(
                                    {
                                        "content": task["content"],
                                        "status": task["status"],
                                        "priority": task["priority"],
                                    }
                                )

        current_context = json.dumps(current_context_json, ensure_ascii=True, default=str)

        context_block = prompt_sections.context_template.format(
            context_json=current_context,
            sender=sender,
            subject=subject,
        )
        message_block = prompt_sections.message_template.format(message_text=msg_content)
        prompt = (
            f"Language hint: {prompt_sections.language_hint}\n"
            f"Instructions:\n{prompt_sections.instructions}\n\n"
            f"JSON response schema:\n{prompt_sections.json_response_schema}\n\n"
            f"Context:\n{context_block}\n\n"
            f"Message:\n{message_block}"
        )

        try:
            return get_llm(
                account_id=account_id,
                mailbox_name=mailbox_name,
            ).generate(prompt, msg_id, operation="extract_tasks", session=session or s)
        except ValueError as exc:
            logger.error("Error extracting tasks: %s", exc)
            return None
