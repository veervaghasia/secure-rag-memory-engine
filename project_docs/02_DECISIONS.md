# 02_DECISIONS.md

# Secure RAG Memory Engine — Architectural Decision Record (ADR)

This document records every significant architectural decision made during the project.

Its goals are to:

- explain why decisions were made
- avoid revisiting previously settled discussions
- distinguish accepted architecture from future research
- preserve architectural intent as implementation evolves

---

# Status Definitions

| Status | Meaning |
|---------|---------|
| Accepted | Explicitly discussed and agreed upon |
| Open | Discussed but intentionally undecided |
| Research | Defer until evaluation or experimentation |
| Superseded | Previously accepted but later replaced |

---

# Core Architectural Principles

---

## ADR-000 — Zero Framework Abstractions

**Status**

Accepted

### Decision

High-level orchestration frameworks such as LangChain, LlamaIndex, and Haystack will not implement core business logic.

Core ingestion, retrieval, memory, orchestration, and state-management logic will be implemented directly in Python.

Infrastructure libraries and services may be used where they provide focused capabilities without owning application logic.

Examples include:

- LiteLLM — LLM provider abstraction
- ChromaDB — vector storage
- Opik — observability
- Redis — caching
- Ragas — evaluation support
- Tenacity — retry handling

### Rationale

The goal of this project is to demonstrate first-principles engineering rather than framework proficiency.

---

## ADR-001 — Tracer Bullet Development

**Status**

Accepted

### Decision

Every phase should deliver a complete working vertical slice before optimization begins.

### Consequences

Avoid premature optimization.

Delay production concerns until they solve real problems.

---

## ADR-002 — Data-Driven Iteration

**Status**

Accepted

### Decision

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

No optimization should be introduced solely because it appears theoretically superior.

---

## ADR-003 — Centralized Runtime Configuration System

**Status**

Accepted

### Decision

Configuration is centralized in a Configuration System rather than a single configuration file. It will be organized into domain-specific modules while exposing a single AppConfig entry point.

### Rationale

As the project evolves across four phases, runtime options become too numerous for a single file.


### Implications

Supports

• Better scalability
• Cleaner separation of concerns
• Easier experimentation
• Stable public configuration API

---

# Pillar Responsibilities

---

## ADR-004 — Pillar Ownership

**Status**

Accepted

### Decision

Each architectural concern has a single owning pillar.

#### Pillar 1

Owns transformation from raw documents into retrievable knowledge.

#### Pillar 2

Owns answering user questions.

#### Pillar 3

Owns mutable conversational state.

#### Pillar 4

Owns operational infrastructure.

### Consequences

Business logic should never leak between pillars.

---

# Ingestion Decisions

---

## ADR-005 — Immutable Raw Models

**Status**

Accepted

### Decision

RawOnenotePage and ProcessedChunk are immutable representations of different pipeline stages.

Each stage produces a new representation rather than modifying previous ones.

---

## ADR-006 — Manifest and Deduplication Solve Different Problems

**Status**

Accepted

### Decision

The ingestion manifest does not replace SHA-256 deduplication.

Manifest:

- incremental ingestion

Deduplication:

- repeated chunk storage

They coexist.

---

## ADR-007 — Enrichment as an Independent Pipeline Stage

**Status**

Accepted

### Decision

Structural ancestry injection is implemented as a dedicated enrichment stage.

Pipeline becomes

Raw Document

↓

Chunking

↓

Enrichment

↓

Embedding

### Rationale

Chunking and enrichment evolve independently.

---

## ADR-008 — Dual Text Representation

**Status**

Accepted

### Decision

Each chunk maintains

- raw text
- enriched embedding text

Embeddings are generated from enriched text.

Retrieved answers always use raw text.

---

## ADR-009 — Embeddings Generated On Demand

**Status**

Accepted

### Decision

Enriched embedding text is generated when embeddings are created.

It is not permanently persisted unless a future embedding strategy requires it.

---

## ADR-010 — Advanced Document Parsing Deferred

**Status**

Accepted

### Decision

Phase 1 will use the minimal parser required for the initial document source.

Advanced document parsing capabilities are deferred to Phase 2, including:

- HTML-specific parsing
- BeautifulSoup-based extraction
- OCR
- layout-aware extraction
- structural document parsing

### Rationale

Phase 1 prioritizes the retrieval, persistence, and evaluation boundaries before introducing document-format-specific parsing complexity.

---

## ADR-011 — Persistent ChromaDB

**Status**

Accepted

### Decision

ChromaDB now persists its collection to disk using `PersistentClient`.

BM25 is also persisted independently because it is a separate lexical retrieval implementation whose state must survive application restarts.


### Rationale

### Rationale

