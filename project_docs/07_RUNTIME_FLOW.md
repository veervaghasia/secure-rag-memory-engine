# 07_RUNTIME_FLOW.md

# Secure RAG Memory Engine — Runtime Flow

This document describes how the application behaves during execution.

The architecture document defines target capability ownership; this document describes how those capabilities participate in runtime execution as they are introduced across phases.

Unlike the roadmap, this document focuses on **runtime behavior**, not implementation order.

The runtime flow evolves across phases while preserving stable interfaces wherever possible.

---

# Runtime Philosophy

The application should evolve by replacing implementations rather than changing control flow.

Whenever possible:

```
Caller
    │
    ▼
Stable Interface
    │
    ▼
Implementation
```

Only the implementation should change between phases.

---

# Application Bootstrap Sequence

```
Application Start

↓

Load Configuration System

↓

Validate Environment

↓

Initialize Telemetry

↓

Initialize Storage

↓

Initialize Retrieval Components

↓

Enter Runtime
```

Infrastructure is initialized once and reused throughout the application's lifetime.

Telemetry initialization establishes the application-level telemetry context before runtime execution begins.

The telemetry backend uses one stable Opik project:

```text
secure-rag-memory-engine
```

The active runtime scope is attached to traces through:

```
phase
experiment_id
```

Therefore telemetry flows from both application workflows into the same project:

```
                    secure-rag-memory-engine
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
           ingest.py                    main.py
                 │                         │
                 ▼                         ▼
          Ingestion traces           Query traces
                 │                         │
                 └────────────┬────────────┘
                              ▼
                       Trace metadata
                       ├── phase
                       └── experiment_id
```

---

# Phase 1 Runtime

Phase 1 contains two separate application workflows:

1. Ingestion runtime
2. Interactive query runtime

The workflows share persistent retrieval state but have different responsibilities.

---

## Document Ingestion Runtime

```
ingest.py
    │
    ▼
Load Configuration
    │
    ▼
Resolve Active Experiment
    │
    ▼
SecureDocxParser
    │
    ▼
Sanitize Text
    │
    ▼
Experiment-Specific Manifest Check
    │
    ├── Already Processed ──► Skip
    │
    └── New / Changed
             │
             ▼
       RawOnenotePage
             │
             ▼
       FixedSizeChunker
             │
             ▼
       ProcessedChunk
             │
        ┌────┴────┐
        ▼         ▼
     Chroma      BM25
        │         │
        └────┬────┘
             ▼
   Persistent Experiment State
```

The ingestion runtime prepares persistent retrieval state for later query execution.

The active experiment_id determines the Chroma collection, BM25 index, and ingestion manifest used by the ingestion workflow.

The same active experiment_id is also attached to the ingestion telemetry trace.

The ingestion runtime therefore produces:

```text
experiment_id
      │
      ├── Chroma collection
      ├── BM25 index
      ├── ingestion manifest
      └── Opik trace metadata
```

Ingestion and query execution do not need to occur in the same application process.

Since we are using telemetry to track, we get this tree
run_ingestion trace
    ├── scan_directory
    ├── parse_section_into_pages
    ├── vector_upsert_chunks
    │      └── _compute_embeddings_batch
    └── bm25_upsert_chunks

Telemetry records operational metadata for meaningful runtime stages.

Large document collections, bulk function inputs and outputs, and embedding vectors are excluded from telemetry capture where they would create excessive payloads.

---

## Interactive Query Runtime

```
main.py
    │
    ▼
Load Configuration
    │
    ▼
Initialize Persistent Infrastructure
    │
    ├── StateManager
    ├── ChromaVectorEngine
    └── BM25Engine
    │
    ▼
Interactive CLI Loop
    │
    ├── Slash Command
    │       │
    │       └── Execute command
    │
    └── User Query
            │
            ▼
    Resolve current_session_name
            │
            ▼
    StateManager.get_or_create_session()
            │
            ▼
        session_id
            │
            ▼
    run_rag_pipeline()
```

Persistent infrastructure is initialized once when the application starts and reused throughout the interactive session.

The query runtime uses the same active experiment_id as the persistent retrieval resources.

Each root query trace is associated with:

```text
phase
experiment_id
```

This allows query traces to be distinguished from ingestion traces while remaining inside the same Opik project.

The intended hierarchy should be documented as:

run_rag_pipeline
    ├── preprocess_query
    ├── vector_search
    │      └── embedding
    ├── bm25_search
    ├── result_fusion
    ├── build_prompt
    └── LLM generation

A single user query should produce one logical parent trace with child spans representing meaningful pipeline stages rather than unrelated traces for each operation.

---

## Session Management Runtime

The CLI exposes human-readable session names while StateManager owns the mapping to persistent session IDs.

```
current_session_name
        │
        ▼
StateManager
        │
        ▼
session_id
        │
        ▼
run_rag_pipeline()
        │
        ├── get_conversation_context(session_id)
        ├── generate response
        ├── save user message
        └── save assistant message
```

