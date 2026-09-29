# Technical Debt & Deferred Work

This document tracks intentional technical debt, deferred architectural improvements, and known limitations.

A task belongs here only if it is intentionally postponed. Planned future features belong in the roadmap instead.

---

# Status Definitions

| Status   | Meaning                                  |
| -------- | ---------------------------------------- |
| Deferred | Intentionally postponed to a later phase |
| Accepted | Known limitation accepted for now        |
| Research | Architecture not finalized               |
| Resolved | Debt has been paid off                   |

---

# Phase 1

## TD-001 — Fixed-Size Character Chunking

**Status**
Deferred → Phase 2

**Reason**

Fixed-size chunking provides a simple baseline for evaluation.

**Current Limitation**

* chunks may split sentences
* structural information is lost
* lower retrieval recall

**Resolution**

Replace with structural chunking after introducing layout-aware parsing.

---

## TD-002 — Plain DOCX Parsing

**Status**

Deferred → Phase 2

**Reason**

A lightweight parser allows rapid end-to-end validation.

**Current Limitation**

OneNote document structure is inferred using heuristics.

**Resolution**

Replace with layout-aware HTML parsing using BeautifulSoup.

---

## TD-003 — No OCR Support

**Status**

Deferred → Phase 2

**Reason**

Images are ignored during baseline evaluation.

**Current Limitation**

Screenshots and diagrams cannot be retrieved.

**Resolution**

Introduce OCR pipeline after HTML parsing.

---

## TD-004 — Simple Retrieval Fusion

**Status**

Deferred → Phase 2

**Current Limitation**

Vector and BM25 results are concatenated without ranking.

**Resolution**

Replace concatenation with Reciprocal Rank Fusion after the Phase 1 baseline has been evaluated.

---

## TD-005 — Chronological Conversation Context

**Status**

Accepted

**Reason**

Phase 1 uses chronological recent-message context from SQLite through the stable `get_conversation_context()` interface.

**Current Limitation**

Conversation context is limited to recent messages and does not yet perform semantic conversation retrieval, summarization, or hybrid memory retrieval.

**Future Evolution**

Replace the implementation behind `get_conversation_context()` during the memory evolution work without changing its callers.

---

## TD-006 — Persistent Storage Hardening

**Status**

Accepted

**Reason**

Phase 1 now uses persistent ChromaDB and serialized BM25 state so ingestion can be separated from query/evaluation runtime.

**Current Limitations**

Persistent local storage is functional but not yet hardened for production-level operational requirements.

Potential issues include:

- concurrent writers
- atomic persistence
- file corruption during writes
- index/schema version compatibility
- cross-store consistency between Chroma and BM25

**Resolution**

Address individual hardening requirements only when deployment or evaluation demonstrates that they are necessary.

---

## TD-007 — No Chunk-Level Deduplication

**Status**

Research

**Reason**

The ingestion pipeline already computes deterministic content hashes, but these hashes are not currently used to deduplicate chunks across persistent storage.

The ingestion manifest prevents unnecessary reprocessing of unchanged source documents, but it does not provide chunk-level deduplication.

**Current Limitation**

Repeated or equivalent chunks may still exist in persistent retrieval stores.

**Research Direction**

Introduce chunk-level SHA-256 deduplication only if persistent storage or evaluation demonstrates that the additional complexity is justified.

---

## TD-013 — SQLite Concurrency Constraints

**Status**

Accepted

**Reason**

SQLite provides zero-configuration, lightweight local file storage ideal for single-user/Phase 1 validation.

**Current Limitation**

High-concurrency parallel writes across multiple threads or web workers can cause `database is locked` errors.

**Resolution**

Migrate persistent state management to PostgreSQL or a managed relational database service if multi-process write concurrency becomes a requirement in Phase 4.

---

## TD-014 — Unbounded Session Message Growth

**Status**

Accepted

**Reason**

Memory retrieval is already bounded at read-time via `LIMIT k` queries, preventing prompt token bloat during Phase 1 evaluation.

**Current Limitation**

The `messages` table grows indefinitely on disk because there is no automated TTL (Time-To-Live), archiving, or pruning policy per `session_id`.

**Resolution**

Introduce message retention, archival, or pruning policies if long-term session growth becomes an operational requirement.

---

## TD-015 — Raw ISO String Timestamp Storage

**Status**

Accepted

**Reason**

String-based ISO 8601 formatting provides human-readable UTC representation without complex schema setup.

**Current Limitation**

Performing time-windowed SQL queries or date math directly inside SQLite requires string parsing or custom functions.

**Resolution**

Normalize to Unix epoch integers or indexed `DATETIME` columns if complex time-range filtering is required in future memory tiers.

---

## TD-016 — BM25 Pickle Persistence

**Status**

Accepted

**Reason**