Persistent storage separates ingestion from query and evaluation workflows, allowing an already-ingested corpus to be reused across application runs and experiments.

Retrieval state is isolated per experiment as defined in ADR-041.

This decision also follows ADR-002 (Data-Driven Iteration) and ADR-026 (Evaluation Before Optimization).

---

## ADR-012 — Chunk-Level Deduplication

**Status**

Research

### Current Position

Not required during Phase 1.

### Current Position

Chunk-level content deduplication is not required for Phase 1.

The question remains open and should be revisited if evaluation or later ingestion workflows demonstrate a need for persistent content-level deduplication.

---

# Retrieval Decisions

---

## ADR-013 — Stable Retriever Interface

**Status**

Accepted

### Decision

All retrieval implementations should inherit from BaseRetriever.

Future retrieval algorithms should not change orchestration code.

---

## ADR-014 — Reciprocal Rank Fusion

**Status**

Accepted

### Decision

Hybrid retrieval will combine retriever rankings rather than directly adding dense and lexical similarity scores.

Reciprocal Rank Fusion (RRF) is the selected fusion strategy.

Raw cosine and BM25 scores will not be added directly because they are not directly comparable.

### Implementation Status

RRF is planned for Phase 2. Phase 1 currently combines dense and lexical retrieval results without RRF.

---

## ADR-015 — Cross-Encoder After Fusion

**Status**

Accepted

### Decision

A Cross-Encoder will rerank only the fused Top-K retrieval candidates.

The Cross-Encoder will not rerank the full corpus.

### Implementation Status

Cross-Encoder reranking is planned for Phase 2, after retrieval fusion.

---

## ADR-016 — Intent Routing Deferred

**Status**

Accepted

### Decision

Intent routing belongs to Phase 3.

Retrieval improvements should remain independently evaluable from routing improvements.

### Implementation Status

Intent routing is not part of the Phase 1 retrieval implementation.

---

## ADR-017 — Self-Corrective Agent Loop

**Status**

Accepted

### Decision

Future agent execution will use a bounded finite-state loop.

Maximum attempts:

3

Infinite retry loops are prohibited.

### Implementation Status

The self-corrective agent loop is planned for Phase 3 and is not part of the current Phase 1 pipeline.

---

# Memory Decisions

---

## ADR-018 — SQLite as Source of Truth

**Status**

Accepted

### Decision

SQLite is the authoritative conversational history.

Vector memory is a derived representation.

---

## ADR-019 — Stable Conversation Interface

**Status**

Accepted

### Decision

All callers depend only on

get_conversation_context()

Its implementation may evolve without changing callers.

---

## ADR-020 — Session IDs Introduced in Phase 1

**Status**

Accepted

### Decision

Every message contains a session_id from the beginning.

Even if only a default session initially exists.

---

## ADR-021 — Shared Session Vector Collection

**Status**

Accepted

### Decision

Session vectors live in one shared Chroma collection.

Isolation occurs through metadata filtering.

---

## ADR-022 — Multi-Tier Memory

**Status**

Accepted

### Decision

The target memory architecture evolves into four layers:

Tier 1

Redis semantic cache.

Tier 2

SQLite conversation history.

Tier 3A

Session vector retrieval.

Tier 3B

Long-term profile memory.

These layers are introduced progressively across later phases rather than implemented together in Phase 1.

---

## ADR-023 — Fact Invalidation Instead of Deletion

**Status**

Accepted

### Decision

Contradictory user facts remain stored.

Older facts become inactive.

New facts become active.

No hard deletion occurs.

---

## ADR-024 — Versioned Profile Facts

**Status**

Accepted

### Decision

Profile facts track

- version
- is_active
- provenance

to preserve historical evolution.

---

## ADR-025 — Read-Verify-Invalidate Pipeline

**Status**

Accepted

### Decision

Profile memory updates follow

Read

↓

Verify

↓

Invalidate

↓

Insert

This replaces naive append-only memory.

---

## ADR-038 — Context-Managed SQLite Connection Lifecycle

**Status**

Accepted

### Decision

All SQLite database connections must use a dedicated context-managed connection lifecycle that guarantees:

- explicit transaction handling
- rollback on failure
- connection closure

State-management code must not manage SQLite connections independently.

### Rationale

Centralizing connection lifecycle management prevents connection leaks and database-locking issues while keeping transaction handling consistent across StateManager operations.

### Consequences

- SQLite resources are released deterministically.
- Transaction handling is standardized.
- State-management operations avoid duplicated connection lifecycle boilerplate.

---

## ADR-039 — Human-Readable Session Names at the Application Boundary

**Status:** Accepted

### Context

The interactive CLI requires users to work with conversational sessions using names rather than opaque database identifiers.