Session-management commands operate through the public StateManager API.

Supported commands include:

```
/help
/info
/experiments
/sessions
/switch <session_name>
/rename <new_session_name>
/history [session_name]
/clear [session_name]
/delete <session_name>
/exit
/quit
```

The CLI owns interaction state such as current_session_name.

StateManager owns:

```
session creation
session-name-to-ID resolution
session listing
session renaming
session history retrieval
session clearing
session deletion
```

The CLI does not perform direct SQL access or database-level session resolution.

---

## User Query Flow

```
User Query
      │
      ▼
current_session_name
      │
      ▼
StateManager.get_or_create_session()
      │
      ▼
session_id
      │
      ▼
get_conversation_context(session_id)
      │
      ▼
Vector Search
      │
      ▼
BM25 Search
      │
      ▼
Append Results
      │
      ▼
Prompt Builder
      │
      ▼
LiteLLM
      │
      ▼
Assistant Response
      │
      ├── Save User Message
      │
      └── Save Assistant Message
```

Conversation persistence occurs through the orchestrator and StateManager.

The SQLite sessions table stores session metadata, while the messages table stores message records referencing the immutable session_id.

---

## Experiment Runtime

Experiments are independent of conversational sessions.

```
Experiment Configuration
        │
        ▼
experiment_id
        │
        ├── Chroma Collection
        ├── BM25 Index
        └── Ingestion Manifest
```

Experiment metadata is maintained separately in the experiment registry.

The /experiments command exposes available experiments.

The /info command exposes active experiment and system configuration information.

Changing experiments changes the persistent retrieval state used by the application without changing conversational session identity.

### Experiment Telemetry Scope

Experiment identity also propagates into runtime telemetry.

```text
Active experiment
       │
       ▼
experiment_id
       │
       ├───────────────┐
       ▼               ▼
Retrieval State     Telemetry
       │               │
       ▼               ▼
Chroma/BM25       Opik metadata
                      │
                      ▼
              secure-rag-memory-engine
```

The telemetry backend does not create a separate project for each experiment.

To inspect a specific experiment, traces are filtered using:

```
experiment_id = <target experiment>
```

To inspect a specific implementation phase:

```
phase = <target phase>
```

Both filters may be applied together:

```
phase = Phase 1
experiment_id = v1_baseline
```

This allows ingestion and query traces belonging to the same experiment to be inspected together.

---

## Evaluation

Phase 1 evaluation runs against the persistent retrieval state produced by the ingestion runtime.

```
Persistent Retrieval State
        │
        ▼
Run Query Pipeline ◄──── Gold Evaluation Dataset
        │
        ▼
Evaluation Harness
        │
        ▼
Collect Metrics
        │
        ▼
Opik Trace
        │
        ├── phase
        └── experiment_id
```

Evaluation is intentionally separated from ingestion so retrieval and generation behavior can be measured without repeating document ingestion for every evaluation run.

Evaluation telemetry uses the same application-level Opik project as ingestion and interactive querying.

Experiment metadata allows evaluation traces to be associated with the exact retrieval state being evaluated.

---

# Phase 2 Runtime

The stable application boundaries remain largely unchanged while retrieval and memory implementations become more capable.

The public runtime remains almost identical.

---

## Enriched Ingestion

```
RawOnenotePage
        │
        ▼
Chunk Generator
        │
        ▼
ProcessedChunk
        │
        ▼
Embedding Enrichment
        │
        ▼
Embedding Text
        │
        ▼
Embedding Generation
        │
        ▼
Vector Store
```

Raw text is preserved.

Embedding text exists only to improve retrieval quality.

---

## Retrieval Pipeline

```
User Query
      │
      ▼
get_conversation_context()
      │
      ▼
Retriever Interface
      │
      ├──────────────┐
      ▼              ▼
Vector        BM25 Retriever
Retriever
      │              │
      └──────┬───────┘
             ▼
Reciprocal Rank Fusion
             │
             ▼
Cross Encoder
             │
             ▼
Prompt Builder
             │
             ▼
LiteLLM
```

---

## Conversation Memory

Phase 2 introduces semantic conversation retrieval.

```
Conversation Message
        │
        ▼
SessionVectorChunk
        │
        ▼
Shared Chroma Collection
        │
        ▼
Session Metadata Filtering
        │
        ▼
Semantic Retrieval
```

Conversation context becomes

```
Recent Messages
        +
Semantic Retrieval
        │
        ▼
get_conversation_context()
```

The Phase 1 implementation remains chronological SQLite history.

Consumers remain unchanged.

---

# Phase 3 Runtime

Phase 3 introduces governed agentic execution through intent routing, corrective retrieval, access-control enforcement, and long-term memory.

---

## Intent Routing

