import json
from datetime import datetime
import logging
from math import e
import os

from src.app.db import get_conn
from src.app.llm import extract_tasks
from src.app.logging_config import setup_logging


setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def process():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id, content FROM messages WHERE processed = 0")
    rows = c.fetchall()

    for row in rows:
        msg_id, content = row

        result = extract_tasks(content, msg_id)

        if len(result.get("response", "")) > 0:
            data = json.loads(result["response"])

            # logger.info("Extracted tasks for message %s: %s", msg_id, result)

            for task in data.get("tasks", []):
                c.execute(
                    """INSERT INTO tasks (content, priority, created_at, updated_at, ai_log_id) VALUES (?, ?, ?, ?, ?)""",
                    (
                        task,
                        data.get("priority"),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        result.get("ai_log_id"),
                    ),
                )

            c.execute("UPDATE messages SET processed = 1 WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
