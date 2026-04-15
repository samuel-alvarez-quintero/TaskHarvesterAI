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
        "tasks": ["..."],
        "priority": "low|medium|high"
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