```
User Query
      │
      ▼
Intent Classifier
      │
 ┌────┼───────────────┐
 ▼    ▼               ▼
Docs Profile       Hybrid
 │      │              │
 └──────┴──────────────┘
            │
            ▼
      ACL Filtering
            │
            ▼
Context Assembly
```

---

## Long-Term Memory Update

Long-term memory updates are triggered by the Phase 3 memory workflow.

The workflow extracts candidate profile facts from conversation state and applies the read-verify-invalidate pipeline before inserting new active facts

```
SQLite Logs
      │
      ▼
LLM Fact Extraction
      │
      ▼
Semantic Collision Search
      │
      ▼
Conflict Evaluation
      │
 ┌────┴────────────┐
 ▼                 ▼
Replace        Append
 │                 │
 ▼                 ▼
Deactivate     Insert
Old Fact       New Fact
```

No historical information is deleted.

---

## Agent Loop

```
User Query
      │
      ▼
Retrieve Context
      │
      ▼
Generate Answer
      │
      ▼
Validate Answer
      │
 ┌────┴────┐
 │         │
Pass     Fail
 │         │
 ▼         ▼
Return  Rewrite Query
            │
            ▼
      Retrieve Again
```

Maximum iterations: 3

The corrective loop is bounded and exits gracefully after the final attempt.

```
3
```

Failure exits gracefully after the final attempt.

---

# Phase 4 Runtime

Phase 4 focuses on runtime efficiency, concurrency, caching, and operational scalability while preserving the established behavioral and evaluation contracts.

---

## Semantic Cache

```
User Query
    │
    ▼
Resolve Request Context
    │
    ├── experiment
    ├── session/user context
    └── authorization context
    │
    ▼
Embedding
      │
      ▼
Cache Lookup
      │
 ┌────┴─────┐
 │          │
Hit       Miss
 │          │
 ▼          ▼
Return   Full Pipeline
```

A cache hit bypasses retrieval and generation entirely.

The cache must be scoped appropriately to the same security/experiment/session semantics as the request. Otherwise a semantically similar query could return another experiment's or user's response.

---

## Parallel Retrieval

```
Intent Router
      │
      ├──────────────┐
      ▼              ▼
Vector Search   BM25 Search
      │              │
      └──────┬───────┘
             ▼
Reciprocal Rank Fusion
             ▼
Cross Encoder
```

Only independent retrieval operations execute concurrently.

---

## Example Cache Invalidation Flow

```
State or Knowledge Change
        │
        ▼
Identify Affected Cache Entries
        │
        ▼
Invalidate
        │
        ▼
Future Requests Recompute
```

Example: when a ProfileFact changes

```
Profile Updated
        │
        ▼
Invalidate Active Fact
        │
        ▼
Redis Eviction
        │
        ▼
Future Requests Miss Cache
```

This prevents stale cached responses.

---

# Stable Interfaces

The following interfaces should remain stable across all phases.

---

## Conversation Context

```
get_conversation_context()
```

May evolve internally from

```
Recent Messages
```

to

```
Recent Messages

+

Semantic Retrieval

+

Summaries

+

Profile Memory
```

without changing callers.

---

## Retrieval

```
BaseRetriever.retrieve()
```

Future implementations include:

* Vector Retriever
* BM25 Retriever
* Graph Retriever
* Hierarchical Retriever

---

## State Management

The application interacts with conversational state through StateManager's public API.

Core responsibilities include:

```
get_or_create_session()
get_conversation_context()
list_sessions()
rename_session()
get_full_history_by_name()
clear_session_by_name()
delete_session_by_name()
```

Internal SQLite representation may evolve while session identity and persistence responsibilities remain encapsulated within StateManager.

The application layer should not perform direct SQL session resolution.

---

## Evaluation

```
Evaluation Harness
```

Every phase uses the same evaluation entry point.

Only datasets and metrics evolve.

---

# Runtime Evolution Summary

| Phase   | Runtime Change                                                  |
| ------- | --------------------------------------------------------------- |
| Phase 1 | Separate ingestion and query lifecycles, persistent retrieval state, and interactive multi-session runtime                                    |
| Phase 2 | Better retrieval quality through enrichment, RRF, and reranking, and semantic conversation retrieval |
| Phase 3 | Intent routing, long-term memory, and corrective agent loop     |
| Phase 4 | Semantic caching, concurrency, and production optimization      |

---

# Runtime Invariants

The following principles should remain true regardless of implementation phase.

1. Documents flow only through the ingestion pipeline.

2. Persistent mutable user state is owned by the state and memory layer.

3. Retrieval never mutates stored knowledge.

4. Evaluation never modifies application behavior.

5. Operational tooling (Opik, LiteLLM, Redis, etc.) must not contain business logic.

6. Stable interfaces should change far less frequently than their implementations.

Maintaining these invariants keeps experimentation localized and minimizes large-scale refactoring as the system evolves.
