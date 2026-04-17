-- SQL schema for the email task extraction and task management system.
-- 
--
-- This table stores the main metadata and normalized content for each email message processed by the system. 
-- It serves as the central hub linking to raw message content, addresses, attachments, AI processing logs, and any tasks extracted from the message.
CREATE TABLE
    IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        -- Source identity
        source TEXT NOT NULL DEFAULT 'email',
        account_id TEXT NOT NULL,
        mailbox TEXT NOT NULL DEFAULT 'INBOX',
        imap_uid TEXT NOT NULL,
        external_id TEXT,
        message_id TEXT,
        thread_key TEXT,
        -- Threading
        in_reply_to TEXT,
        references_header TEXT,
        -- Main participants
        from_name TEXT,
        from_email TEXT,
        subject TEXT,
        -- Dates
        received_on DATETIME NOT NULL,
        message_date DATETIME,
        imap_internal_date DATETIME,
        -- Operational metadata
        importance TEXT,
        flags_json TEXT,
        has_attachments INTEGER NOT NULL DEFAULT 0,
        attachment_count INTEGER NOT NULL DEFAULT 0,
        size_bytes INTEGER,
        -- Normalized content used by the app
        body_text_raw TEXT,
        body_html_raw TEXT,
        body_text_clean TEXT,
        body_hash TEXT,
        clean_body_hash TEXT,
        headers_json TEXT,
        -- Processing lifecycle
        status TEXT NOT NULL DEFAULT 'pending', -- pending|processing|done|error|ignored
        error_count INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        processed_at DATETIME,
        last_attempt_at DATETIME,
        -- Audit
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME
    );

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_account_mailbox_uid ON messages (account_id, mailbox, imap_uid);

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_message_id ON messages (message_id);

CREATE INDEX IF NOT EXISTS idx_messages_status_received_on ON messages (status, received_on);

CREATE INDEX IF NOT EXISTS idx_messages_from_email ON messages (from_email);

CREATE INDEX IF NOT EXISTS idx_messages_thread_key ON messages (thread_key);

--
--
-- This table stores the raw RFC822 content of each email message, along with the original headers in raw text form for reference or reprocessing. 
-- It is linked to the main messages table via a foreign key. 
-- This allows us to keep the raw data for reference or reprocessing while maintaining a clean separation from the normalized content used for task extraction and display.
CREATE TABLE
    IF NOT EXISTS raw_messages (
        id INTEGER PRIMARY KEY,
        message_row_id INTEGER NOT NULL,
        raw_rfc822 BLOB NOT NULL,
        raw_headers TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (message_row_id) REFERENCES messages (id) ON DELETE CASCADE
    );

CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_messages_message_row_id ON raw_messages (message_row_id);

--
--
-- This table captures all email addresses associated with a message, categorized by their role (e.g., from, to, cc, bcc, reply_to, sender). 
-- It allows for flexible querying of participants and supports messages with multiple recipients in each category. 
-- The display name is stored for convenience, but the email address is the primary field for lookups and associations.
CREATE TABLE
    IF NOT EXISTS message_addresses (
        id INTEGER PRIMARY KEY,
        message_row_id INTEGER NOT NULL,
        address_role TEXT NOT NULL, -- from|to|cc|bcc|reply_to|sender
        display_name TEXT,
        email_address TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (message_row_id) REFERENCES messages (id) ON DELETE CASCADE
    );

CREATE INDEX IF NOT EXISTS idx_message_addresses_message_row_id ON message_addresses (message_row_id);

CREATE INDEX IF NOT EXISTS idx_message_addresses_email_address ON message_addresses (email_address);

CREATE INDEX IF NOT EXISTS idx_message_addresses_role ON message_addresses (address_role);

--
--
-- This table stores classification and filter tags for each message. It is designed to support multiple filters and future extensions without altering the messages table.
CREATE TABLE
    IF NOT EXISTS message_filters (
        id INTEGER PRIMARY KEY,
        message_row_id INTEGER NOT NULL,
        filter_name TEXT NOT NULL,
        filter_value INTEGER NOT NULL DEFAULT 0,
        confidence REAL,
        reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (message_row_id) REFERENCES messages (id) ON DELETE CASCADE,
        UNIQUE (message_row_id, filter_name)
    );

CREATE INDEX IF NOT EXISTS idx_message_filters_message_row_id ON message_filters (message_row_id);

CREATE INDEX IF NOT EXISTS idx_message_filters_filter_name ON message_filters (filter_name);

--
--
-- This table stores metadata about each attachment associated with a message, including MIME information, size, and optional local storage paths. 
-- It also includes fields for tracking the status of content extraction (e.g., text extraction from PDFs or OCR results) and any errors encountered during processing. 
-- This allows the system to manage attachments effectively and link them to the relevant messages and tasks.
CREATE TABLE
    IF NOT EXISTS message_attachments (
        id INTEGER PRIMARY KEY,
        message_row_id INTEGER NOT NULL,
        -- MIME identity
        part_index INTEGER,
        content_id TEXT,
        filename TEXT,
        filename_normalized TEXT,
        mime_type TEXT NOT NULL,
        disposition TEXT,
        is_inline INTEGER NOT NULL DEFAULT 0,
        -- Size / dedupe
        size_bytes INTEGER,
        content_hash TEXT,
        -- Optional local storage
        storage_path TEXT,
        -- Extraction / OCR
        extracted_text TEXT,
        ocr_text TEXT,
        extraction_method TEXT, -- pdf|docx|ocr|none
        extraction_status TEXT NOT NULL DEFAULT 'pending', -- pending|processing|done|error|ignored
        error_message TEXT,
        -- Audit
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (message_row_id) REFERENCES messages (id) ON DELETE CASCADE
    );

