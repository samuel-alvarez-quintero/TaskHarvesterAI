import requests
import os
from datetime import datetime

from src.app.db import get_conn
from src.app.utility import clear_url
from src.app.llm_clients.LLMClientInterface import LLMClientInterface

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


class OllamaClient(LLMClientInterface):
    def generate(self, prompt: str, msg_id: int) -> dict:
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
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                msg_id,
            ),
        )
        ai_log_id = c.lastrowid

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
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

    def get_llm_info(self) -> dict:
        return {
            "provider": "ollama",
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
        }
