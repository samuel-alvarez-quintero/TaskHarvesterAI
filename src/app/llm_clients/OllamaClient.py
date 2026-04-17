import json
import logging
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import session_scope
from app.utility import clear_url
from app.llm_clients.LLMClientInterface import LLMClientInterface
from app.repository.ai_log_repository import AiLogRepository

OLLAMA_URL = settings.ollama_url
OLLAMA_MODEL = settings.ollama_model


class OllamaClient(LLMClientInterface):
    _logger = logging.getLogger(__name__)

    def generate(
        self,
        prompt: str,
        msg_id: int,
        operation: str = "extract_tasks",
        session: Session | None = None,
    ) -> dict[str, Any]:
        base_url = clear_url(OLLAMA_URL)

        with session_scope() as s:
            with AiLogRepository(session or s) as repo:
                ai_log = repo.create_ai_log(
                    provider="ollama",
                    model=OLLAMA_MODEL,
                    operation=operation,
                    message_row_id=msg_id,
                    prompt=prompt,
                )
                ai_log_id = ai_log.id

            self._logger.info(f"Using Ollama model: {OLLAMA_MODEL}")

            try:
                r = requests.post(
                    f"{base_url}/api/generate",
                    json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                    timeout=120,
                )
                json_response = r.json()
            except (requests.RequestException, ValueError) as exc:
                with AiLogRepository(session or s) as repo:
                    repo.update_ai_log(
                        ai_log_id=ai_log_id,
                        status="failed",
                        error_message=str(exc),
                    )
                return {
                    "error": str(exc),
                    "details": None,
                    "response": "",
                    "ai_log_id": ai_log_id,
                }

            status = "completed" if json_response.get("done") else "failed"
            response_text = json_response.get("response", "")

            with AiLogRepository(session or s) as repo:
                repo.update_ai_log(
                    ai_log_id=ai_log_id,
                    http_status=str(r.status_code),
                    status=status,
                    response=response_text,
                    response_payload=json.dumps(
                        json_response, ensure_ascii=True, default=str
                    ),
                )

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
