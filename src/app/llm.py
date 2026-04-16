import json
import logging
import os
from typing import Any

from app.db.sqlite.database import get_conn
from app.llm_clients.OllamaClient import OllamaClient
from app.llm_clients.OpenAIClient import OpenAIClient
from app.llm_clients.LLMClientInterface import LLMClientInterface

logger = logging.getLogger(__name__)


def get_llm() -> LLMClientInterface:
    llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    logger.info("Using LLM provider: %s", llm_provider)

    match llm_provider:
        case "openai":
            return OpenAIClient()
        case "ollama":
            return OllamaClient()
        case _:
            raise ValueError("LLM not supported")


def extract_tasks(
    msg_id: int, msg_content: str, sender: str, subject: str
) -> dict[str, Any] | None:
    with get_conn() as conn:
        c = conn.cursor()

        current_context_json: dict[str, Any] = {"clients": {}}

        c.execute(
            """
            SELECT id, name, name_slug, status, primary_email, primary_phone, notes
            FROM client
            """
        )
        clients = c.fetchall()

        for client in clients:
            client_id = client[0]
            current_context_json["clients"][client_id] = {
                "name": client[1],
                "name_slug": client[2],
                "status": client[3],
                "emails": [client[4]] if client[4] else [],
                "phone_numbers": [client[5]] if client[5] else [],
                "notes": client[6],
                "task_groups": {},
            }

            c.execute(
                """
                SELECT id, name, name_slug, status, requested_on, expected_delivery_date, priority
                FROM task_groups
                WHERE client_id = ?
                """,
                (client_id,),
            )
            task_groups = c.fetchall()

            for task_group in task_groups:
                task_group_id = task_group[0]
                current_context_json["clients"][client_id]["task_groups"][
                    task_group_id
                ] = {
                    "name": task_group[1],
                    "name_slug": task_group[2],
                    "status": task_group[3],
                    "requested_on": task_group[4],
                    "expected_delivery_date": task_group[5],
                    "priority": task_group[6],
                    "tasks": [],
                }

                c.execute(
                    """
                    SELECT content, status, priority
                    FROM tasks
                    WHERE task_group_id = ?
                    """,
                    (task_group_id,),
                )
                tasks = c.fetchall()

                for task in tasks:
                    current_context_json["clients"][client_id]["task_groups"][
                        task_group_id
                    ]["tasks"].append(
                        {
                            "content": task[0],
                            "status": task[1],
                            "priority": task[2],
                        }
                    )

    current_context = json.dumps(current_context_json)

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
        return get_llm().generate(prompt, msg_id, operation="extract_tasks")
    except ValueError as exc:
        logger.error("Error extracting tasks: %s", exc)
        return None
