# Feature Dependency Graph

This document describes architectural dependencies between features.

Its purpose is to answer:

* What can be built independently?
* What must already exist?
* What depends on which stable interface?
* What is safe to refactor?

The dependency model is independent of the physical project layout, while stable public interfaces and runtime entry points may be referenced where they define architectural boundaries.

---

# Global Architectural Dependency Hierarchy

```text
Application

↓

Configuration System
(config/)

↓

Infrastructure

↓

Application Components
```

---

# Cross-Cutting Dependencies

```text
Configuration System
        │
        ▼
Runtime Components
        │
        ├── Ingestion
        ├── Retrieval
        ├── Memory
        ├── Cache
        ├── Telemetry
        ├── Evaluation
        └── Application Runtime

↓

Consumed by

├── ingestion
├── retrieval
├── memory
├── evaluation
└── main.py
```

## Telemetry Dependencies

Application components
→ telemetry abstraction
→ Opik

LiteLLM
→ telemetry integration
→ Opik

The application does not directly depend on Opik configuration from individual business components.

Telemetry is an observability dependency rather than a functional dependency.

If telemetry becomes unavailable, ingestion and query execution should continue without telemetry.

```text
Configuration System
        │
        ▼
Telemetry Configuration
        │
        ├── phase
        ├── experiment_id
        └── telemetry enable/disable state
        │
        ▼
Telemetry Abstraction
        │
        ▼
Opik
        │
        ▼
Application-Level Project
secure-rag-memory-engine
```

Both application runtimes depend on the telemetry abstraction:

```
                    Telemetry
                       │
              ┌────────┴────────┐
              ▼                 ▼
          ingest.py          main.py
              │                 │
              └────────┬────────┘
                       ▼
                Opik Project
        secure-rag-memory-engine
```

Trace filtering by phase or experiment depends on the metadata attached by the telemetry layer.

The application workflows do not directly depend on Opik configuration details.

---

# Infrastructure Compatibility Constraints

## LiteLLM / Opik Compatibility

LiteLLM must remain at a version compatible with the Opik integration.

The current minimum supported LiteLLM version is:

`litellm >= 1.94.0`

This constraint exists because older LiteLLM versions can generate trace/span IDs with timestamps that are rejected by newer Opik validation.

---

# Dependency types

* Runtime dependency - required during execution
* Data dependency - depends on persisted/generated data
* Evaluation dependency - required to measure behavior
* Operational dependency - required for observability, infrastructure, or deployment behavior

---

# Application Runtime

```text
Configuration
      ↓
Application Runtime
      │
      ├───────────────┐
      │               │
 Ingestion        Query Runtime
 Runtime              │
      │               ▼
      ▼          Session Management
Persistent             │
Retrieval State         ▼
      │          RAG Orchestrator
      │               │
      └───────┬───────┘
              ▼
       Chroma + BM25
```

Ingestion and interactive querying are separate runtime workflows.

The query runtime depends on persistent retrieval state produced by ingestion.

---

# Phase 1

## Ingestion

```text
Document Parser
        ↓
Document Sanitization
        ↓
RawOnenotePage
        ↓
Chunk Generation
        ↓
ProcessedChunk
        │
        ├───────────────┐
        ▼               ▼
Embedding Generation   BM25 Indexing
        │               │
        ▼               ▼
Chroma Collection    BM25 Index
        │               │
        └───────┬───────┘
                ▼
        Experiment-Specific
        Persistent Retrieval State
```

The active experiment_id determines the retrieval resources used by the ingestion pipeline.

The ingestion manifest is also experiment-specific.

Therefore:
```
        experiment_id
        ├── manifest
        ├── Chroma collection
        └── BM25 index
```

---

## Retrieval

```text
Vector Store
        ↓
Vector Search
```

```text
BM25 Index
        ↓
Lexical Search
```

```
Vector Store
        ↓
Vector Search
        │
        ├──────────────┐
        │              │
        ▼              ▼
Vector Results     BM25 Results
        │              │
        └──────┬───────┘
               ▼
        Simple Result
        Concatenation
```

---

## State and Session Management

```text
CLI
 │
 ▼
current_session_name
 │
 ▼
StateManager
 │
 ├── get_or_create_session()
 │          │
 │          ▼
 │      session_id
 │
 ├── list_sessions()
 │
 ├── rename_session()
 │
 ├── get_full_history_by_name()
 │
 ├── clear_session_by_name()
 │
 └── delete_session_by_name()
          │
          ▼
   SQLite sessions table
          │
          ▼
   SQLite messages table
          │
          ▼
get_conversation_context(session_id)
```

The CLI depends on the public StateManager API.

The CLI does not depend directly on SQLite schema or private StateManager helpers.

---

## Session Identity

```text
Human-facing session name
          │
          ▼
StateManager
          │
          ▼
Immutable session_id
          │
          ▼
messages.session_id
```

Session names are unique and renameable.

Session IDs are persistent internal identifiers and remain unchanged during renames.

Therefore:
```
        Rename Session
        ↓
        UPDATE sessions.session_name
```

rather than:
```
        UPDATE every message
```

---

## Experiment Management

