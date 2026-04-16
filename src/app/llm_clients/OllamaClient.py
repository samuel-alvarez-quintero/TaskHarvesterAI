import logging
from typing import Any

import requests
import os
from datetime import datetime

from app.db_schema import get_conn
from app.utility import clear_url
from app.llm_clients.LLMClientInterface import LLMClientInterface

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


class OllamaClient(LLMClientInterface):
    _logger = logging.getLogger(__name__)
    
    def generate(self, prompt: str, msg_id: int) -> dict[str, Any]:
        base_url = clear_url(OLLAMA_URL)

        conn = get_conn()
        c = conn.cursor()

        # Log the prompt before making the API call
        c.execute(
            """INSERT INTO ai_log (provider, model, prompt, created_at, message_id) VALUES (?, ?, ?, ?, ?)""",
            (
                "ollama",
                OLLAMA_MODEL,
                prompt,
                datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                msg_id,
            ),
        )
        ai_log_id = c.lastrowid

        conn.commit()

        self._logger.info(f"Using Ollama model: {OLLAMA_MODEL}")

        try:
            r = requests.post(
                f"{base_url}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            json_response = r.json()
        except (requests.RequestException, ValueError) as exc:
            c.execute(
                "UPDATE ai_log SET status = ?, response = ?, updated_at = ? WHERE id = ?",
                (
                    "failed",
                    str(exc),
                    datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                    ai_log_id,
                ),
            )
            conn.commit()
            conn.close()
            return {
                "error": str(exc),
                "details": None,
                "response": "",
                "ai_log_id": ai_log_id,
            }

        status = "completed" if json_response.get("done") else "failed"
        response_text = json_response.get("response", "")

        c.execute(
            "UPDATE ai_log SET http_status = ?, status = ?, response = ?, updated_at = ? WHERE id = ?",
            (
                r.status_code,
                status,
                response_text,
                datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                ai_log_id,
            ),
        )
        conn.commit()
        conn.close()

        if status == "completed":
            return {
                "error": None,
                "details": json_response,
                "response": response_text,
                "ai_log_id": ai_log_id,
            }
        else:
            return {
                "error": f"API call failed with status: {status}",
                "details": json_response,
                "response": "",
                "ai_log_id": ai_log_id,
            }

    def get_llm_info(self) -> dict[str, str]:
        return {
            "provider": "ollama",
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
        }
