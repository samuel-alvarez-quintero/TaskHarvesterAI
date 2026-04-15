import json
from datetime import datetime
import logging

from app.db import get_conn
from app.llm import extract_tasks


logger = logging.getLogger(__name__)


def process() -> None:
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id, content, from_address, subject FROM messages WHERE processed = 0")
    rows = c.fetchall()

    for row in rows:
        msg_id, content, from_address, subject = row

        try:
            result = extract_tasks(content, msg_id)

            if not result:
                logger.warning("No result returned for message ID: %s", msg_id)
                continue

            response = result.get("response", "")
            if len(response) == 0:
                logger.info("No tasks extracted for message ID: %s", msg_id)
                c.execute("UPDATE messages SET processed = 1 WHERE id = ?", (msg_id,))
                conn.commit()
                continue

            data = json.loads(response)

            logger.info("Extracted tasks for message ID: %s | From: %s | Subject: %s", msg_id, from_address, subject)

            for task in data.get("tasks", []):
                c.execute(
                    """INSERT INTO tasks (content, priority, created_at, updated_at, ai_log_id) VALUES (?, ?, ?, ?, ?)""",
                    (
                        task,
                        data.get("priority"),
                        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                        result.get("ai_log_id"),
                    ),
                )

            c.execute("UPDATE messages SET processed = 1 WHERE id = ?", (msg_id,))
            conn.commit()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            conn.rollback()
            logger.error("Error processing message %s: %s", msg_id, e)
        except Exception as e:
            conn.rollback()
            logger.exception("Unexpected error processing message %s", msg_id)
    conn.close()
