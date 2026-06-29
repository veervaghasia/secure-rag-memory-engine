# Feature Dependency Graph

This document describes architectural dependencies between features.

It is intentionally independent of filenames and implementation details.

Its purpose is to answer:

* What can be built independently?
* What must already exist?
* What is safe to refactor?

---

# Global Dependency Hierarchy

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

├── Chunking
├── Retrieval
├── Memory
├── Cache
├── Telemetry
├── Runtime
└── Evaluation

↓

Consumed by

├── ingestion
├── retrieval
├── memory
├── evaluation
└── main.py
```

---

# Depencency types

* Runtime dependency
* Compile-time dependency
* Data dependency
* Evaluation dependency

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
        ↓
Vector Store
```

---

## Retrieval

```text
Vector Store
        ↓
Vector Search
```

---

## Memory

```text
SQLite
        ↓
ChatMessage
        ↓
Session History
        ↓
get_conversation_context()
```

---

## Evaluation

```text
Pipeline
        ↓
Gold Dataset
        ↓
Evaluation Harness
        ↓
Baseline Metrics
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
SQLite
        ↓
ChatMessage
        ↓
SessionVectorChunk
        ↓
Semantic Retrieval
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

## Agent Loop

```text
Retrieval
        ↓
Generation
        ↓
Validation
        ↓
Rewrite
        ↓
Retry
```

Maximum iterations: 3

---

# Phase 4

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

## Parallel Retrieval

```text
Intent Router
      │
      ├───────────────┐
      │               │
Vector Search     BM25 Search
      │               │
      └───────┬───────┘
              ▼
        Reciprocal Rank Fusion
```

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

```
eval_harness.py
```

Every architectural optimization should be measurable using the same evaluation pipeline.

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
