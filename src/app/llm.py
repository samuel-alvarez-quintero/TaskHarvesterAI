import json
import logging
from re import S
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import session_scope
from app.llm_clients.ollama_client import OllamaClient
from app.llm_clients.openai_client import OpenAIClient
from app.llm_clients.llm_client_interface import LLMClientInterface
from app.repository import ClientRepository, TaskGroupRepository, TaskRepository

logger = logging.getLogger(__name__)


def get_llm() -> LLMClientInterface:
    llm_provider = settings.llm_provider
    logger.info("Using LLM provider: %s", llm_provider)

    match llm_provider:
        case "openai":
            return OpenAIClient()
        case "ollama":
            return OllamaClient()
        case _:
            raise ValueError("LLM not supported")


def extract_tasks(
    msg_id: int,
    msg_content: str,
    sender: str,
    subject: str,
    session: Session | None = None,
) -> dict[str, Any] | None:
    current_context_json: dict[str, Any] = {"clients": {}}

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

        prompt = f"""
            Responde en español.
            No agregues texto fuera del JSON.
            Usa el contexto actual en la base de datos para verificar los clientes, grupos de tareas y tareas existentes para omitirlas.
            Si no encuentras la información de un cliente, usa el remitente del mensaje para inferir el nombre del cliente y su información de contacto (correo electrónico y número de teléfono). Si no puedes inferir el nombre del cliente, usa "Cliente desconocido".
            Ignorar los clientes desactivados (status = 'inactive') y todos sus grupos de tareas y tareas en el contexto actual.
            Si no encuentras la información de un grupo de tareas, usa el asunto del mensaje para inferir el nombre del grupo de tareas. Si no puedes inferir el nombre del grupo de tareas, usa: nombre del cliente + " - Tareas sin nombre".
            Ignorar los grupos de tareas completados (status = 'completed') y todas sus tareas en el contexto actual, incluso si el cliente está activo.
            Ignorar las tareas completadas (status = 'completed') en el contexto actual, incluso si el cliente y el grupo de tareas están activos.
            Analiza el mensaje y devuelve JSON válido:

            Respuesta JSON con esta estructura:
            {{
                "task_group_info": {{
                    "name": "...",
                    "name_slug": "...",
                    "requested_on": "%Y-%m-%d %H:%M:%S%z",
                    "expected_delivery_date": "%Y-%m-%d %H:%M:%S%z or null",
                    "priority": "low|medium|high",
                    "status": "pending|in_progress|completed"
                }},
                "client_info": {{
                    "name": "...",
                    "name_slug": "...",
                    "emails": ["...", "..."],
                    "phone_numbers": ["...", "..."]
                }},
                "tasks": [
                    {{
                        "content": "...",
                        "requested_on": "%Y-%m-%d %H:%M:%S%z",
                        "expected_delivery_date": "%Y-%m-%d %H:%M:%S%z or null",
                        "priority": "low|medium|high",
                        "status": "pending|in_progress|completed"
                    }}
                ]
            }}

            Contexto actual en la base de datos:
            {current_context}

            Remitente del mensaje:
            {sender}

            Asunto del mensaje:
            {subject}

            Mensaje:
            {msg_content}
            """

        try:
            return get_llm().generate(prompt, msg_id, operation="extract_tasks", session=session or s)
        except ValueError as exc:
            logger.error("Error extracting tasks: %s", exc)
            return None
