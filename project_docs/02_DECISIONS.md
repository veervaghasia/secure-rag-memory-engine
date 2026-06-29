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

# Core Architectural Manifestos

---

## ADR-000 — Zero Framework Abstractions

**Status**

Accepted

**Discussed**

Yes

### Decision

High-level orchestration frameworks (LangChain, LlamaIndex, Haystack, etc.) will not implement any core business logic.

Frameworks may only be used as infrastructure components.

Examples include:

- LiteLLM
- ChromaDB
- Opik
- Redis
- Ragas
- Tenacity

### Rationale

The goal of this project is to demonstrate first-principles engineering rather than framework proficiency.

---

## ADR-001 — Tracer Bullet Development

**Status**

Accepted

**Discussed**

Yes

### Decision

Every phase should deliver a complete working vertical slice before optimization begins.

### Consequences

Avoid premature optimization.

Delay production concerns until they solve real problems.

---

## ADR-002 — Data-Driven Iteration

**Status**

Accepted

**Discussed**

Yes

### Decision

Every optimization must improve measurable evaluation metrics.

Metrics include

- Context Precision
- Context Recall
- Faithfulness
- Latency

No optimization should be introduced solely because it appears theoretically superior.

---

## ADR-003 — Centralized Runtime Configuration System

**Status**

Accepted

**Discussed**

Yes

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

**Discussed**

Yes

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

**Discussed**

Yes

### Decision

RawOnenotePage and ProcessedChunk are immutable representations of different pipeline stages.

Each stage produces a new representation rather than modifying previous ones.

---

## ADR-006 — Manifest and Deduplication Solve Different Problems

**Status**

Accepted

**Discussed**

Yes

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

**Discussed**

Yes

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

**Discussed**

Yes

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

**Discussed**

Yes

### Decision

Enriched embedding text is generated when embeddings are created.

It is not permanently persisted unless a future embedding strategy requires it.

---

## ADR-010 — Layout-Aware Parsing Deferred

**Status**

Accepted

**Discussed**

Yes

### Decision

HTML parsing.

BeautifulSoup.

OCR.

Structural chunking.

All postponed until Phase 2.

---

## ADR-011 — Persistent ChromaDB

**Status**

Research

**Discussed**

Yes

### Current Position

Ephemeral storage is sufficient for early development.

Persistent storage should only be introduced once it solves an observed problem.

---

## ADR-012 — Chunk-Level Deduplication

**Status**

Research

**Discussed**

Yes

### Current Position

Not required during Phase 1.

Revisit after persistent vector storage exists.

---

# Retrieval Decisions

---

## ADR-013 — Stable Retriever Interface

**Status**

Accepted

**Discussed**

Yes

### Decision

All retrieval implementations should inherit from BaseRetriever.

Future retrieval algorithms should not change orchestration code.

---

## ADR-014 — Reciprocal Rank Fusion

**Status**

Accepted

**Discussed**

Yes

### Decision

Hybrid retrieval combines rankings rather than raw similarity scores.

Raw cosine and BM25 scores should never be added together.

---

## ADR-015 — Cross-Encoder After Fusion

**Status**

Accepted

**Discussed**

Yes

### Decision

Only fused Top-K candidates are reranked.

The Cross-Encoder should never rerank the full corpus.

---

## ADR-016 — Intent Routing Deferred

**Status**

Accepted

**Discussed**

Yes

### Decision

Intent routing belongs to Phase 3.

Retrieval improvements should be isolated from routing improvements.

---

## ADR-017 — Self-Corrective Agent Loop

**Status**

Accepted

**Discussed**

Yes

### Decision

Agent execution uses a bounded finite-state loop.

Maximum attempts:

3

Infinite retry loops are prohibited.

---

# Memory Decisions

---

## ADR-018 — SQLite as Source of Truth

**Status**

Accepted

**Discussed**

Yes

### Decision

