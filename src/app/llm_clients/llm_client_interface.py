from abc import abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class LLMClientInterface:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: str | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.base_url = base_url
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def generate(
        self,
        prompt: str,
        msg_id: int,
        operation: str = "extract_tasks",
        session: Session | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_llm_info(self) -> dict[str, str]:
        pass
