import argparse
import logging
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from app.db.sqlite.database import get_conn, init_db
from app.imap_client import fetch_unseen
from app.logging_config import setup_logging
from app.message_filter import FILTER_DEFINITIONS, filter_messages
from app.processor import process

load_dotenv()
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
console = Console()


def _print_summary(title: str, summary: dict[str, int]) -> None:
    table = Table(title=title)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", justify="right", style="bold")
    for key, value in summary.items():
        table.add_row(key.replace("_", " "), str(value))
    console.print(table)


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
        console.print("[yellow]No tasks found.[/yellow]")
        return

    table = Table(title="Tasks")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", style="green", no_wrap=True)
    table.add_column("Priority", style="magenta", no_wrap=True)
    table.add_column("Content", overflow="fold")

    for row in rows:
        task_id, content, priority, task_status = row
        normalized_content = (content or "").replace("\n", " ").strip()
        table.add_row(
            str(task_id),
            task_status or "",
            priority or "",
            normalized_content,
        )

    console.print(table)


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

    messages_table = Table(title="Messages")
    messages_table.add_column("Status", style="cyan", no_wrap=True)
    messages_table.add_column("Count", justify="right", style="bold")
    for status, count in message_rows:
        messages_table.add_row(status, str(count))

    tasks_table = Table(title="Tasks")
    tasks_table.add_column("Status", style="cyan", no_wrap=True)
    tasks_table.add_column("Count", justify="right", style="bold")
    for status, count in task_rows:
        tasks_table.add_row(status, str(count))

    overview_table = Table(title="Overview")
    overview_table.add_column("Entity", style="cyan", no_wrap=True)
    overview_table.add_column("Count", justify="right", style="bold")
    overview_table.add_row("Clients", str(client_count))
    overview_table.add_row("Task groups", str(task_group_count))

    console.print(messages_table)
    console.print(tasks_table)
    console.print(overview_table)


def _get_selected_filters(args: argparse.Namespace) -> list[str]:
    selected_filters = [
        key for key in FILTER_DEFINITIONS if getattr(args, key, False)
    ]
    return selected_filters or list(FILTER_DEFINITIONS)


def run_fetch(
    limit: int | None,
    filter_enabled: bool,
    filter_keys: list[str] | None = None,
) -> int:
    summary = fetch_unseen(
        limit=limit,
        filter_messages=filter_enabled,
        filter_keys=filter_keys,
    )
    _print_summary("Fetch summary", summary)
    return 0


def run_filter(filter_keys: list[str] | None, limit: int | None) -> int:
    summary = filter_messages(filter_keys=filter_keys, limit=limit)
    _print_summary("Filter summary", summary)
    return 1 if summary["errors"] > 0 else 0


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
    fetch_parser.add_argument("--filter", action="store_true", help="Run AI filters on newly fetched emails")
    for filter_name, filter_info in FILTER_DEFINITIONS.items():
        fetch_parser.add_argument(
            f"--{filter_name}",
            action="store_true",
            help=filter_info["description"],
        )

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

    filter_parser = subparsers.add_parser("filter", help="Run AI filters on existing messages")
    filter_parser.add_argument("--limit", type=int, default=None)
    for filter_name, filter_info in FILTER_DEFINITIONS.items():
        filter_parser.add_argument(
            f"--{filter_name}",
            action="store_true",
            help=filter_info["description"],
        )

    subparsers.add_parser("init-db", help="Initialize the database schema")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    init_db()

    exit_code = 0

    match args.command:
        case "fetch":
            filter_keys = _get_selected_filters(args) if args.filter else None
            exit_code = run_fetch(
                limit=args.limit,
                filter_enabled=args.filter,
                filter_keys=filter_keys,
            )
        case "process":
            exit_code = run_process(
                limit=args.limit,
                retry_errors=args.retry_errors,
                retry_processing_after_minutes=args.retry_processing_after_minutes,
            )
        case "filter":
            exit_code = run_filter(
                filter_keys=_get_selected_filters(args),
                limit=args.limit,
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
                        console.print(
                            f"[green]Task {args.task_id} marked as completed.[/green]"
                        )
                case _:
                    parser.error("Unknown tasks command")
        case "init-db":
            console.print("[green]Database initialized.[/green]")
        case _:
            parser.error("Unknown command")

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
