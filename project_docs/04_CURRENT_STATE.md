# Current Phase:
Phase 1

---
# Current Pillar:
Pillar 2 — Agentic RAG Orchestrator

---
# Current Branch:
feature/phase1-persistent-storage

---
## Current Goal:
Establish persistent retrieval storage and a usable interactive multi-session runtime.

This branch separates ingestion from query execution, persists ChromaDB and BM25 state across application restarts, isolates retrieval state by experiment, and provides an interactive CLI for multi-turn conversations and session management.

---
## Completed:

### Ingestion

- document parser 
- document sanitization
- fixed size chunk generator

### Chunk Identity

Each `ProcessedChunk` has two separate identities:

- `chunk_id` — deterministic identity based on source page and chunk position.
- `content_hash` — deterministic identity based on chunk text.

The distinction prevents identical text occurring at different source locations from overwriting each other in persistent retrieval stores.

`content_hash` provides content identity but is not currently used for persistent chunk-level deduplication.

The current test ingestion of 11,964 chunks produces 11,964 unique chunk IDs.

### Chroma Vector Engine

- chunk embedding 
- upsert chunks into Chromadb
- similarity search using Chromadb

### BM25 Engine

- Chunk indexing
- Lexical search
- Persistent index serialization
- Persistent index restoration

### Search Fusion

- Simple concatenation of results from vector and bm25 search

### Retrieval Orchestration Pipeline 

- connected retrieval components
- context assembly
- generation pipeline

### State & Session Memory Management

- ChatMessage DTO with Pydantic validation & LiteLLM payload formatting.
- StateManager SQLite persistence layer with @contextmanager lifecycle handling.
- Chronological history retrieval (get_conversation_context) & session cleanup (clear_session).
- Dual-turn persistence (user query + assistant reply) integrated into orchestrator.py
- Automated memory test suite (test_memory_engine.py).

### Session Management

- human-readable `session_name` used as the CLI-facing session identity
- immutable internal `session_id` retained for database relationships
- dedicated SQLite `sessions` table
- unique session names
- session creation through `get_or_create_session()`
- session-name-to-ID resolution encapsulated inside `StateManager`
- full session-history inspection
- session listing
- session switching
- session renaming
- session clearing
- session deletion with associated message cleanup
- active-session tracking inside `main.py`
- session existence is guaranteed before the RAG pipeline persists messages

### Experiment Management

- experiment-specific persistent Chroma collection
- experiment-specific BM25 index path
- experiment-specific ingestion manifest
- experiment registry persisted to `data/experiments.json`
- experiment listing through `/experiments`
- active experiment/system configuration inspection through `/info`

### Interactive Runtime

- `main.py` converted from integration-test style execution into the interactive application entry point
- persistent engines initialized once at application startup
- continuous multi-turn interaction loop
- explicit `/exit` and `/quit` commands
- empty-input handling
- slash-command dispatch before normal RAG execution
- `/help` command
- `/info` command
- `/experiments` command
- `/sessions` command
- `/switch <session_name>` command
- `/rename <new_session_name>` command
- `/history [session_name]` command
- `/clear [session_name]` command
- `/delete <session_name>` command
- assistant response latency display
- retrieved source display in the CLI

### Ingestion Runtime

- dedicated `ingest.py` entry point
- ingestion separated from interactive query execution
- incremental ingestion remains the default behavior
- command-line ingestion arguments through `argparse`
- experiment selection through ingestion arguments
- explicit reset flow for experiment-specific ingestion state
- persistent retrieval state can therefore be prepared before starting the query runtime

### Ingestion Batching

`embedding_batch_size` = 250
`chroma_upsert_batch_size` = 5000 

Two independent batch-size constraints exist in the ingestion pipeline.

#### Embedding API batching

`embedding_batch_size` = 250

(OpenAI api max tokens = 300,000)

Controls how many texts are sent to LiteLLM/OpenAI during each embedding request.

#### Chroma upsert batching

`chroma_upsert_batch_size = 5000`

(Chroma max size allowed = 5461)

Controls how many records are written to ChromaDB in a single upsert.

These values are intentionally separate because the embedding provider and the vector database impose different operational constraints.

The ChromaDB environment reported a maximum batch size of 5,461 records, so the configured upsert size was set below that limit.

### Telemetry & Observability

Phase 1 uses a centralized telemetry abstraction under `telemetry/`.

Current implementation:

- Opik is the telemetry backend.
- Application components use the `telemetry/` abstraction rather than configuring Opik directly.
- The active Opik project is `secure-rag-memory-engine`.
- Root traces record the active `experiment_id` and `phase` as metadata.
- Ingestion and interactive query traces use the same Opik project.
- LiteLLM calls are associated with the active Opik span through the telemetry abstraction.
- Telemetry initialization is fault-tolerant and does not prevent application startup when Opik is unavailable.
- Bulk ingestion inputs, outputs, and embedding vectors are excluded from telemetry capture where they would create excessive payloads.
- Operational metadata such as chunk counts, batch sizes, embedding model, collection name, retrieval configuration, result counts, session identifiers, experiment identity, and phase are retained.

