# Project Guidelines

## Architecture
- Keep the current pipeline boundaries clear:
  - IMAP ingestion in `src/app/imap_client.py`
  - message/task persistence in `src/app/db/`
  - LLM task extraction in `src/app/llm_clients/`
  - batch orchestration in `src/app/processor.py`
  - operator CLI in `src/cli/`
- Preserve the existing flow: fetch unseen emails -> store raw messages -> process unprocessed messages -> extract tasks -> persist tasks -> mark message as processed.
- Prefer thin entry scripts in `scripts/` and keep business logic in `src/app/` modules.

## Build and Test
- Install dependencies with `poetry install`.
- Fetch unseen emails with `poetry run taskh fetch`.
- Process queued messages with `poetry run taskh process`.
- Use the CLI manually:
  - `poetry run taskh tasks list`
  - `poetry run taskh tasks complete <task_id>`
- There is currently no formal test suite or lint config in this repository. Do not invent test commands; if adding tests or tooling, document the exact command in README.

## Conventions
- Use the existing SQLite access pattern (`get_conn()`, direct parameterized SQL) unless a migration is explicitly requested. Use Alembic for schema migrations.
- Keep external integration behavior local-first:
  - environment variables from `.env`
  - LLM endpoints and models from environment variables (support for Ollama, OpenAI, etc.)
- Keep prompts and user-facing extraction behavior in Spanish to match current implementation and project docs.
- Favor small, incremental changes over broad refactors in core processing files (`src/app/imap_client.py`, `src/app/processor.py`).
- When handling failures in processing, avoid crashing the whole batch; preserve per-message isolation.
- Use strict typing for all classes, methods, properties, and functions. Annotate return types, parameters, and instance variables to ensure type safety and pass mypy checks.

## Documentation
- For product intent and constraints, see `README.md`.
- For workflow details, see `docs/flowchart.md`.
- For requirements, see `docs/SRS.md`.
- For commit message format, follow `.github/instructions/commits.instructions.md`.