```text
Experiment Configuration
        ↓
experiment_id
        │
        ├───────────────┐
        │               │
        ▼               ▼
Chroma Collection    BM25 Index
        │               │
        └───────┬───────┘
                ▼
        Ingestion Manifest

experiment_id
        │
        ▼
Query Runtime
        │
        ├── ChromaVectorEngine
        └── BM25Engine

experiment_id
        ↓
Experiment Registry
        ↓
data/experiments.json
```

Experiment state is independent from chat-session state.

Experiments describe retrieval/application configurations.

Sessions describe conversational state.

But, both ingestion and querying must operate against the same experiment-specific retrieval state.

Experiment identity also propagates into telemetry:

```text
experiment_id
      │
      ├── Chroma Collection
      ├── BM25 Index
      ├── Ingestion Manifest
      ├── Experiment Registry
      └── Telemetry Metadata
```

Telemetry metadata does not provide retrieval-state isolation. It only identifies which experiment produced a trace.

---

## Evaluation

```text
Retrieval / Generation Pipeline
              │
              │
Gold Evaluation Dataset
              │
              ▼
      Evaluation Harness
              │
              ▼
           Metrics
```

---

# Phase 2

## Enriched Ingestion

```text
RawOnenotePage
        ↓
ProcessedChunk
        ↓
Embedding Enrichment
        ↓
Embedding Generation
        ↓
Vector Store
```

---

## Hybrid Retrieval

```text
Vector Retriever
             │
             │
BM25 Retriever
             │
             ▼
      BaseRetriever
             ▼
Reciprocal Rank Fusion
             ▼
Cross Encoder
             ▼
Prompt Builder
```

---

## Conversation Memory

```text
SQLite Conversation History
        ↓
ChatMessage
        ↓
SessionVectorChunk Generation
        ↓
Embedding
        ↓
Shared Chroma Collection
        ↓
Session-Scoped Semantic Retrieval
        ↓
get_conversation_context()
```

---

# Phase 3

## Intent Routing

```text
User Query
        ↓
Intent Classifier
        ↓
Document Retrieval

OR

Profile Retrieval

OR

Hybrid Retrieval
```

---

## Agent Loop

```text
Retrieve
   ↓
Generate
   ↓
Validate
   │
   ├── Pass ──► Return
   │
   └── Fail
          ↓
     Rewrite Query
          ↓
       Retrieve
```

Maximum iterations: 3

Execution is bounded; infinite retry loops are prohibited.

---

## Long-Term Memory

```text
SQLite Logs
        ↓
Fact Extraction
        ↓
Collision Detection
        ↓
Conflict Evaluation
        ↓
Fact Invalidation
        ↓
Profile Memory
```

---

## Access Control

```text
User / Session Context
        ↓
Authorization Context
        ↓
Retrieval
        ↓
ACL Filtering
        ↓
Authorized Context
        ↓
Prompt Builder
```

---

# Phase 4

## Parallel Retrieval

```text
User Query
      │
      ├───────────────┐
      ▼               ▼
Vector Search     BM25 Search
      │               │
      └───────┬───────┘
              ▼
      Reciprocal Rank Fusion
              ▼
        Cross Encoder
```

---

## Semantic Cache

```text
User Query
        ↓
Embedding
        ↓
Redis Similarity Search
        │
 ┌──────┴──────┐
 │             │
Hit          Miss
 │             │
 ▼             ▼
Return     Full Pipeline
```

---

# Application Boundary Dependencies

The following describes current application-boundary dependencies. It does not define the internal implementation of these components.

```text
main.py
  │
  ├── Configuration
  ├── StateManager
  ├── ChromaVectorEngine
  ├── BM25Engine
  ├── run_rag_pipeline()
  └── experiment_registry
```

Responsibilities:

- main.py owns user interaction and command dispatch.
- StateManager owns session persistence and session identity resolution.
- retrieval engines own retrieval state.
- run_rag_pipeline() owns query orchestration.
- experiment_registry owns experiment metadata.
- configuration determines the active experiment and corresponding persistent resources.

main.py should not contain SQL, retrieval algorithms, or experiment persistence logic.

---

# Stable Interfaces

These interfaces should remain stable even if implementations change.

## Conversation Context

```
get_conversation_context()
```

May evolve:

Recent Messages

↓

Semantic Retrieval

↓

Summarization

↓

Hybrid Context

without changing callers.

---

## Retriever Interface

```
BaseRetriever.retrieve()
```

Supports future retrievers without modifying orchestration.

Examples

* Vector Retriever
* BM25 Retriever
* Graph Retriever
* Hierarchical Retriever

---

## Evaluation Interface

The evaluation workflow should expose a stable evaluation entry point.

Conceptually:

```
Evaluation Harness
```

Every architectural optimization should remain measurable using the same evaluation workflow.

---

# Safe Refactoring Rules

A component may be replaced freely if:

* its public interface remains unchanged
* downstream consumers require no modifications
* evaluation metrics remain comparable

---

# Dependency Principle

Every feature should depend only on the smallest stable abstraction available.

Prefer:

Application
→ Interface
→ Implementation

instead of

Application
→ Concrete Implementation

This keeps future experimentation localized and minimizes cascading refactors.
