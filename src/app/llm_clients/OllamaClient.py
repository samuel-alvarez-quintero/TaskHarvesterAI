import requests
import os
from datetime import datetime

from src.app.db import get_conn
from src.app.utility import clear_url
from src.app.llm_clients.LLMClientInterface import LLMClientInterface

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


class OllamaClient(LLMClientInterface):
    def generate(self, prompt: str, msg_id: int) -> str:
        base_url = clear_url(OLLAMA_URL)

        conn = get_conn()
        c = conn.cursor()

        # Log the prompt before making the API call
        c.execute(
            """INSERT INTO ai_log (provider, model, prompt, created_at, message_id) VALUES (?, ?, ?, ?, ?) RETURNING id""",
            (
                "ollama",
                OLLAMA_MODEL,
                prompt,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                msg_id,
            ),
        )

        r = requests.post(
            f"{base_url}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )

        json_response = r.json()

        status = "completed" if json_response.get("done") else "failed"

        c.execute(
            "UPDATE ai_log SET http_status = ?, status = ?, response = ?, updated_at = ? WHERE id = ?",
            (
                r.status_code,
                status,
                json_response["response"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                msg_id,
            ),
        )
        conn.commit()
        conn.close()

        if status == "completed":
            return {
                "error": None,
                "details": json_response,
                "response": json_response["response"],
                "ai_log_id": c.lastrowid,
            }
        else:
            return {
                "error": f"API call failed with status: {status}",
                "details": json_response,
                "response": "",
                "ai_log_id": c.lastrowid,
            }

    def get_llm_info(self) -> dict:
        return {
            "provider": "ollama",
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
        }
