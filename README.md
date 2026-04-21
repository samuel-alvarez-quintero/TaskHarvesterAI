# task-harvester-ai

`task-harvester-ai` is a local, CLI-driven pipeline that ingests unread emails from IMAP inboxes and converts message content into structured tasks using an LLM.

## What it does today

- Fetches unread emails from IMAP (`UNSEEN`) and stores them in SQLite.
- Persists normalized message data:
  - core message metadata
  - raw message payload
  - sender/recipient addresses
  - attachment metadata
- Optionally classifies messages with AI filters (spam/phishing/malware/important).
- Processes pending messages and extracts structured tasks via LLM.
- Stores extracted tasks grouped by client and task group.
- Provides CLI commands for fetch/process/filter/status/tasks operations.

## Current maturity

This project is in an early production-hardening phase:

- Core ingestion and extraction workflow is implemented.
- Data model is richer than current feature surface (some fields/features are scaffolded but not fully used yet).
- Documentation and implementation are not yet fully aligned.

## Tech stack

- Python 3.13
- Poetry
- SQLAlchemy + SQLite
- IMAP (`imaplib`)
- LLM providers:
  - Ollama (`/api/generate`)
  - OpenAI-compatible (`/v1/responses`)
- Rich logging output

## Project structure (high level)

- `src/cli/main.py` - CLI entrypoint (`taskh`)
- `src/app/imap_client.py` - IMAP fetch + message persistence
- `src/app/message_filter.py` - AI-based filtering
- `src/app/processor.py` - pending message processing + task persistence
- `src/app/llm.py` / `src/app/llm_clients/` - LLM provider abstraction
- `src/app/db/models/` - SQLAlchemy models
- `src/app/repository/` - data access layer

## Documentation set

- [Audit Summary](docs/01-audit-summary.md)
- [Functional and Non-Functional Requirements](docs/02-requirements.md)
- [Core Operation Flowcharts](docs/03-flowcharts.md)
- [Entity-Relationship Diagram](docs/04-entity-relationship-diagram.md)
- [Class Diagram](docs/05-class-diagram.md)
- [Sequence Diagrams](docs/06-sequence-diagrams.md)

## Installation

### Prerequisites

- Python 3.13
- Poetry
- IMAP credentials for the mailbox to ingest
- At least one configured LLM provider

### Setup

```bash
poetry install
```

Create a `.env` file (or export environment variables) with at least:

```bash
# DB
DATABASE_URL=sqlite:///data/tasks.db
# or DB_PATH=data/tasks.db
APP_SECRET_KEY=replace_with_strong_secret
APP_ENV=development

# IMAP
IMAP_HOST=imap.example.com
IMAP_USER=you@example.com
IMAP_PASS=your_password
IMAP_MAILBOX=INBOX
IMAP_PORT=993

# LLM
LLM_PROVIDER=ollama   # or openai

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# OpenAI-compatible
OPENAI_URL=https://api.openai.com
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your_key

# Logging
LOG_LEVEL=INFO
```

## Usage

### 1) Fetch unread emails into queue

```bash
poetry run taskh fetch
```

Optional flags:

- `--limit N`
- `--filter`
- `--spam --phishing --malware --important`

### 2) Process queued messages into tasks

```bash
poetry run taskh process
```

Optional flags:

- `--limit N`
- `--retry-errors`
- `--retry-processing-after-minutes N`

### 3) Run filter on existing messages

```bash
poetry run taskh filter --spam --phishing --malware --important
```

### 4) Combined pipeline

```bash
poetry run taskh run
```

### 5) Inspect status and tasks

```bash
poetry run taskh status
poetry run taskh tasks list
poetry run taskh tasks complete <task_id>
```

## Current limitations

- Attachment metadata is stored, but attachment text extraction/OCR flow is not fully active in processing.
- LLM output must be valid JSON; malformed responses can send messages to `error` state.
- Retry-related DB fields exist, but retry/attempt accounting is not fully leveraged across all failure paths.
- Current implementation focuses on email as the only ingestion channel.
- Dynamic workspace configuration is seeded from env on first run; interactive setup UI/API is not yet implemented.

## High-level roadmap

### v1.0 (first stable release)

- Align docs with actual CLI/runtime behavior.
- Harden processing reliability (error handling, retries, idempotency expectations).
- Complete attachment content extraction pipeline and integrate it into task extraction.
- Improve observability of extraction/filter outcomes.
- Stabilize acceptance criteria for "processed successfully" vs "needs manual review".

### v1.x (extensions)

- Add pluggable ingestion connectors for other communication sources:
  - chat platforms
  - video-call artifacts (transcripts/notes)
  - additional client-developer communication channels
- Evolve toward a class-oriented architecture with explicit service boundaries and abstract media adapters.

