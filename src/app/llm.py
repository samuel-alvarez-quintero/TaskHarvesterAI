import logging
import os
from typing import Any

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


def extract_tasks(text: str, msg_id: int) -> dict[str, Any] | None:
    prompt = f"""
        Responde en español.
        No agregues texto fuera del JSON.
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
        
        Mensaje:
        {text}
        """

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
