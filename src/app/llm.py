import json
import logging
import os
from typing import Any

from app.db import get_conn
from app.llm_clients.OllamaClient import OllamaClient
from app.llm_clients.OpenAIClient import OpenAIClient
from app.llm_clients.LLMClientInterface import LLMClientInterface

logger = logging.getLogger(__name__)


def get_llm() -> LLMClientInterface:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    logger.info(f"Using LLM provider: {LLM_PROVIDER}")

    match LLM_PROVIDER:
        case "openai":
            return OpenAIClient()
        case "ollama":
            return OllamaClient()
        case _:
            raise ValueError("LLM not supported")


def extract_tasks(
    msg_id: int, msg_content: str, sender: str, subject: str
) -> dict[str, Any] | None:
    conn = get_conn()
    c = conn.cursor()

    # Search for existing tasks, task_groups and clients in the current context to avoid duplicates
    current_context_json = {"clients": {}}

    # Search all clients
    c.execute("SELECT * FROM client")
    clients = c.fetchall()

    for client in clients:
        client_id = client[0]

        current_context_json["clients"][client_id] = {
            "name": client[1],
            "name_slug": client[2],
            "status": client[3],
            "emails": client[4].split(",") if client[4] else [],
            "phone_numbers": client[5].split(",") if client[5] else [],
            "task_groups": {},
        }

        # Search all task groups for the client
        c.execute(
            "SELECT * FROM task_groups WHERE client_id = ?",
            (client_id,),
        )
        task_groups = c.fetchall()

        for task_group in task_groups:
            task_group_id = task_group[0]

            current_context_json["clients"][client_id]["task_groups"][task_group_id] = {
                "name": task_group[1],
                "name_slug": task_group[2],
                "status": task_group[3],
                "requested_on": task_group[4],
                "expected_delivery_date": task_group[5],
                "priority": task_group[6],
                "tasks": [],
            }

            # Search all tasks for the task group
            c.execute(
                "SELECT content FROM tasks WHERE task_group_id = ?",
                (task_group_id,),
            )
            tasks = c.fetchall()

            # Add tasks to current context
            for task in tasks:
                current_context_json["clients"][client_id]["task_groups"][
                    task_group_id
                ]["tasks"].append(task)

    current_context = json.dumps(current_context_json)

    # Build the prompt with the current context and the new message
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
                "priority": "low|medium|high"
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
                    "priority": "low|medium|high"
                    "status": "pending|in_progress|completed"
                }},
                ...
            ]
        }}

        Ejemplo de respuesta JSON:
        {{
            "task_group_info": {{
                "name": "Tareas para proyecto X",
                "name_slug": "tareas-para-proyecto-x",
                "requested_on": "2024-06-01 10:00:00+0000",
                "expected_delivery_date": "2024-06-10 18:00:00+0000",
                "priority": "high",
                "status": "pending"
            }},
            "client_info": {{
                "name": "Empresa ABC",
                "name_slug": "empresa-abc",
                "emails": ["example@empresa-abc.com", "Gerencia <gerencia@empresa-abc.com>"],
                "phone_numbers": ["+1234567890"]
            }},
            "tasks": [
                {{
                    "content": "Investigar sobre el mercado objetivo para el proyecto X.",
                    "requested_on": "2024-06-01 10:00:00+0000",
                    "expected_delivery_date": "2024-06-05 18:00:00+0000",
                    "priority": "high",
                    "status": "pending"
                }},
                {{
                    "content": "Desarrollar un plan de marketing para el proyecto X.",
                    "requested_on": "2024-06-01 10:00:00+0000",
                    "expected_delivery_date": "2024-06-10 18:00:00+0000",
                    "priority": "medium",
                    "status": "pending"
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

    # Call the LLM to extract tasks
    try:
        if get_llm() is not None:
            res = get_llm().generate(prompt, msg_id)

            return res
        else:
            logger.error("No LLM client available.")
            return None
    except ValueError as e:
        logger.error(f"Error extracting tasks: {e}")
        return None
