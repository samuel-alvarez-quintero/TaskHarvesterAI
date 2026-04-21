# Sequence Diagrams

## 1) `taskh fetch` (with failure branches)

```mermaid
sequenceDiagram
    participant User
    participant CLI as CliMain
    participant Fetch as fetch_unseen
    participant IMAP as ImapServer
    participant Repo as MessageRepository
    participant DB as SQLite

    User->>CLI: taskh fetch --limit N
    CLI->>Fetch: fetch_unseen(limit)

    alt missing IMAP credentials
        Fetch-->>CLI: summary with zero selected
        CLI-->>User: warning + summary
    else credentials present
        Fetch->>IMAP: login + select mailbox
        alt auth/select failure
            Fetch-->>CLI: summary with fetch errors
            CLI-->>User: error summary
        else auth/select success
            Fetch->>IMAP: search UNSEEN
            alt search not OK
                Fetch-->>CLI: summary with fetch errors
                CLI-->>User: error summary
            else search OK
                loop each candidate message
                    Fetch->>IMAP: fetch UID RFC822 FLAGS INTERNALDATE
                    IMAP-->>Fetch: payload
                    Fetch->>Repo: dedupe check
                    Repo->>DB: select
                    DB-->>Repo: existing or none
                    alt duplicate
                        Fetch-->>Fetch: increment duplicates
                    else new message
                        Fetch->>Repo: create message status=pending
                        Repo->>DB: insert
                    end
                end
                Fetch->>IMAP: logout
                Fetch-->>CLI: summary
                CLI-->>User: fetch summary
            end
        end
    end
```

## 2) `taskh filter`

```mermaid
sequenceDiagram
    participant User
    participant CLI as CliMain
    participant FilterSvc as filter_messages
    participant MsgRepo as MessageRepository
    participant LLMFlow as classify_message
    participant LLM as LLMProvider
    participant FilterRepo as MessageFilterRepository
    participant DB as SQLite

    User->>CLI: taskh filter --spam --phishing --malware --important
    CLI->>FilterSvc: filter_messages(filter_keys, limit)
    FilterSvc->>MsgRepo: get_messages_for_filtering(limit)
    MsgRepo->>DB: select candidate messages
    DB-->>MsgRepo: rows

    loop each message
        FilterSvc->>LLMFlow: classify_message(msg_id, sender, subject, text)
        LLMFlow->>LLM: generate(classification prompt)
        LLM-->>LLMFlow: response
        alt parsed classification
            LLMFlow->>FilterRepo: create_or_update_filter(...)
            FilterRepo->>DB: upsert message_filters
        else parse/provider error
            FilterSvc-->>FilterSvc: increment errors
        end
    end

    FilterSvc-->>CLI: filter summary
    CLI-->>User: filter summary
```

## 3) `taskh process`

```mermaid
sequenceDiagram
    participant User
    participant CLI as CliMain
    participant Proc as process
    participant MsgRepo as MessageRepository
    participant Extract as extract_tasks
    participant LLM as LLMProvider
    participant ClientRepo as ClientRepository
    participant GroupRepo as TaskGroupRepository
    participant TaskRepo as TaskRepository
    participant DB as SQLite

    User->>CLI: taskh process --limit N
    CLI->>Proc: process(limit, retry flags)
    Proc->>MsgRepo: get_unprocessed_messages(...)
    MsgRepo->>DB: select pending/error
    DB-->>MsgRepo: messages

    loop each selected message
        Proc->>MsgRepo: update status=processing
        MsgRepo->>DB: update messages
        Proc->>Extract: extract_tasks(msg_id, text, sender, subject)
        Extract->>LLM: generate(extraction prompt)
        LLM-->>Extract: response payload

        alt no result or parse exception
            Proc->>MsgRepo: update status=error + last_error
            MsgRepo->>DB: update messages
        else valid extracted JSON
            Proc->>ClientRepo: create_or_update_client
            ClientRepo->>DB: upsert client
            Proc->>GroupRepo: create_or_update_task_group
            GroupRepo->>DB: upsert task_groups
            Proc->>TaskRepo: create_task per extracted task
            TaskRepo->>DB: insert tasks
            Proc->>MsgRepo: update status=done + processed_at
            MsgRepo->>DB: update messages
        end
    end

    Proc-->>CLI: process summary
    CLI-->>User: process summary
```

## 4) `taskh run`

```mermaid
sequenceDiagram
    participant User
    participant CLI as CliMain
    participant Fetch as fetch_unseen
    participant Proc as process

    User->>CLI: taskh run --fetch-limit X --process-limit Y
    CLI->>Fetch: fetch_unseen(limit=X)
    Fetch-->>CLI: fetch summary
    CLI->>Proc: process(limit=Y, retry flags)
    Proc-->>CLI: process summary
    CLI-->>User: print summaries and exit code
```

## Assumptions
- Sequence diagrams reflect current implementation behavior and CLI/module interactions.
- AI logging internals are omitted to keep diagrams readable.
