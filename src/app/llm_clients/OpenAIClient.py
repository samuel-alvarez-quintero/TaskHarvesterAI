import json
import logging
import requests
import os
from datetime import datetime

from src.app.db import get_conn
from src.app.utility import clear_url
from src.app.llm_clients.LLMClientInterface import LLMClientInterface

OPENAI_URL = os.getenv("OPENAI_URL", "https://api.openai.com")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", False)


class OpenAIClient(LLMClientInterface):
    _logger = logging.getLogger(__name__)
    
    def generate(self, prompt: str, msg_id: int) -> dict:
        base_url = clear_url(OPENAI_URL)

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

        conn = get_conn()
        c = conn.cursor()

        # Log the prompt before making the API call
        c.execute(
            """INSERT INTO ai_log (provider, model, prompt, created_at, message_id) VALUES (?, ?, ?, ?, ?)""",
            (
                "openai",
                OPENAI_MODEL,
                prompt,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                msg_id,
            ),
        )
        ai_log_id = c.lastrowid

        conn.commit()
        self._logger.info(f"Using OpenAI model: {OPENAI_MODEL}")

        try:
            r = requests.post(
                url=f"{base_url}/v1/responses",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                },
                json={
                    "model": OPENAI_MODEL,
                    "input": [
                        {
                            "role": "user",
                            "content": json.dumps(
                                {"type": "input_text", "text": prompt}
                            ),
                        }
                    ],
                },
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

        status = json_response.get("status")

        c.execute(
            "UPDATE ai_log SET http_status = ?, status = ?, response = ?, updated_at = ? WHERE id = ?",
            (
                r.status_code,
                status,
                json.dumps(json_response),
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
                "response": json_response.get("output", [{}])[0]
                .get("content", [{}])[0]
                .get("text", ""),
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
            "provider": "openai",
            "url": OPENAI_URL,
            "model": OPENAI_MODEL,
        }
