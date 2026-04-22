import json
import logging
from typing import Any
import requests
from sqlalchemy.orm import Session

from app.db.database import session_scope
from app.utility import clear_url
from app.llm_clients.llm_client_interface import LLMClientInterface
from app.repository.ai_log_repository import AiLogRepository


class OpenAIClient(LLMClientInterface):
    _logger = logging.getLogger(__name__)

    def generate(
        self,
        prompt: str,
        msg_id: int,
        operation: str = "extract_tasks",
        session: Session | None = None,
    ) -> dict[str, Any]:
        base_url = clear_url(self.base_url)

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

        with session_scope() as s:
            with AiLogRepository(session or s) as repo:
                ai_log = repo.create_ai_log(
                    provider="openai",
                    model=self.model_name,
                    operation=operation,
                    message_row_id=msg_id,
                    prompt=prompt,
                )
                ai_log_id = ai_log.id

            self._logger.info("Using OpenAI model: %s", self.model_name)

            try:
                r = requests.post(
                    url=f"{base_url}/v1/responses",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json={
                        "model": self.model_name,
                        "input": [
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {"type": "input_text", "text": prompt},
                                    ensure_ascii=True,
                                    default=str,
                                ),
                            }
                        ],
                    },
                    timeout=self.timeout_seconds,
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

            status = json_response.get("status")

            with AiLogRepository(session or s) as repo:
                repo.update_ai_log(
                    ai_log_id=ai_log_id,
                    http_status=str(r.status_code),
                    status=status,
                    response=json_response.get("output", [{}])[0]
                    .get("content", [{}])[0]
                    .get("text", ""),
                    response_payload=json.dumps(
                        json_response, ensure_ascii=True, default=str
                    ),
                )

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

    def get_llm_info(self) -> dict[str, str]:
        return {
            "provider": "openai",
            "url": self.base_url,
            "model": self.model_name,
        }