A session therefore has two identities:

- `session_id` — immutable internal identifier used by database relationships
- `session_name` — human-readable identifier used by the CLI

### Decision

`main.py` maintains the active session using `current_session_name`.

The application resolves `session_name` to the internal `session_id` through StateManager before executing the RAG pipeline.

The CLI does not directly perform SQL lookups or access private StateManager methods.

For session-management commands, StateManager exposes public name-based operations such as:

- list_sessions()
- get_full_history_by_name()
- clear_session_by_name()
- delete_session_by_name()
- rename_session()

### Rationale

The CLI should operate in user-facing concepts rather than database implementation details.

Keeping name → ID resolution inside StateManager preserves encapsulation and allows the underlying database representation to change without requiring changes to main.py.

The session ID remains stable even when the session is renamed.

### Consequence

The application layer is simpler, while StateManager owns the mapping between human-readable session identity and persistent database identity.

---

## ADR-040 — Separate Session Metadata from Conversation Messages

**Status:** Accepted

### Context

A conversational session requires both:

- mutable human-readable metadata such as `session_name`
- persistent message records referencing that session

Using the session name directly as the message relationship would make renaming expensive and error-prone.

### Decision

SQLite uses separate `sessions` and `messages` tables.

The `sessions` table contains:

- `session_id` — primary key
- `session_name` — unique human-readable name
- `created_at`
- `updated_at`

The `messages` table references `sessions.session_id`.

`session_id` is treated as an immutable internal identifier.

`session_name` may be renamed without modifying existing message rows.

### Rationale

Separating identity from display metadata prevents a rename operation from requiring updates across all messages belonging to the session.

The unique constraint on `session_name` also provides deterministic name-based session lookup.

### Consequences

- Session renames modify one session record.
- Messages retain stable foreign-key relationships.
- Session deletion can cascade to associated messages.
- CLI-facing session operations can use names while database relationships continue using IDs.

---

# Evaluation Decisions

---

## ADR-026 — Evaluation Before Optimization

**Status**

Accepted

### Decision

Every optimization must be benchmarked against the previous phase.

---

## ADR-027 — Small Smoke Test

**Status**

Accepted

### Decision

Development begins with approximately five smoke-test questions.

---

## ADR-028 — Baseline Dataset

**Status**

Accepted

### Decision

Phase 1 establishes a 20-question gold evaluation dataset.

Future phases expand rather than replace it.

---

# Performance Decisions

---

## ADR-029 — Async Deferred

**Status**

Accepted

### Decision

Sequential execution first.

Async later.

### Implementation Status

Sequential execution remains the Phase 1 implementation.

---

## ADR-030 — Parallel Retrieval Deferred

**Status**

Accepted

### Decision

Parallel retrieval belongs only after retrieval correctness is verified.

### Implementation Status

Retrieval remains sequential in Phase 1.

---

## ADR-031 — Redis Introduced Last

**Status**

Accepted

### Decision

Caching should compensate for latency introduced by agentic reasoning.

It should not hide inefficient architecture.

### Implementation Status

Redis caching is deferred to a later phase.

---

# Security Decisions

---

## ADR-032 — Document Sanitization During Parsing

**Status**

Accepted

### Decision

Sensitive patterns are redacted during ingestion before storage.

---

## ADR-033 — Metadata-Based Access Control

**Status**

Accepted

### Decision

Retrievers must apply authorization filters before similarity search so unauthorized documents are excluded from retrieval candidates.

### Implementation Status

Metadata-based access control is a future security capability and is not part of the current Phase 1 retrieval implementation.

---

# Experiment and Observability Decisions

---

## ADR-041 — Experiment-Isolated Retrieval State

**Status:** Accepted

### Context

Different experiments may change parameters that affect the structure, representation, or retrieval behavior of the corpus, including:

- chunking strategy
- chunk size
- chunk overlap
- embedding model
- retrieval configuration

Allowing different experiment configurations to share the same vector collection, BM25 index, or ingestion manifest can mix incompatible retrieval state.

### Decision

Persistent retrieval state is isolated by `experiment_id`.

The active experiment determines:

```text
experiment_id
      ├── Chroma collection
      ├── BM25 index
      └── ingestion manifest
```

Experiment metadata is additionally recorded in the experiment registry.

### Rationale

Vector and lexical retrieval must operate over the same chunk corpus.

A changed chunking or embedding strategy must therefore not silently reuse incompatible persistent state.

The manifest is also experiment-specific because changing the experiment configuration must be able to trigger independent ingestion.

### Consequences

Changing the active experiment changes the persistent retrieval resources without requiring application control-flow changes.

Experiment inspection is separate from conversational session state.

---

