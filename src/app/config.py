from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/tasks.db")
    db_path: str = os.getenv("DB_PATH", "data/tasks.db")

    imap_host: str | None = os.getenv("IMAP_HOST")
    imap_user: str | None = os.getenv("IMAP_USER")
    imap_pass: str | None = os.getenv("IMAP_PASS")
    imap_mailbox: str = os.getenv("IMAP_MAILBOX", "INBOX")

    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")
    openai_url: str = os.getenv("OPENAI_URL", "https://api.openai.com")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()

    @property
    def database_path(self) -> Path:
        return Path(self.db_path)


settings = Settings.from_env()
