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

Resolved in Phase 2

**Current Limitation**

Vector and BM25 results are concatenated without ranking.

**Resolution**

Replace with Reciprocal Rank Fusion.

---

## TD-005 — Recent History Injection

**Status**

Deferred → Phase 2

**Reason**

Conversation context initially uses chronological history only.

**Resolution**

Replace implementation behind
`get_conversation_context()`.

---

## TD-006 — Ephemeral Vector Store

**Status**

Accepted

**Reason**

Persistent storage is unnecessary during early development.

**Future Evaluation**

Persistent Chroma may be introduced when repeated ingestion becomes expensive.

---

## TD-007 — No Chunk-Level Deduplication

**Status**

Accepted

**Reason**

The ingestion manifest already prevents unnecessary reprocessing during Phase 1.

**Future Evaluation**

Introduce SHA-256 chunk deduplication only if persistent storage justifies the additional complexity.

---

# Phase 2

## TD-008 — Retrieval Only

**Status**

Deferred → Phase 3

**Current Limitation**

No routing.

No query rewriting.

No agent loop.

**Resolution**

Introduce intent routing and corrective loops.

---

## TD-009 — No Long-Term User Memory

**Status**

Deferred → Phase 3

**Resolution**

Implement ProfileFact extraction and mutation pipeline.

---

# Phase 3

## TD-010 — Sequential Execution

**Status**

Deferred → Phase 4

**Current Limitation**

Retrieval executes sequentially.

**Resolution**

Async orchestration.

Parallel retrieval.

Concurrent routing.

---

## TD-011 — No Semantic Cache

**Status**

Deferred → Phase 4

**Resolution**

Redis semantic cache.

---

## TD-012 — Basic Synchronization

**Status**

Deferred → Phase 4

**Current Limitation**

SQLite and vector writes are independent.

**Resolution**

Improve synchronization and transactional consistency.

---

# Ongoing Research Topics

The following items are intentionally left open until supported by evaluation.

* Persistent ChromaDB adoption
* Chunk-level deduplication strategy
* Hierarchical retrieval
* Graph-based retrieval
* Distributed execution
* Distributed caching
* Adaptive retry strategies
* Production latency optimization
* Parallel routing heuristics

These topics should only be implemented if they solve an observed problem rather than an anticipated one.

---

# Guiding Principle

Technical debt is acceptable when it accelerates learning without compromising architectural integrity.

No debt should be resolved before evaluation demonstrates that it has become a bottleneck.
