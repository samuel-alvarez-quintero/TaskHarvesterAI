# Core Operation Flowcharts

## 1) `taskh fetch`

```mermaid
flowchart TD
    startFetch[StartFetch] --> checkCreds{IMAPCredsSet}
    checkCreds -->|No| returnEmpty[ReturnSummaryNoFetch]
    checkCreds -->|Yes| connectImap[ConnectLoginSelectMailbox]
    connectImap --> searchUnseen[SearchUNSEEN]
    searchUnseen --> statusOk{SearchStatusOK}
    statusOk -->|No| returnSearchError[ReturnSummaryWithSearchError]
    statusOk -->|Yes| applyLimit[ApplyOptionalLimit]
    applyLimit --> loopMsgs{MoreMessages}

    loopMsgs -->|No| logout[LogoutIMAP]
    logout --> returnSummary[ReturnFetchSummary]

    loopMsgs -->|Yes| fetchMsg[FetchUIDRFC822FLAGSINTERNALDATE]
    fetchMsg --> fetchOk{FetchPayloadValid}
    fetchOk -->|No| countFetchError[IncFetchOrPayloadError]
    countFetchError --> loopMsgs

    fetchOk -->|Yes| parseEmail[ParseRFC822HeadersBodyAttachments]
    parseEmail --> dedupe{DuplicateByMessageIdOrUID}
    dedupe -->|Yes| countDup[IncDuplicates]
    countDup --> loopMsgs

    dedupe -->|No| insertMessage[InsertMessageStatusPending]
    insertMessage --> insertRaw[InsertRawMessage]
    insertRaw --> insertAddr[InsertAddresses]
    insertAddr --> insertAttach[InsertAttachmentMetadata]
    insertAttach --> incFetched[IncFetched]

    incFetched --> runFilter{FilterEnabled}
    runFilter -->|No| loopMsgs
    runFilter -->|Yes| classify[ClassifyMessageLLM]
    classify --> classOk{ClassificationParsed}
    classOk -->|No| incFilterErr[IncFilterErrors]
    incFilterErr --> loopMsgs
    classOk -->|Yes| saveFilters[SaveMessageFilters]
    saveFilters --> incFiltered[IncFiltered]
    incFiltered --> loopMsgs
```

## 2) `taskh filter`

```mermaid
flowchart TD
    startFilter[StartFilterCommand] --> loadMsgs[LoadMessagesForFiltering]
    loadMsgs --> loopFilter{MoreMessages}

    loopFilter -->|No| returnFilterSummary[ReturnFilterSummary]

    loopFilter -->|Yes| buildText[BuildMessageTextFromCleanRawHtml]
    buildText --> hasText{TextNotEmpty}
    hasText -->|No| incErrEmpty[IncErrors]
    incErrEmpty --> loopFilter

    hasText -->|Yes| buildPrompt[BuildFilterPromptBySelectedKeys]
    buildPrompt --> llmClassify[CallLLMClassifyMessage]
    llmClassify --> parsed{ParseClassificationJSON}
    parsed -->|No| incErrParse[IncErrors]
    incErrParse --> loopFilter

    parsed -->|Yes| saveFilterRows[PersistMessageFilterRows]
    saveFilterRows --> incFiltered[IncFiltered]
    incFiltered --> loopFilter
```

## 3) `taskh process`

```mermaid
flowchart TD
    startProcess[StartProcessCommand] --> selectMsgs[SelectMessagesByStatusAndRetryOptions]
    selectMsgs --> loopProc{MoreSelectedMessages}

    loopProc -->|No| returnProcSummary[ReturnProcessSummary]

    loopProc -->|Yes| buildInput[PickTextCleanRawHtmlAndMetadata]
    buildInput --> textEmpty{MessageTextEmpty}
    textEmpty -->|Yes| markDoneEmpty[MarkMessageDoneProcessedAtSet]
    markDoneEmpty --> incSkipped[IncSkippedEmptyAndProcessed]
    incSkipped --> loopProc

    textEmpty -->|No| markProcessing[MarkMessageProcessing]
    markProcessing --> callExtract[ExtractTasksViaLLM]
    callExtract --> gotResult{ResultExists}
    gotResult -->|No| markErrorNoResult[MarkMessageErrorNoResult]
    markErrorNoResult --> incNoResult[IncNoResultAndErrors]
    incNoResult --> loopProc

    gotResult -->|Yes| hasResponse{ResponseTextNotEmpty}
    hasResponse -->|No| markDoneNoTasks[MarkMessageDoneNoTasks]
    markDoneNoTasks --> incNoTasks[IncNoTasksAndProcessed]
    incNoTasks --> loopProc

    hasResponse -->|Yes| parseJson[ParseTaskJSON]
    parseJson --> parseOk{ParseAndDataValid}
    parseOk -->|No| markErrorParse[MarkMessageErrorWithException]
    markErrorParse --> incProcErr[IncErrors]
    incProcErr --> loopProc

    parseOk -->|Yes| upsertClient[CreateOrUpdateClientIfPresent]
    upsertClient --> upsertGroup[CreateOrUpdateTaskGroupIfPresent]
    upsertGroup --> persistTasks[CreateOrUpdateTasks]
    persistTasks --> markDone[MarkMessageDoneProcessedAtSet]
    markDone --> incProcessed[IncProcessed]
    incProcessed --> loopProc
```

## 4) `taskh run`

```mermaid
flowchart TD
    startRun[StartRunCommand] --> runFetch[ExecuteFetchWithFetchLimit]
    runFetch --> runProcess[ExecuteProcessWithProcessLimitAndRetryFlags]
    runProcess --> printSummaries[PrintFetchAndProcessSummaries]
    printSummaries --> exitCode{ProcessErrorsGreaterThanZero}
    exitCode -->|Yes| exit1[ExitCode1]
    exitCode -->|No| exit0[ExitCode0]
```

## Assumptions
- Flowcharts model current implementation paths only.
- Attachment metadata persistence is implemented; attachment text extraction is not yet in the active processing flow.
