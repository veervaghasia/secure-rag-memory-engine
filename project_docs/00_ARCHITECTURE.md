# 00_ARCHITECTURE.md

# Secure RAG Memory Engine — System Architecture

This document defines the target architecture of the Secure RAG Memory Engine.

It describes the long-term responsibilities, capabilities, interfaces, and boundaries of the system. Capabilities listed here represent the intended architecture and may be introduced progressively across development phases.

The roadmap defines when those capabilities are implemented, while the ADR documents explain the architectural decisions behind them.

---

# Architectural Principles

## 1. Zero Framework Abstractions

High-level orchestration frameworks such as LangChain and LlamaIndex must not own core business logic.

Core ingestion, retrieval, routing, fusion, memory, and agentic workflows are implemented directly in Python.

Focused infrastructure libraries may be used where they provide supporting capabilities without owning application logic.

Examples include:

* LiteLLM
* ChromaDB
* Redis
* Opik
* Ragas
* Tenacity

---

## 2. Tracer Bullet Development

Every phase should produce a fully working vertical slice.

Optimization is intentionally delayed until correctness has been established.

Development priorities are:

* correctness
* simplicity
* observability
* stable interfaces

---

## 3. Data-Driven Iteration

Architectural changes must be justified using evaluation metrics rather than intuition.

Primary evaluation metrics are:

* Context Precision
* Context Recall
* Faithfulness
* Latency

Every optimization should be measurable.

---

## 4. Stable Interfaces, Swappable Implementations

Consumers should depend only on interfaces.

Implementations may evolve between phases without changing callers.

Examples include:

* recent-history retrieval → semantic/hybrid conversation retrieval
* vector retrieval → hybrid retrieval
* one retrieval strategy → routed retrieval
* sequential orchestration → agentic orchestration

---

# Cross-Cutting Infrastructure

## Configuration System

The application is configured through a centralized Configuration System (`config/`).

Responsibilities include:

* experiment configuration
* ingestion and chunking parameters
* retrieval configuration
* embedding model selection
* memory and cache configuration
* telemetry configuration
* runtime behavior and feature toggles
* evaluation settings

Business logic must consume configuration values instead of hardcoded constants.

---

## Application Bootstrap

Every application run follows the same high-level lifecycle.

```
Application Start
        │
        ▼
Load Configuration
        │
        ▼
Validate Environment
        │
        ▼
Initialize Infrastructure
        │
        ▼
Assemble Application Services
        │
        ▼
Start Runtime
```

Infrastructure is initialized once for each application runtime and reused throughout that runtime.

Ingestion is intentionally a separate application lifecycle from interactive querying. Persistent retrieval state allows ingestion to complete before the query or evaluation lifecycle begins.

---

## Application Boundary

The application layer provides runtime entry points without owning domain state or retrieval logic.

The system contains two primary runtime workflows:

### Ingestion Runtime

```text
ingest.py
    ↓
Document Parsing
    ↓
Chunking
    ↓
Enrichment
    ↓
Embedding
    ↓
Persistent Retrieval Stores
```

### Interactive Query Runtime

```text
main.py
    ↓
CLI Interaction
    ↓
Session Resolution
    ↓
RAG Orchestrator
    ↓
Persistent Retrieval Stores
```

The two workflows share persistent infrastructure but have different responsibilities.

`ingest.py` prepares retrieval state.

`main.py` consumes persistent retrieval state and manages the interactive application flow.

---

# The Four Architectural Pillars

| Pillar | Owns |
|---|---|
| Pillar 1 — Secure Data Ingestion Pipeline | Document acquisition, transformation, enrichment, embedding preparation, ingestion state, and retrieval-state preparation |
| Pillar 2 — Agentic RAG Orchestrator | Query understanding, retrieval orchestration, generation, validation, routing, and agent execution |
| Pillar 3 — State & Session Management | Conversation state, session identity, memory, and stateful caching |
| Pillar 4 — LLMOps | Model operations, telemetry, evaluation, benchmarking, and operational analytics |

---

## Pillar 1 — Secure Data Ingestion Pipeline

Responsible for transforming external knowledge sources into high-quality, searchable knowledge artifacts.

Responsibilities include:

### Document Acquisition
- document parsing
- layout-aware HTML parsing
- OCR/image extraction
- synchronization with external sources
- incremental ingestion
- ingestion manifest management

### Document Transformation
- document sanitization
- structural chunk generation
- metadata enrichment
- embedding text generation
- deterministic identifiers
- content normalization

### Storage Preparation
- immutable document models
- chunk-level metadata generation
- deterministic identifiers
- content identity
- chunk-level deduplication
- retrieval-time metadata authorization
- document access filtering

### Performance & Reliability
- batch processing
- ingestion performance optimization
- synchronization optimization
- ingestion error isolation
- deterministic and repeatable ingestion

The chunker is responsible only for segmenting content.

