import json
from datetime import datetime
import logging

from app.db_schema import get_conn
from app.llm import extract_tasks


logger = logging.getLogger(__name__)


def process() -> None:
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT id, content, from_address, subject, received_on FROM messages WHERE processed = 0"
    )
    rows = c.fetchall()

    for row in rows:
        msg_id, content, from_address, subject, received_on = row

        try:
            # Extract tasks from the message content using the LLM
            result = extract_tasks(msg_id, content, from_address, subject)

            if not result:
                logger.warning("No result returned for message ID: %s", msg_id)
                continue

            response = result.get("response", "")
            if len(response) == 0:
                logger.info("No tasks extracted for message ID: %s", msg_id)
                c.execute("UPDATE messages SET processed = 1 WHERE id = ?", (msg_id,))
                conn.commit()
                continue

            data_task = json.loads(response)

            # Log the extracted tasks for debugging
            logger.info(
                "Extracted tasks for message ID: %s | From: %s | Subject: %s",
                msg_id,
                from_address,
                subject,
            )

            # Extract client info and save
            client_info = data_task.get("client_info", {})
            client_id = None
            if (
                len(client_info) > 0
                and client_info.get("name") is not None
                and client_info.get("name_slug") is not None
            ):
                # Check if client already exists
                c.execute(
                    "SELECT id FROM client WHERE name_slug = ?",
                    (client_info.get("name_slug"),),
                )
                existing_client = c.fetchone()
                if existing_client:
                    client_id = existing_client[0]
                else:
                    # Save client info
                    c.execute(
                        """
                        INSERT INTO client (name, name_slug, emails, phone_numbers, created_at) 
                        VALUES (?, ?, ?, ?, ?)""",
                        (
                            client_info.get("name"),
                            client_info.get("name_slug"),
                            json.dumps(client_info.get("emails", [])),
                            json.dumps(client_info.get("phone_numbers", [])),
                            datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                        ),
                    )
                    client_id = c.lastrowid

            # Extract group info and save
            task_group_info = data_task.get("task_group_info", {})
            task_group_id = None
            if (
                len(task_group_info) > 0
                and task_group_info.get("name") is not None
                and task_group_info.get("name_slug") is not None
            ):
                # Check if task group already exists
                c.execute(
                    "SELECT id FROM task_groups WHERE name_slug = ?",
                    (task_group_info.get("name_slug"),),
                )
                existing_group = c.fetchone()
                if existing_group:
                    task_group_id = existing_group[0]
                else:
                    # Save task group info
                    c.execute(
                        """
                        INSERT INTO task_groups (name, name_slug, status, requested_on, expected_delivery_date, priority, created_at, client_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            task_group_info.get("name"),
                            task_group_info.get("name_slug"),
                            task_group_info.get("status"),
                            task_group_info.get("requested_on"),
                            task_group_info.get("expected_delivery_date"),
                            task_group_info.get("priority"),
                            datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                            client_id,
                        ),
                    )
                    task_group_id = c.lastrowid

            for task in data_task.get("tasks", []):
                c.execute(
                    """
                    INSERT INTO tasks (requested_on, expected_delivery_date, priority, content, status, created_at, task_group_id, ai_log_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task.get("requested_on"),
                        task.get("expected_delivery_date"),
                        task.get("priority"),
                        task.get("content"),
                        task.get("status"),
                        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                        task_group_id,
                        result.get("ai_log_id"),
                    ),
                )

            c.execute("UPDATE messages SET processed = 1 WHERE id = ?", (msg_id,))
            conn.commit()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            conn.rollback()
            logger.error("Error processing message %s: %s", msg_id, e)

    conn.close()
