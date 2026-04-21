# Functional and Non-Functional Requirements Status

## Status Legend
- **Implemented**: clearly present and usable in current code.
- **Partial**: scaffolded or incomplete.
- **Missing**: not found in current code path.

## Functional Requirements (FR)

### Email Ingestion
- **FR-01 multiple IMAP accounts**: Missing
- **FR-02 initial batch sync**: Partial
- **FR-03 deduplication by UID/message id**: Implemented
- **FR-04 periodic incremental sync**: Missing
- **FR-05 configurable polling interval**: Missing

### Pre-Persistence Filtering
- **FR-06 filter before persistence**: Missing
- **FR-07 configurable rules (sender/keywords/domain)**: Partial
- **FR-08 discard empty/useless messages early**: Partial
- **FR-09 whitelist**: Missing
- **FR-10 blacklist**: Missing
- **FR-11 max message size limit**: Missing

### Persistence and Queue
- **FR-12 persist messages as `pending`**: Implemented
- **FR-13 persist content/source/date/external id**: Implemented
- **FR-14 message lifecycle states**: Implemented
- **FR-15 batch processing with limits**: Implemented
- **FR-16 prioritize recent messages**: Partial
- **FR-17 retry failed processing**: Implemented
- **FR-18 terminal failure after repeated retries**: Partial

### Attachments and Normalization
- **FR-19 detect attachment MIME type**: Implemented
- **FR-20 extract text from PDF/images/DOCX**: Missing
- **FR-21 OCR for scanned PDFs**: Missing
- **FR-22 ignore irrelevant attachments**: Partial
- **FR-23 deduplicate attachments by hash**: Missing
- **FR-24 clean signatures/reply chains**: Partial
- **FR-25 truncate long text**: Partial
- **FR-26 unified processing text**: Implemented

### AI Processing
- **FR-27 send normalized text to AI**: Implemented
- **FR-28 extract actionable tasks**: Implemented
- **FR-29 enforce priority enum**: Partial
- **FR-30 valid JSON output contract**: Implemented
- **FR-31 schema validation of output**: Partial
- **FR-32 retry on AI error**: Partial
- **FR-33 fallback model chain (llama3 to qwen)**: Missing

### Task Persistence and CLI
- **FR-34 persist extracted tasks**: Implemented
- **FR-35 link task to source message**: Implemented
- **FR-36 maintain processing history**: Partial
- **FR-37 manual sync via CLI**: Implemented
- **FR-38 manual processing via CLI**: Implemented
- **FR-39 system status via CLI**: Implemented
- **FR-40 task listing via CLI**: Implemented
- **FR-41 task completion via CLI**: Implemented

### API and App
- **FR-42 task API endpoints**: Missing
- **FR-43 task visualization app**: Missing
- **FR-44 task editing**: Missing
- **FR-45 mark completed via API/app**: Missing
- **FR-46 future client/project management support**: Partial

### Dynamic Configuration and Prompt Personalization
- **FR-47 runtime configuration from DB (single workspace)**: Partial
- **FR-48 first-run setup seeds mailbox/provider defaults**: Implemented
- **FR-49 encrypted-at-rest secret storage**: Implemented
- **FR-50 per-mailbox provider configuration**: Partial
- **FR-51 per-mailbox prompt template for `extract_tasks` and `classify_message`**: Implemented
- **FR-52 editable prompt fields are limited to `instructions` and `language`**: Partial
- **FR-53 fixed prompt structure (`instructions`, `json_response`, `context`, `message`)**: Implemented

## Non-Functional Requirements (NFR)

### Performance and Scalability
- **RNF-01 bounded batch processing**: Implemented
- **RNF-02 controlled processing concurrency**: Implemented (single-worker execution)
- **RNF-03 controlled LLM concurrency**: Implemented (single-request flow)
- **RNF-04 handle large initial volume**: Partial
- **RNF-05 support data growth**: Partial
- **RNF-06 add workers safely**: Missing

### Availability, Security, and Maintainability
- **RNF-07 tolerate item-level failures**: Implemented
- **RNF-08 resume interrupted processing**: Partial
- **RNF-09 protect credentials through environment variables**: Implemented
- **RNF-10 avoid sensitive logging**: Partial
- **RNF-11 API authentication**: Missing
- **RNF-12 modular architecture**: Implemented
- **RNF-13 configure behavior without code changes**: Partial
- **RNF-14 local reproducibility**: Implemented
- **RNF-19 fail-fast for missing encryption key outside development**: Implemented
- **RNF-20 extensible schema for future configuration types**: Implemented

### Observability and Privacy
- **RNF-15 logs for ingest/process/errors**: Implemented
- **RNF-16 queue and timing observability**: Partial
- **RNF-17 local processing with Ollama**: Implemented
- **RNF-18 avoid sending sensitive data externally**: Partial

## Assumptions
- `docs/SRS.md` is treated as target requirement baseline.
- Source code is treated as implementation truth for status mapping.

## Questions to Confirm
- Should attachment extraction be mandatory for v1.0, or deferred to v1.1?
- Should v1.0 enforce strict schema validation with hard failure on malformed AI output?
- Should setup flow be delivered first as CLI wizard, web form, or API endpoint?
