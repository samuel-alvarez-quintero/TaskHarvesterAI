import json
from datetime import datetime
import logging

from app.db.sqlite.database import get_conn
from app.llm import extract_tasks


logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")


def process() -> None:
    with get_conn() as conn:
        c = conn.cursor()

        c.execute(
            """
            SELECT id, body_text_clean, body_text_raw, from_email, subject, received_on
            FROM messages
            WHERE status = 'pending'
            ORDER BY received_on DESC
            """
        )
        rows = c.fetchall()

        for row in rows:
            msg_id, body_text_clean, body_text_raw, from_email, subject, received_on = (
                row
            )
            message_text = body_text_clean or body_text_raw or ""
            sender = from_email or ""
            subject = subject or ""

            try:
                c.execute(
                    """
                    UPDATE messages
                    SET status = 'processing', last_attempt_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (_now(), _now(), msg_id),
                )
                conn.commit()

                result = extract_tasks(msg_id, message_text, sender, subject)
                if not result:
                    logger.warning("No result returned for message ID: %s", msg_id)
                    c.execute(
                        """
                        UPDATE messages
                        SET status = 'error',
                            error_count = error_count + 1,
                            last_error = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        ("No result returned by LLM extraction.", _now(), msg_id),
                    )
                    conn.commit()
                    continue

                response = result.get("response", "")
                if len(response) == 0:
                    logger.info("No tasks extracted for message ID: %s", msg_id)
                    c.execute(
                        """
                        UPDATE messages
                        SET status = 'done',
                            processed_at = ?,
                            updated_at = ?,
                            last_error = NULL
                        WHERE id = ?
                        """,
                        (_now(), _now(), msg_id),
                    )
                    conn.commit()
                    continue

                data_task = json.loads(response)

                logger.info(
                    "Extracted tasks for message ID: %s | From: %s | Subject: %s",
                    msg_id,
                    sender,
                    subject,
                )

                client_info = data_task.get("client_info", {})
                client_id = None
                if client_info.get("name") and client_info.get("name_slug"):
                    primary_email = next(
                        (
                            email
                            for email in client_info.get("emails", [])
                            if isinstance(email, str) and email.strip()
                        ),
                        None,
                    )
                    primary_phone = next(
                        (
                            phone
                            for phone in client_info.get("phone_numbers", [])
                            if isinstance(phone, str) and phone.strip()
                        ),
                        None,
                    )

                    c.execute(
                        "SELECT id FROM client WHERE name_slug = ?",
                        (client_info.get("name_slug"),),
                    )
                    existing_client = c.fetchone()
                    if existing_client:
                        client_id = existing_client[0]
                        c.execute(
                            """
                            UPDATE client
                            SET name = ?,
                                primary_email = COALESCE(primary_email, ?),
                                primary_phone = COALESCE(primary_phone, ?),
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                client_info.get("name"),
                                primary_email,
                                primary_phone,
                                _now(),
                                client_id,
                            ),
                        )
                    else:
                        c.execute(
                            """
                            INSERT INTO client (
                                name,
                                name_slug,
                                primary_email,
                                primary_phone,
                                created_at,
                                updated_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                client_info.get("name"),
                                client_info.get("name_slug"),
                                primary_email,
                                primary_phone,
                                _now(),
                                _now(),
                            ),
                        )
                        client_id = c.lastrowid

                task_group_info = data_task.get("task_group_info", {})
                task_group_id = None
                if task_group_info.get("name") and task_group_info.get("name_slug"):
                    c.execute(
                        "SELECT id FROM task_groups WHERE name_slug = ?",
                        (task_group_info.get("name_slug"),),
                    )
                    existing_group = c.fetchone()
                    if existing_group:
                        task_group_id = existing_group[0]
                        c.execute(
                            """
                            UPDATE task_groups
                            SET name = ?,
                                status = ?,
                                requested_on = ?,
                                expected_delivery_date = ?,
                                priority = ?,
                                client_id = COALESCE(?, client_id),
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                task_group_info.get("name"),
                                task_group_info.get("status", "pending"),
                                task_group_info.get("requested_on") or received_on,
                                task_group_info.get("expected_delivery_date"),
                                task_group_info.get("priority"),
                                client_id,
                                _now(),
                                task_group_id,
                            ),
                        )
                    else:
                        c.execute(
                            """
                            INSERT INTO task_groups (
                                name,
                                name_slug,
                                status,
                                requested_on,
                                expected_delivery_date,
                                priority,
                                client_id,
                                source_message_id,
                                created_at,
                                updated_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                task_group_info.get("name"),
                                task_group_info.get("name_slug"),
                                task_group_info.get("status", "pending"),
                                task_group_info.get("requested_on") or received_on,
                                task_group_info.get("expected_delivery_date"),
                                task_group_info.get("priority"),
                                client_id,
                                msg_id,
                                _now(),
                                _now(),
                            ),
                        )
                        task_group_id = c.lastrowid

                for task in data_task.get("tasks", []):
                    task_content = task.get("content")
                    if not task_content:
                        continue

                    c.execute(
                        """
                        SELECT id FROM tasks
                        WHERE source_message_id = ?
                          AND content = ?
                          AND COALESCE(task_group_id, 0) = COALESCE(?, 0)
                        """,
                        (msg_id, task_content, task_group_id),
                    )
                    existing_task = c.fetchone()
                    if existing_task:
                        c.execute(
                            """
                            UPDATE tasks
                            SET requested_on = ?,
                                expected_delivery_date = ?,
                                priority = ?,
                                status = ?,
                                ai_log_id = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                task.get("requested_on") or received_on,
                                task.get("expected_delivery_date"),
                                task.get("priority"),
                                task.get("status", "pending"),
                                result.get("ai_log_id"),
                                _now(),
                                existing_task[0],
                            ),
                        )
                        continue

                    c.execute(
                        """
                        INSERT INTO tasks (
                            content,
                            status,
                            priority,
                            requested_on,
                            expected_delivery_date,
                            task_group_id,
                            source_message_id,
                            ai_log_id,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            task_content,
                            task.get("status", "pending"),
                            task.get("priority"),
                            task.get("requested_on") or received_on,
                            task.get("expected_delivery_date"),
                            task_group_id,
                            msg_id,
                            result.get("ai_log_id"),
                            _now(),
                            _now(),
                        ),
                    )

                c.execute(
                    """
                    UPDATE messages
                    SET status = 'done',
                        processed_at = ?,
                        updated_at = ?,
                        last_error = NULL
                    WHERE id = ?
                    """,
                    (_now(), _now(), msg_id),
                )
                conn.commit()
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                conn.rollback()
                c.execute(
                    """
                    UPDATE messages
                    SET status = 'error',
                        error_count = error_count + 1,
                        last_error = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (str(exc), _now(), msg_id),
                )
                conn.commit()
                logger.error("Error processing message %s: %s", msg_id, exc)
