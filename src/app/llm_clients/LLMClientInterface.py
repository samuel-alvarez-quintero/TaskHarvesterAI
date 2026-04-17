from abc import abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class LLMClientInterface:
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