Pickle provides a simple Phase 1 mechanism for serializing BM25 state and allows the project to establish persistent lexical retrieval quickly.

**Current Limitations**

- pickle files are Python-specific
- arbitrary pickle files must not be treated as trusted input
- schema/version compatibility is not explicitly managed
- writes are not yet atomic

**Resolution**

Replace or harden the persistence mechanism if portability, security boundaries, concurrent writes, or version migration become requirements.

---

## TD-017 — Independent Vector and Lexical Persistence

**Status**

Accepted

**Reason**

ChromaDB and BM25 are independent retrieval implementations and therefore maintain separate persistent state.

**Current Limitation**

There is no transaction spanning both stores.

A failure during ingestion could theoretically leave one store updated while the other is not.

**Resolution**

Introduce coordinated ingestion state/versioning or transactional synchronization only when evaluation or deployment requirements justify the added complexity.

---

## TD-018 — CLI Command Dispatch Structure

**Status**

Accepted

**Reason**

Phase 1 uses straightforward command matching in `main.py` because the CLI command set is small.

**Current Limitation**

As the number of commands grows, a long conditional dispatcher may become difficult to maintain.

**Resolution**

Introduce a dedicated command-dispatch abstraction only if CLI complexity grows enough to justify it.

---

## TD-019 — Telemetry Backend-Level Trace Isolation

**Status**

Accepted

**Reason**

The application intentionally uses one Opik project for all phases and experiments.

Logical isolation is provided through:

- `phase`
- `experiment_id`

rather than separate Opik projects.

**Current Limitation**

Telemetry consumers must filter traces using metadata when inspecting a specific phase or experiment.

The application does not currently create separate backend-level telemetry namespaces for individual experiments.

**Resolution**

No change planned unless telemetry volume, access-control requirements, or operational workflows demonstrate that stronger backend-level isolation is necessary.

---

## TD-020: Telemetry Decorator Initialization Coupling

**Status**

Deferred

**Scope**

Phase 1 telemetry infrastructure

**Description**

The telemetry adapter centralizes Opik configuration, but decorated functions
are imported before application bootstrap configuration executes.

Python evaluates decorators when modules are imported. Therefore, simply checking
telemetry availability inside the decorator factory is insufficient when
availability is established later during application startup.

The current `track()` implementation requires further hardening so that telemetry initialization failure cannot prevent instrumented modules from importing or executing.

**Desired Outcome**

The telemetry decorator should remain backend-neutral and should safely behave as
a no-op when telemetry is unavailable.

Telemetry failure must never prevent the core ingestion or query pipeline from
running.

**Related Components**

* `telemetry/opik_adapter.py`
* `main.py`
* `ingest.py`
* modules using `@track`

---

# Phase 2

## TD-008 — No Query Routing or Corrective Retrieval

**Status**

Deferred → Phase 3

**Current Limitation**

Phase 1 and Phase 2 execute a fixed retrieval pipeline.

The system does not yet perform:

- intent routing
- query rewriting
- corrective retrieval
- bounded agent execution

**Resolution**

Introduce governed intent routing and bounded corrective retrieval workflows in Phase 3.

---

## TD-009 — No Long-Term User Memory

**Status**

Deferred → Phase 3

**Resolution**

Implement ProfileFact extraction and mutation pipeline.

---

# Phase 3

## TD-010 — Sequential Retrieval Execution

**Status**

Deferred → Phase 4

**Current Limitation**

Independent retrieval operations execute sequentially in the current runtime.

**Resolution**

Introduce asynchronous orchestration and parallel execution for independent retrieval operations where evaluation demonstrates a latency benefit.

---

## TD-011 — No Semantic Cache

**Status**

Deferred → Phase 4

**Resolution**

Redis semantic cache.

---

## TD-021 — No Metadata Access Control Enforcement

**Status**

Deferred → Phase 3

**Reason**

Phase 1 and Phase 2 operate without document-level authorization filtering.

**Current Limitation**

Retrieved content is not currently filtered according to user or session authorization context before being passed to generation.

**Resolution**

Introduce metadata-based access-control enforcement in the retrieval/context pipeline so unauthorized content cannot reach generation.

---

# Ongoing Research Topics

The following topics remain open research questions. They are not committed implementation work unless they are later added to the roadmap.

- Chunk-level deduplication strategy
- Persistent index versioning
- Cross-store ingestion consistency
- Concurrent persistent-store access
- Hierarchical retrieval
- Graph-based retrieval
- Distributed execution
- Distributed caching
- Adaptive retry strategies
- Production latency optimization
- Parallel routing heuristics

---

# Guiding Principle

Technical debt is acceptable when it accelerates learning without compromising architectural integrity.

Debt should be resolved when evaluation, security requirements, operational requirements, or deployment constraints demonstrate that the limitation has become consequential.

Deferred work should not be implemented merely because it is architecturally possible.