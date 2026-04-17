import sqlite3
from pathlib import Path

from app.config import settings

DB_PATH = Path(settings.db_path)
SCHEMA_PATH = Path(__file__).with_name("tasks_schema.sql")


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_conn() as conn:
        conn.executescript(schema_sql)