#### Current Opik Constraint

Opik telemetry previously generated HTTP 413 errors because large tracked function inputs and outputs were serialized into telemetry payloads.

The issue was resolved by disabling automatic input/output capture for bulk operations and recording compact operational metadata instead.

After this change, ingestion of 11,964 chunks completed successfully without the previous Opik 413 error.

### Persistence Verification

- Chroma persistence verified across engine re-instantiation
- BM25 persistence verified across engine re-instantiation
- temporary filesystem locations used for persistence tests
- embedding calls mocked during persistence tests to avoid unnecessary external API calls

---
## Current Phase 1 Data Models

class RawOnenotePage(BaseModel):
    page_id: str 
    notebook_name: str
    section_name: str
    page_title: str
    text_content: str
    page_hash: str
    depth: int = 0  # 0 = main page, 1 = subpage, etc.
    parent_page_id: Optional[str] = None  # Tracks hierarchy for sub-pages

class ProcessedChunk(BaseModel):
    chunk_id: str 
    parent_page_id: str
    text_content: str
    chunk_index: int
    notebook_name: str
    section_name: str
    parent_page_title: str
    content_hash: str  

class IngestionPayload(BaseModel): 
    source_page_id: str
    chunks: List[ProcessedChunk]
    total_chunks: int
    parsing_latency_ms: float

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] 
    content: str
    session_id: str
    user_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the message was recorded."
    )
    def to_llm_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content
        }

---
## Branch Completion Status

- [x] Configure persistent ChromaDB client (PersistentClient) with centralized disk path in config.py
- [x] Implement disk serialization/deserialization for BM25 Engine index (e.g., via pickle or joblib)
- [x] Application can restart without losing vector retrieval state
- [x] Application can restart without losing BM25 retrieval state
- [x] Interactive CLI supports multi-turn conversations
- [x] Multiple named sessions can coexist
- [x] Sessions can be switched without recreating `StateManager`
- [x] Session names can be renamed without changing session IDs
- [x] Full session history can be inspected independently of retrieval context
- [x] Experiment retrieval state is isolated
- [x] Ingestion and query execution can be run as separate lifecycles
- [x] Verify Chroma and BM25 persistence across engine re-instantiation with automated tests

---
## Explicitly Out of Scope

- Chunk-level SHA-256 deduplication in persistent storage (open research question)
- Metadata access control / ACL security enforcement (Phase 3)
- Semantic conversation retrieval & ProfileFact extraction (Phase 3)
- Redis semantic cache & async execution (Phase 4)

---
# Document Context

This document describes the current implementation state of the Secure RAG Memory Engine.

- `00_ARCHITECTURE.md` defines the target architecture and long-term capability ownership.
- `01_ROADMAP.md` defines implementation sequencing and phase progress.
- `02_DECISIONS.md` records architectural decisions and their rationale.
- This document records what is currently implemented, tested, deferred, or still incomplete.

When this document is provided without the other project documents, the architectural context below provides the minimum context required to interpret the current implementation correctly.

---
# Architectural Context

## Global Dependency Hierarchy

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
## Runtime Philosophy

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

---
# Interactive Runtime

`main.py` is the application-facing interactive runtime.

The runtime initializes stateful components once:

```text
Application Start
        │
        ├── StateManager
        ├── ChromaVectorEngine
        └── BM25Engine
        │
        ▼
Interactive CLI Loop
        │
        ├── Slash Command
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

The CLI owns runtime interaction state such as:

`current_session_name`

It does not own database lookup or session persistence logic.

StateManager owns the translation between the human-readable session name and the persistent session ID.

---
# Phase 1 Runtime flow

## Document Ingestion

```
Exported OneNote Sections
            │
            ▼
SecureDocxParser
            │
            ▼
Manifest Check
            │
            ▼
Sanitize Text
            │
     Already Processed?
      │            │
     Yes          No
      │            ▼
      │      RawOnenotePage
      │            │
      │            ▼
      │    FixedSizeChunker
      │            │
      │            ▼
      │    ProcessedChunk
      │            │
      │            ▼
      │    ChromaDB Storage
      │            │
      │            ▼
      └────► BM25 Index
```

---
## User Query

```
User Query
      │
      ├──────────────► get_conversation_context()
      │                         │
      │                         ▼
      │                  SQLite Conversation State
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
```

---
## Conversation Persistence

```text
CLI current_session_name
        │
        ▼
StateManager.get_or_create_session()
        │
        ▼
Persistent session_id
        │
        ▼
run_rag_pipeline()
        │
        ├── get_conversation_context(session_id)
        │
        ├── generate response
        │
        ├── save user message
        │
        └── save assistant message
```

Session identity is intentionally split:

session_name → human-facing CLI identity
session_id   → immutable database identity

session_name can be renamed without modifying existing message rows.

session_id remains the foreign-key relationship used by the messages table.

---
## Current Test Status

- State/session persistence tests: passing
- Chroma persistence tests: passing
- BM25 persistence tests: passing
- Embedding calls mocked in persistence tests
- Phase 1 evaluation harness: not yet implemented
- 20-question baseline evaluation: not yet executed