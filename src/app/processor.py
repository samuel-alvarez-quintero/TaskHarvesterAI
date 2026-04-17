import json
import logging
from typing import Any
from datetime import datetime

from app.db.database import session_scope
from app.llm import extract_tasks
from app.repository import (
    ClientRepository,
    MessageRepository,
    TaskGroupRepository,
    TaskRepository,
)

"""Processor module to handle message processing and task extraction logic."""

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now().astimezone()


def str_to_datetime(date_str: Any) -> datetime | None:
    if isinstance(date_str, str):
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S%z")
    else:
        return None


def process(
    limit: int | None = None,
    retry_errors: bool = False,
    retry_processing_after_minutes: int | None = None,
) -> dict[str, int]:
    """Process unprocessed messages, extract tasks, and update the database accordingly."""

    # Initialize summary metrics
    summary = {
        "selected": 0,
        "processed": 0,
        "skipped_empty": 0,
        "no_result": 0,
        "no_tasks": 0,
        "clients_created": 0,
        "task_groups_created": 0,
        "tasks_created": 0,
        "tasks_updated": 0,
        "errors": 0,
    }

    status_filters = ["pending"]
    if retry_errors:
        status_filters.append("error")

    with session_scope() as session:
        # Fetch unprocessed messages based on filters and limits
        with MessageRepository(session) as message_repo:
            messages = message_repo.get_unprocessed_messages(
                limit=limit,
                status_filters=status_filters,
                retry_processing_after_minutes=retry_processing_after_minutes,
            )
            summary["selected"] = len(messages)

            for message in messages:
                msg_id = message["id"]
                body_text_clean = message.get("body_text_clean")
                body_text_raw = message.get("body_text_raw")
                body_html_raw = message.get("body_html_raw")
                from_email = message.get("from_email")
                subject = message.get("subject")

                message_text = body_text_clean or body_text_raw or body_html_raw or ""
                sender = from_email or ""
                subject = subject or ""

                # If message text is empty, skip processing and mark as done
                if len(message_text) == 0:
                    logger.info("Skipping message ID %s due to empty content", msg_id)
                    message_repo.update_message_status(
                        message_id=msg_id,
                        status="done",
                        processed_at=_now(),
                        last_error=None,
                    )
                    summary["skipped_empty"] += 1
                    summary["processed"] += 1
                    continue

                try:
                    message_repo.update_message_status(
                        message_id=msg_id,
                        status="processing",
                        last_error=None,
                    )

                    # Call the LLM extraction function to get tasks from the message
                    result = extract_tasks(msg_id, message_text, sender, subject, session=session)

                    # If no result is returned, mark the message as error and continue
                    if not result:
                        logger.warning("No result returned for message ID: %s", msg_id)
                        message_repo.update_message_status(
                            message_id=msg_id,
                            status="error",
                            last_error="No result returned by LLM extraction.",
                        )
                        summary["no_result"] += 1
                        summary["errors"] += 1
                        continue

                    response = result.get("response", "")

                    # If response is empty, mark the message as done and continue
                    if len(response) == 0:
                        logger.info("No tasks extracted for message ID: %s", msg_id)
                        message_repo.update_message_status(
                            message_id=msg_id,
                            status="done",
                            processed_at=_now(),
                            last_error=None,
                        )
                        summary["no_tasks"] += 1
                        summary["processed"] += 1
                        continue

                    data_task = json.loads(response)

                    # Log the extracted tasks for debugging and traceability
                    logger.info(
                        "Extracted tasks for message ID: %s | From: %s | Subject: %s",
                        msg_id,
                        sender,
                        subject,
                    )

                    # Create or update client based on the extracted data
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

                        with ClientRepository(session) as client_repo:
                            client = client_repo.create_or_update_client(
                                name=client_info.get("name"),
                                name_slug=client_info.get("name_slug"),
                                primary_email=primary_email,
                                primary_phone=primary_phone,
                            )
                            client_id = client["id"]
                            summary["clients_created"] += 1

                    # Create or update task group based on the extracted data
                    task_group_info = data_task.get("task_group_info", {})
                    task_group_id = None
                    if task_group_info.get("name") and task_group_info.get("name_slug"):
                        with TaskGroupRepository(session) as task_group_repo:
                            requested_on = str_to_datetime(
                                task_group_info.get("requested_on")
                            )
                            received_on = str_to_datetime(
                                task_group_info.get("received_on")
                            )
                            expected_delivery_date = str_to_datetime(
                                task_group_info.get("expected_delivery_date")
                            )

                            task_group = task_group_repo.create_or_update_task_group(
                                name=task_group_info.get("name"),
                                name_slug=task_group_info.get("name_slug"),
                                client_id=client_id,
                                status=task_group_info.get("status", "pending"),
                                requested_on=requested_on or received_on,
                                expected_delivery_date=expected_delivery_date,
                                priority=task_group_info.get("priority"),
                            )
                            task_group_id = task_group["id"]
                            summary["task_groups_created"] += 1

                    # Create or update tasks based on the extracted data
                    with TaskRepository(session) as task_repo:
                        for task in data_task.get("tasks", []):
                            task_content = task.get("content")
                            if not task_content:
                                continue

                            task_obj = task_repo.create_task(
                                content=task_content,
                                source_message_id=msg_id,
                                task_group_id=task_group_id,
                                status=task.get("status", "pending"),
                                priority=task.get("priority"),
                                requested_on=str_to_datetime(task.get("requested_on"))
                                or str_to_datetime(message.get("received_on")),
                                expected_delivery_date=(
                                    str_to_datetime(task.get("expected_delivery_date"))
                                    if task.get("expected_delivery_date")
                                    else None
                                ),
                                ai_log_id=result.get("ai_log_id"),
                            )
                            if task_obj.get("id"):
                                summary["tasks_created"] += 1
                            else:
                                summary["tasks_updated"] += 1

                    # If we reach this point without exceptions, mark the message as done
                    message_repo.update_message_status(
                        message_id=msg_id,
                        status="done",
                        processed_at=_now(),
                        last_error=None,
                    )
                    summary["processed"] += 1
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    message_repo.update_message_status(
                        message_id=msg_id,
                        status="error",
                        last_error=str(exc),
                    )
                    summary["errors"] += 1
                    logger.error("Error processing message %s: %s", msg_id, exc)

    return summary