SQLite is the authoritative conversational history.

Vector memory is a derived representation.

---

## ADR-019 — Stable Conversation Interface

**Status**

Accepted

**Discussed**

Yes

### Decision

All callers depend only on

get_conversation_context()

Its implementation may evolve without changing callers.

---

## ADR-020 — Session IDs Introduced in Phase 1

**Status**

Accepted

**Discussed**

Yes

### Decision

Every message contains a session_id from the beginning.

Even if only a default session initially exists.

---

## ADR-021 — Shared Session Vector Collection

**Status**

Accepted

**Discussed**

Yes

### Decision

Session vectors live in one shared Chroma collection.

Isolation occurs through metadata filtering.

---

## ADR-022 — Multi-Tier Memory

**Status**

Accepted

**Discussed**

Yes

### Decision

Memory evolves into four layers.

Tier 1

Redis semantic cache.

Tier 2

SQLite conversation history.

Tier 3A

Session vector retrieval.

Tier 3B

Long-term profile memory.

---

## ADR-023 — Fact Invalidation Instead of Deletion

**Status**

Accepted

**Discussed**

Yes

### Decision

Contradictory user facts remain stored.

Older facts become inactive.

New facts become active.

No hard deletion occurs.

---

## ADR-024 — Versioned Profile Facts

**Status**

Accepted

**Discussed**

Yes

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

**Discussed**

Yes

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

# Evaluation Decisions

---

## ADR-026 — Evaluation Before Optimization

**Status**

Accepted

**Discussed**

Yes

### Decision

Every optimization must be benchmarked against the previous phase.

---

## ADR-027 — Small Smoke Test

**Status**

Accepted

**Discussed**

Yes

### Decision

Development begins with approximately five smoke-test questions.

---

## ADR-028 — Baseline Dataset

**Status**

Accepted

**Discussed**

Yes

### Decision

Phase 1 establishes a 20-question gold dataset.

Future phases expand rather than replace it.

---

# Performance Decisions

---

## ADR-029 — Async Deferred

**Status**

Accepted

**Discussed**

Yes

### Decision

Sequential execution first.

Async later.

---

## ADR-030 — Parallel Retrieval Deferred

**Status**

Accepted

**Discussed**

Yes

### Decision

Parallel retrieval belongs only after retrieval correctness is verified.

---

## ADR-031 — Redis Introduced Last

**Status**

Accepted

**Discussed**

Yes

### Decision

Caching should compensate for latency introduced by agentic reasoning.

It should not hide inefficient architecture.

---

# Security Decisions

---

## ADR-032 — Document Sanitization During Parsing

**Status**

Accepted

**Discussed**

Yes

### Decision

Sensitive patterns are redacted during ingestion before storage.

---

## ADR-033 — Metadata-Based Access Control

**Status**

Accepted

**Discussed**

Yes

### Decision

Retrievers should filter unauthorized documents before similarity search.

---

# Open Questions

---

## ADR-034 — Persistent Embedding Storage

**Status**

Open

**Discussed**

Yes

Question

Should enriched embedding text eventually be persisted to simplify embedding regeneration?

Current Position

Generate on demand.

---

## ADR-035 — Distributed Execution

**Status**

Research

**Discussed**

Partially

Question

Will the architecture eventually support distributed retrieval workers?

Decision deferred until scalability becomes a demonstrated need.

---

## ADR-036 — Graph-Based Retrieval

**Status**

Research

**Discussed**

Partially

Decision intentionally postponed until Phase 4 experimentation.

---

# Superseded Decisions

---

## ADR-037 — Recent-History Injection Only

**Status**

Superseded

**Discussed**

Yes

Original

Conversation context consisted only of recent chronological messages.

Replacement

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

New decisions should never overwrite existing ones.

Instead:

Accepted

↓

Superseded

↓

Replacement ADR

This preserves the architectural history of the project and documents why the system evolved over time.