# 00_ARCHITECTURE.md

# Secure RAG Memory Engine — System Architecture

This document defines the long-term architecture of the Secure RAG Memory Engine.

Unlike the roadmap, this document is intended to remain relatively stable throughout development. It describes the guiding principles, system responsibilities, and architectural boundaries rather than implementation status.

---

# Architectural Manifestos

## 1. Zero Framework Abstractions

High-level orchestration frameworks (LangChain, LlamaIndex, etc.) must not implement business logic.

All ingestion, retrieval, routing, fusion, memory, and agentic workflows are implemented directly in Python.

Frameworks may only be used as infrastructure libraries.

Examples include:

* LiteLLM
* ChromaDB
* Redis
* Opik
* Ragas

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

* recent history → semantic retrieval
* vector retrieval → hybrid retrieval
* simple retrieval → routed retrieval
* linear execution → agentic execution

---

# Cross-Cutting Infrastructure

## Configuration System

The application is configured through a centralized Configuration System (`config/`).

Responsibilities include:

* chunking parameters
* retrieval configuration
* embedding model selection
* cache configuration
* memory configuration
* telemetry
* runtime behavior
* feature toggles
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

Infrastructure is initialized once and reused throughout the application's lifetime.

---

# The Four Architectural Pillars

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
- pre-embedding deduplication
- future chunk-level deduplication
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
- conversation-context assembly via `get_conversation_context()`

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
- observability
- routing decisions
- validator outcomes
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
- production readiness assessment
- operational reporting

No business logic should reside in this pillar.

This pillar provides the evidence used to validate architectural decisions, measure system quality, and compare implementations across phases.

---

# High-Level Runtime

```
User Query
        │
        ▼
Configuration
        │
        ▼
Memory Layer
        │
        ▼
Retriever
        │
        ▼
Context Assembly
        │
        ▼
LLM
        │
        ▼
Validator
        │
        ▼
Response
```

The internal implementations evolve across phases while preserving the overall control flow.

---

# Guiding Principle

Every phase should improve one of four properties without unnecessarily compromising the others:

* correctness
* retrieval quality
* latency
* maintainability

Trade-offs should always be intentional and measurable.