Embedding enrichment is handled by a dedicated enrichment stage.

This pillar owns every transformation required to convert raw documents into searchable knowledge. It does **not** answer queries or manage conversational state.

---

## Pillar 2 — Agentic RAG Orchestrator

Responsible for transforming a user query into a grounded, validated response.

Responsibilities include:

### Query Understanding
- query processing
- intent classification
- query rewriting
- retrieval strategy selection

### Retrieval
- retrieval abstraction
- retrieval implementations
- retrieval fusion
- reranking
- metadata security filtering
- hybrid retrieval
- consuming conversation context through `get_conversation_context()`

### Agent Execution
- routing
- answer generation
- answer validation
- self-correction loops
- bounded agent execution

### Runtime Orchestration
- retry orchestration
- concurrent retrieval orchestration
- asynchronous execution
- retrieval strategy experimentation
- performance optimization of retrieval workflows

This pillar owns runtime control flow.

It consumes knowledge from other pillars but never owns document storage, memory persistence, or operational telemetry.

---

## Pillar 3 — State & Session Management

Responsible for every piece of mutable state that evolves throughout the lifetime of the application.

Responsibilities include:

### Conversation State
- session persistence
- SQLite audit logs
- conversation history
- short-term conversation memory
- semantic chat memory
- shared session vector collection

### Session Identity

The application exposes human-readable session_name values, while persistent storage uses immutable session_id values. StateManager owns the mapping between them. Session metadata is stored separately from message records so renaming a session does not alter message relationships.

### Long-Term Memory
- profile memory
- background profile extraction
- multi-tier memory management
- semantic collision detection
- fact mutation
- fact invalidation
- version tracking
- memory provenance

### Response Optimization
- semantic response caching
- TTL management
- cache invalidation
- cache consistency
- cache lifecycle management

Caching is introduced progressively; Redis-backed semantic caching is a later-phase capability.

### State Evolution
- conversation summarization
- long-term memory evolution
- session restoration
- future distributed state management

SQLite remains the authoritative conversational record.

Semantic memory augments retrieval but never replaces persistent conversation history.

This pillar owns every piece of mutable application state but never owns retrieval algorithms or evaluation logic.

---

## Pillar 4 — LLMOps

Responsible for operating, observing, evaluating, and continuously improving the system.

Responsibilities include:

### Model Operations
- model routing
- retries
- adaptive retry policies
- retry traces
- model configuration

### Observability
- telemetry
- tracing
- runtime trace metadata
- phase and experiment trace scoping
- routing and validation outcomes
- mutation events

### Evaluation
- benchmarking
- regression testing
- evaluation
- evaluation history
- longitudinal benchmarking across system versions

### Operational Analytics
- latency tracking
- token cost monitoring
- performance dashboards
- experiment tracking
- operational reporting

No business logic should reside in this pillar.

This pillar provides the evidence used to validate architectural decisions, measure system quality, and compare implementations across phases.

### Telemetry Boundary

Application components do not configure or depend directly on the telemetry backend.

The application interacts with a backend-neutral telemetry interface exposed through `telemetry/`. The current implementation uses Opik as the telemetry backend.

The boundary is:

```text
Application Components
        ↓
    telemetry/
        ↓
       Opik
```

The telemetry layer is responsible for:

* backend configuration
* availability detection
* function and span tracking
* runtime trace metadata
* correlation of model-provider operations with application traces

The application remains operational when telemetry is unavailable; telemetry is observability rather than a functional dependency of the RAG pipeline.

Retrieval state is physically isolated by experiment, while telemetry is logically scoped through `experiment_id` and `phase` metadata.

---

# High-Level Runtime

```
                    ┌──────────────────┐
                    │ Ingestion Runtime│
                    │    ingest.py     │
                    └────────┬─────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Experiment-Isolated  │
                  │ Retrieval State      │
                  ├──────────────────────┤
                  │ Chroma               │
                  │ BM25                 │
                  │ Ingestion Manifest   │
                  └──────────┬───────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Interactive Query│
                    │    main.py       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Session / State  │
                    │   Management     │
                    │    SQLite        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ RAG Orchestrator │
                    └───────┬──────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
                Retrieval    Conversation State
                    │                │
                    └───────┬────────┘
                            ▼
                           LLM
                            │
                            ▼
                          Response
```

The ingestion and query runtimes are separated by persistent retrieval state.

Session state is independent of experiment state:

- `session_id` represents conversational state.
- `experiment_id` represents retrieval and application configuration.

They must not be conflated.

---

# Guiding Principle

# Guiding Principle

Every phase should improve the system without unnecessarily compromising:

* correctness
* retrieval quality
* latency
* maintainability

Changes should be evaluated using measurable system metrics where applicable, particularly:

* Context Precision
* Context Recall
* Faithfulness
* Latency

Architectural trade-offs should be intentional, documented, and measurable where practical.