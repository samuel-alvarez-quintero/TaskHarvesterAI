import argparse
import logging
import os

from dotenv import load_dotenv

from app.db.sqlite.database import get_conn, init_db
from app.imap_client import fetch_unseen
from app.logging_config import setup_logging
from app.processor import process

load_dotenv()
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def _print_summary(title: str, summary: dict[str, int]) -> None:
    print(title)
    for key, value in summary.items():
        print(f"  {key}: {value}")


def list_tasks(status: str | None = None, limit: int | None = None) -> None:
    query = "SELECT id, content, priority, status FROM tasks"
    params: list[object] = []

    if status and status != "all":
        query += " WHERE status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC, id DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(query, tuple(params))
        rows = c.fetchall()

    if not rows:
        print("No tasks found.")
        return

    for row in rows:
        print(f"ID: {row[0]}, Content: {row[1]}, Priority: {row[2]}, Status: {row[3]}")


def complete_task(task_id: int) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE tasks
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (task_id,),
        )
        conn.commit()
        return c.rowcount


def print_status() -> None:
    with get_conn() as conn:
        c = conn.cursor()

        c.execute(
            "SELECT status, COUNT(*) FROM messages GROUP BY status ORDER BY status"
        )
        message_rows = c.fetchall()

        c.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY status")
        task_rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM client")
        client_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM task_groups")
        task_group_count = c.fetchone()[0]

    print("Messages:")
    for status, count in message_rows:
        print(f"  {status}: {count}")

    print("Tasks:")
    for status, count in task_rows:
        print(f"  {status}: {count}")

    print(f"Clients: {client_count}")
    print(f"Task groups: {task_group_count}")


def run_fetch(limit: int | None) -> int:
    summary = fetch_unseen(limit=limit)
    _print_summary("Fetch summary", summary)
    return 0


def run_process(
    limit: int | None,
    retry_errors: bool,
    retry_processing_after_minutes: int | None,
) -> int:
    summary = process(
        limit=limit,
        retry_errors=retry_errors,
        retry_processing_after_minutes=retry_processing_after_minutes,
    )
    _print_summary("Process summary", summary)
    return 1 if summary["errors"] > 0 else 0


def run_pipeline(args: argparse.Namespace) -> int:
    fetch_summary = fetch_unseen(limit=args.fetch_limit)
    process_summary = process(
        limit=args.process_limit,
        retry_errors=args.retry_errors,
        retry_processing_after_minutes=args.retry_processing_after_minutes,
    )
    _print_summary("Fetch summary", fetch_summary)
    _print_summary("Process summary", process_summary)
    return 1 if process_summary["errors"] > 0 else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taskh",
        description="CLI for fetching emails and extracting tasks into SQLite.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch unseen emails")
    fetch_parser.add_argument("--limit", type=int, default=None)

    process_parser = subparsers.add_parser("process", help="Process queued messages")
    process_parser.add_argument("--limit", type=int, default=None)
    process_parser.add_argument("--retry-errors", action="store_true")
    process_parser.add_argument("--retry-processing-after-minutes", type=int, default=None)

    run_parser = subparsers.add_parser("run", help="Fetch and process in one bounded run")
    run_parser.add_argument("--fetch-limit", type=int, default=None)
    run_parser.add_argument("--process-limit", type=int, default=None)
    run_parser.add_argument("--retry-errors", action="store_true")
    run_parser.add_argument("--retry-processing-after-minutes", type=int, default=None)

    subparsers.add_parser("status", help="Show DB processing summary")

    tasks_parser = subparsers.add_parser("tasks", help="Task operations")
    task_subparsers = tasks_parser.add_subparsers(dest="tasks_command", required=True)

    list_parser = task_subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "--status",
        default="all",
        choices=["all", "pending", "in_progress", "completed", "cancelled"],
    )
    list_parser.add_argument("--limit", type=int, default=None)

    complete_parser = task_subparsers.add_parser("complete", help="Mark a task as completed")
    complete_parser.add_argument("task_id", type=int)

    subparsers.add_parser("init-db", help="Initialize the database schema")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    init_db()

    exit_code = 0

    match args.command:
        case "fetch":
            exit_code = run_fetch(limit=args.limit)
        case "process":
            exit_code = run_process(
                limit=args.limit,
                retry_errors=args.retry_errors,
                retry_processing_after_minutes=args.retry_processing_after_minutes,
            )
        case "run":
            exit_code = run_pipeline(args)
        case "status":
            print_status()
        case "tasks":
            match args.tasks_command:
                case "list":
                    list_tasks(status=args.status, limit=args.limit)
                case "complete":
                    updated = complete_task(args.task_id)
                    if updated == 0:
                        logger.error("Task ID %s was not found.", args.task_id)
                        exit_code = 1
                    else:
                        print(f"Task {args.task_id} marked as completed.")
                case _:
                    parser.error("Unknown tasks command")
        case "init-db":
            print("Database initialized.")
        case _:
            parser.error("Unknown command")

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
