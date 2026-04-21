# Entity-Relationship Diagram

## Full Schema ERD

```mermaid
erDiagram
    messages {
        int id PK
        string source
        string account_id
        string mailbox
        string imap_uid
        string external_id
        string message_id
        string thread_key
        string from_email
        string subject
        datetime received_on
        string status
        int error_count
        datetime processed_at
    }

    raw_messages {
        int id PK
        int message_row_id FK
        bytes raw_rfc822
        text raw_headers
    }

    message_addresses {
        int id PK
        int message_row_id FK
        string address_role
        string email_address
    }

    message_attachments {
        int id PK
        int message_row_id FK
        string filename
        string mime_type
        string extraction_status
    }

    message_filters {
        int id PK
        int message_row_id FK
        string filter_name
        int filter_value
    }

    ai_log {
        int id PK
        int message_row_id FK
        string provider
        string model
        string operation
        string status
    }

    client {
        int id PK
        string name
        string name_slug
        string status
    }

    task_groups {
        int id PK
        int client_id FK
        int source_message_id FK
        string name
        string status
        string priority
    }

    tasks {
        int id PK
        int task_group_id FK
        int source_message_id FK
        int ai_log_id FK
        text content
        string status
        string priority
    }

    messages ||--o| raw_messages : one_to_one
    messages ||--o{ message_addresses : one_to_many
    messages ||--o{ message_attachments : one_to_many
    messages ||--o{ message_filters : one_to_many
    messages ||--o{ ai_log : one_to_many
    messages ||--o{ task_groups : optional_source_link
    messages ||--o{ tasks : required_source_link

    client ||--o{ task_groups : optional_client_link
    task_groups ||--o{ tasks : optional_group_link
    ai_log ||--o{ tasks : optional_ai_provenance
```

## Minimal Core ERD

```mermaid
erDiagram
    messages {
        int id PK
        string external_id
        string from_email
        string subject
        string status
        datetime received_on
    }

    client {
        int id PK
        string name
        string name_slug
        string status
    }

    task_groups {
        int id PK
        int client_id FK
        int source_message_id FK
        string name
        string status
        string priority
    }

    tasks {
        int id PK
        int task_group_id FK
        int source_message_id FK
        text content
        string status
        string priority
    }

    messages ||--o{ task_groups : optional_source_link
    messages ||--o{ tasks : required_source_link
    client ||--o{ task_groups : optional_client_link
    task_groups ||--o{ tasks : optional_group_link
```

## Assumptions
- Optional links correspond to nullable foreign keys in current SQLAlchemy models.
- Diagram captures schema-level truth, not future intended constraints.
