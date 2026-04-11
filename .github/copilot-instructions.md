# Project Guidelines

## Architecture
- Keep the current pipeline boundaries clear:
  - IMAP ingestion in `app/imap_client.py`
  - message/task persistence in `app/db.py`
  - LLM task extraction in `app/ollama_client.py`
  - batch orchestration in `app/processor.py`
  - operator CLI in `app/cli.py`
- Preserve the existing flow: fetch unseen emails -> store raw messages -> process unprocessed messages -> extract tasks -> persist tasks -> mark message as processed.
- Prefer thin entry scripts in `scripts/` and keep business logic in `app/` modules.

## Build and Test
- Install dependencies with `pip install -r requirements.txt`.
- Initialize DB and fetch unseen emails with `python scripts/fetch_emails.py`.
- Process queued messages with `python scripts/process_messages.py`.
- Use the CLI manually:
  - `python -m app.cli list`
  - `python -m app.cli done <task_id>`
- There is currently no formal test suite or lint config in this repository. Do not invent test commands; if adding tests or tooling, document the exact command in README.

## Conventions
- Use the existing SQLite access pattern (`get_conn()`, direct parameterized SQL) unless a migration is explicitly requested.
- Keep external integration behavior local-first:
  - environment variables from `.env`
  - Ollama endpoint from `OLLAMA_URL`
  - model from `MODEL`
- Keep prompts and user-facing extraction behavior in Spanish to match current implementation and project docs.
- Favor small, incremental changes over broad refactors in core processing files (`app/imap_client.py`, `app/processor.py`).
- When handling failures in processing, avoid crashing the whole batch; preserve per-message isolation.

## Documentation
- For product intent and constraints, see `README.md`.
- For workflow details, see `docs/flowchart.md`.
- For requirements, see `docs/SRS.md`.
- For commit message format, follow `.github/instructions/commits.instructions.md`.
