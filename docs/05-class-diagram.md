# Class Diagram

## Current Structure (module-oriented)

```mermaid
classDiagram
    class CliMain {
        +main()
        +build_parser()
        +run_fetch()
        +run_filter()
        +run_process()
        +run_pipeline()
    }

    class ImapClientModule {
        +fetch_unseen(limit, filter_messages, filter_keys)
    }

    class MessageFilterModule {
        +filter_messages(filter_keys, limit)
        +classify_message(msg_id, sender, subject, message_text, filter_keys)
    }

    class ProcessorModule {
        +process(limit, retry_errors, retry_processing_after_minutes)
    }

    class LlmModule {
        +get_llm()
        +extract_tasks(msg_id, msg_content, sender, subject, session)
    }

    class LLMClientInterface {
        <<interface>>
        +generate(prompt, msg_id, operation, session)
    }

    class OllamaClient
    class OpenAIClient

    class MessageRepository
    class TaskRepository
    class TaskGroupRepository
    class ClientRepository
    class MessageFilterRepository
    class AiLogRepository

    CliMain --> ImapClientModule : invokes
    CliMain --> MessageFilterModule : invokes
    CliMain --> ProcessorModule : invokes

    ProcessorModule --> LlmModule : uses
    MessageFilterModule --> LlmModule : uses
    LlmModule --> LLMClientInterface : dispatches
    LLMClientInterface <|.. OllamaClient
    LLMClientInterface <|.. OpenAIClient

    ImapClientModule --> MessageRepository : writes
    ProcessorModule --> MessageRepository : updates
    ProcessorModule --> TaskRepository : writes
    ProcessorModule --> TaskGroupRepository : upserts
    ProcessorModule --> ClientRepository : upserts
```

## Proposed Refactor Target (service-oriented)

```mermaid
classDiagram
    class ServicePipelineRunner {
        +run(fetch_opts, process_opts)
    }

    class ServiceIngestion {
        +fetch_new(limit)
    }

    class ServiceMessageClassification {
        +classify(message_id)
    }

    class ServiceTaskExtraction {
        +extract(message_id)
    }

    class ServiceAttachmentExtraction {
        +extract_text(message_id)
    }

    class ServiceMessageProcessing {
        +process_pending(limit, retry_policy)
    }

    class MediaSourceAdapter {
        <<abstract>>
        +fetch_items(limit)
        +normalize_item(raw_item)
    }

    class AdapterImap
    class AdapterFutureChannel

    class ServiceLLMGateway {
        +classify(prompt_ctx)
        +extract_tasks(prompt_ctx)
    }

    class RepositoryUnitOfWork {
        +session_scope()
    }

    ServicePipelineRunner --> ServiceIngestion
    ServicePipelineRunner --> ServiceMessageProcessing

    ServiceIngestion --> MediaSourceAdapter
    MediaSourceAdapter <|-- AdapterImap
    MediaSourceAdapter <|-- AdapterFutureChannel

    ServiceMessageProcessing --> ServiceAttachmentExtraction
    ServiceMessageProcessing --> ServiceMessageClassification
    ServiceMessageProcessing --> ServiceTaskExtraction

    ServiceMessageClassification --> ServiceLLMGateway
    ServiceTaskExtraction --> ServiceLLMGateway

    ServiceIngestion --> RepositoryUnitOfWork
    ServiceMessageProcessing --> RepositoryUnitOfWork
```

## Assumptions
- Current diagram reflects actual module boundaries, not a strict object-oriented domain model.
- Proposed diagram is incremental and designed to preserve current repository and model assets.