CREATE INDEX IF NOT EXISTS idx_message_attachments_message_row_id ON message_attachments (message_row_id);

CREATE INDEX IF NOT EXISTS idx_message_attachments_content_hash ON message_attachments (content_hash);

CREATE INDEX IF NOT EXISTS idx_message_attachments_extraction_status ON message_attachments (extraction_status);

--
--
-- This table logs all interactions with AI services for each message, including the provider, model, operation type, prompts, responses, and execution status. 
-- It serves as an audit trail for AI processing and allows for analysis of performance, errors, and outcomes. 
-- Each log entry is linked to a specific message and can be referenced by extracted tasks through tasks.ai_log_id for traceability.
CREATE TABLE
    IF NOT EXISTS ai_log (
        id INTEGER PRIMARY KEY,
        -- LLM request context
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        operation TEXT NOT NULL DEFAULT 'extract_tasks', -- extract_tasks|ocr|classify|summarize|etc.
        -- Link to source message
        message_row_id INTEGER NOT NULL,
        -- Request / response
        prompt TEXT,
        response TEXT,
        request_payload TEXT, -- optional JSON payload actually sent
        response_payload TEXT, -- optional full JSON/raw response
        -- Execution status
        http_status TEXT,
        status TEXT NOT NULL DEFAULT 'pending', -- pending|completed|failed|timeout
        error_message TEXT,
        duration_ms INTEGER,
        -- Audit
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (message_row_id) REFERENCES messages (id) ON DELETE CASCADE
    );

CREATE INDEX IF NOT EXISTS idx_ai_log_message_row_id ON ai_log (message_row_id);

CREATE INDEX IF NOT EXISTS idx_ai_log_status ON ai_log (status);

CREATE INDEX IF NOT EXISTS idx_ai_log_provider_model ON ai_log (provider, model);

--
--
-- This table defines clients (e.g., companies or organizations) that tasks can be associated with. 
-- It includes core identity fields, optional business metadata, and audit timestamps.
CREATE TABLE
    IF NOT EXISTS client (
        id INTEGER PRIMARY KEY,
        -- Core identity
        name TEXT NOT NULL,
        name_slug TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', -- active|inactive|archived
        -- Optional business metadata
        primary_email TEXT,
        primary_phone TEXT,
        notes TEXT,
        -- Audit
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        UNIQUE (name_slug)
    );

CREATE INDEX IF NOT EXISTS idx_client_status ON client (status);

CREATE INDEX IF NOT EXISTS idx_client_primary_email ON client (primary_email);

--
--
-- This table defines task groups, which are collections of related tasks that can be tracked together. 
-- Each group has its own identity, status, priority, and optional association with a client and source message. 
-- This allows for organizing tasks into projects or categories and tracking their overall progress and context.
CREATE TABLE
    IF NOT EXISTS task_groups (
        id INTEGER PRIMARY KEY,
        -- Identity
        name TEXT NOT NULL,
        name_slug TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- pending|in_progress|completed|cancelled
        -- Dates
        requested_on DATETIME,
        expected_delivery_date DATETIME,
        completed_at DATETIME,
        -- Priority / ownership
        priority TEXT, -- low|medium|high
        client_id INTEGER,
        source_message_id INTEGER, -- the message that created or first identified this group
        -- Optional operator context
        notes TEXT,
        -- Audit
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (client_id) REFERENCES client (id) ON DELETE SET NULL,
        FOREIGN KEY (source_message_id) REFERENCES messages (id) ON DELETE SET NULL,
        UNIQUE (name_slug)
    );

CREATE INDEX IF NOT EXISTS idx_task_groups_client_id ON task_groups (client_id);

CREATE INDEX IF NOT EXISTS idx_task_groups_status ON task_groups (status);

CREATE INDEX IF NOT EXISTS idx_task_groups_priority ON task_groups (priority);

CREATE INDEX IF NOT EXISTS idx_task_groups_source_message_id ON task_groups (source_message_id);

--
--
-- This table defines individual tasks extracted from messages. Each task has content, status, priority, and optional associations with a task group, source message, and AI log entry. 
-- This allows for detailed tracking of each task's lifecycle, context, and any AI processing that contributed to its creation or updates.
CREATE TABLE
    IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        -- Task content
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- pending|in_progress|completed|cancelled
        priority TEXT, -- low|medium|high
        -- Dates
        requested_on DATETIME,
        expected_delivery_date DATETIME,
        completed_at DATETIME,
        -- Relationships
        task_group_id INTEGER,
        source_message_id INTEGER NOT NULL,
        ai_log_id INTEGER,
        -- Optional metadata
        extracted_confidence REAL, -- optional future scoring
        notes TEXT,
        -- Audit
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (task_group_id) REFERENCES task_groups (id) ON DELETE SET NULL,
        FOREIGN KEY (source_message_id) REFERENCES messages (id) ON DELETE CASCADE,
        FOREIGN KEY (ai_log_id) REFERENCES ai_log (id) ON DELETE SET NULL
    );

CREATE INDEX IF NOT EXISTS idx_tasks_task_group_id ON tasks (task_group_id);

CREATE INDEX IF NOT EXISTS idx_tasks_source_message_id ON tasks (source_message_id);

CREATE INDEX IF NOT EXISTS idx_tasks_ai_log_id ON tasks (ai_log_id);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);

CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);

CREATE INDEX IF NOT EXISTS idx_tasks_expected_delivery_date ON tasks (expected_delivery_date);