## ADR-042 — Separate Chunk Identity from Content Identity

**Status**

Accepted

### Context

### Context

A content hash alone cannot distinguish identical text occurring at different source locations.

Chunk identity and content identity therefore represent different concepts.

This incorrectly conflated:

- where a chunk came from
- what content the chunk contains

### Decision

Use two deterministic hashes with different semantics.

`chunk_id`:

SHA-256 of:

`parent_page_id + ":" + chunk_index`

`content_hash`:

SHA-256 of the chunk text.

Therefore:

- `chunk_id` represents chunk identity/location.
- `content_hash` represents content identity.

Identical content from different source locations can therefore coexist while
remaining deterministic across ingestion runs.

### Consequences

- Duplicate content is not accidentally collapsed by the primary chunk ID.
- Chunk IDs remain reproducible.
- Content identity remains available independently for future deduplication,
  change detection, or content-level analysis.

### Relationship to ADR-012

`content_hash` provides content identity but does not perform deduplication.

Chunk-level content deduplication therefore remains an open research question under ADR-012.

---

## ADR-043 — Shared Telemetry Project with Metadata-Based Trace Scoping

**Status:** Accepted

### Context

The application contains multiple runtime workflows, including:

- ingestion through `ingest.py`
- interactive querying through `main.py`
- future evaluation workflows

These workflows produce telemetry traces that belong to the same application but may operate under different:

- phases
- experiments
- runtime operations

Creating a separate Opik project for every phase or experiment would fragment observability and make cross-phase comparisons more difficult.

### Decision

All application telemetry uses a single stable Opik project:

`secure-rag-memory-engine`

Trace scope is represented through runtime metadata rather than separate Opik projects.

Every root trace records:
`experiment_id`
`phase`

Additional operation-specific metadata may be attached to individual traces or spans.

The telemetry architecture therefore follows:

```
Opik project
    │
    └── secure-rag-memory-engine
            │
            ├── phase
            └── experiment_id
```

To inspect a particular phase or experiment, telemetry consumers filter traces using:
`phase`
`experiment_id`


The application does not create separate Opik projects for these scopes.

### Implementation Status

The shared Opik project and metadata-based trace scoping are implemented for the current telemetry architecture. This decision does not imply that the evaluation harness or all future evaluation workflows are complete.

### Rationale

A shared project provides:

- one application-level observability namespace
- consistent trace structure across phases
- easier comparison between experiments
- centralized operational history
- reduced telemetry configuration complexity

Metadata provides the logical separation required for experiment and phase analysis without physically fragmenting the telemetry backend.

### Consequences

- All enabled application runs appear in the same Opik project.
- Phase and experiment filters must be applied when inspecting traces.
- Root traces must attach the current experiment_id and phase.
- Operation-specific metadata should describe the runtime behavior without duplicating experiment identity.
- Changing the experiment does not require changing the Opik project.

### Boundary

Experiment isolation of retrieval state and telemetry grouping are separate concerns.

Retrieval state is physically isolated:

```
experiment_id
    ├── Chroma collection
    ├── BM25 index
    └── ingestion manifest
```

Telemetry is logically isolated:

```
Opik project
    ├── phase metadata
    └── experiment_id metadata
```

Telemetry metadata must never be treated as a substitute for retrieval-state isolation.


---

# Open Questions

---

## ADR-034 — Persistent Embedding Storage

**Status**

Open

### Question

Should enriched embedding text eventually be persisted to simplify embedding regeneration?

### Current Position

The current implementation generates enriched embedding text on demand and does not persist it.

Whether to persist it remains open for future experimentation.

---

## ADR-035 — Distributed Execution

**Status**

Research

### Question

Will the architecture eventually support distributed retrieval workers?

### Current Position

Decision deferred until scalability becomes a demonstrated need.

---

## ADR-036 — Graph-Based Retrieval

**Status**

Research

### Current Position

Decision intentionally postponed until Phase 4 experimentation.

---

# Superseded Decisions

---

## ADR-037 — Recent-History Injection Only

**Status**

Superseded

### Original

Conversation context consisted only of recent chronological messages.

### Replacement

Stable get_conversation_context() supporting

- recent history
- semantic retrieval
- summarization
- hybrid context

without changing callers.

---

# Decision Review Policy

Every architectural decision should satisfy at least one of the following:

- improves maintainability
- improves extensibility
- improves evaluation metrics
- simplifies future experimentation
- reduces coupling
- preserves architectural consistency

If none of these are true, the decision should be reconsidered.

---

# Change Policy

When an accepted decision changes, the original ADR is retained and marked Superseded.

Accepted

↓
Superseded

↓
Replacement ADR

This preserves the architectural history of the project and documents why the system evolved over time.