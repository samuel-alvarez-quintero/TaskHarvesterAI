import logging
import os
import sys

from dotenv import load_dotenv
from app.db_schema import get_conn, init_db
from app.logging_config import setup_logging
from app.imap_client import fetch_unseen
from app.processor import process

load_dotenv()
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def list_all_tasks() -> None:
    conn = get_conn()
    c = conn.cursor()

    for row in c.execute("SELECT id, content, priority, status FROM tasks"):
        print(f"ID: {row[0]}, Content: {row[1]}, Priority: {row[2]}, Status: {row[3]}")

    conn.close()


def list_pending_tasks() -> None:
    conn = get_conn()
    c = conn.cursor()

    for row in c.execute(
        "SELECT id, content, priority FROM tasks WHERE status = 'pending'"
    ):
        print(f"ID: {row[0]}, Content: {row[1]}, Priority: {row[2]}")

    conn.close()


def list_completed_tasks() -> None:
    conn = get_conn()
    c = conn.cursor()

    for row in c.execute(
        "SELECT id, content, priority FROM tasks WHERE status = 'completed'"
    ):
        print(f"ID: {row[0]}, Content: {row[1]}, Priority: {row[2]}")

    conn.close()


def complete(task_id: int) -> None:
    conn = get_conn()
    c = conn.cursor()

    c.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def fetch_unseen_emails() -> None:
    init_db()
    fetch_unseen()


def process_emails() -> None:
    process()


def main() -> None:
    COMMAND_LIST_TEXT = """'list-all' to list all tasks \n'list-pending' to list pending tasks \n'list-completed' to list completed tasks \n'complete <id>' to complete a task. \n'fetch-unseen' to fetch unseen emails \n'process' to process unprocessed emails"""

    if len(sys.argv) < 2:
        logger.error(f"""\nPlease provide a command: \n{COMMAND_LIST_TEXT}""")
        sys.exit(1)

    cmd = sys.argv[1]

    match cmd:
        case "list-all":
            list_all_tasks()
        case "list-pending":
            list_pending_tasks()
        case "list-completed":
            list_completed_tasks()
        case "complete":
            if len(sys.argv) < 3:
                logger.error("Please provide a task ID to complete.")
                sys.exit(1)

            try:
                task_id = int(sys.argv[2])
                complete(task_id)
            except ValueError:
                logger.error("Invalid task ID. Please provide a numeric value.")
                sys.exit(1)
        case "fetch-unseen":
            fetch_unseen_emails()
        case "process":
            process_emails()
        case _:
            logger.error(f"""\nUnknown command. \n\nUse: \n{COMMAND_LIST_TEXT}""")


if __name__ == "__main__":
    main()
