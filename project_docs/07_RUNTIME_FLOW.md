# 07_RUNTIME_FLOW.md

# Secure RAG Memory Engine — Runtime Flow

This document describes how the application behaves during execution.

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

---

# Phase 1 Runtime

## Document Ingestion

```
Exported OneNote Sections
            │
            ▼
SecureDocxParser
            │
            ▼
Sanitize Text
            │
            ▼
Manifest Check
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
      ▼
SQLite History
      │
      ▼
get_conversation_context()
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

```
User Message
      │
      ▼
SQLite
      │
      ▼
ChatMessage
      │
      ▼
Commit
```

Assistant responses follow the same path.

---

## Evaluation

```
Gold Dataset
      │
      ▼
eval_harness.py
      │
      ▼
Run Pipeline
      │
      ▼
Collect Metrics
      │
      ▼
Opik Trace
```

---

# Phase 2 Runtime

Only the internal implementations change.

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

```
New Chat Message
        │
        ▼
SQLite
        │
        ▼
SessionVectorChunk
        │
        ▼
Shared Chroma Collection
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

Consumers remain unchanged.

---

# Phase 3 Runtime

The application becomes agentic.

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
Docs Profile      Hybrid
 │      │            │
 └──────┴────────────┘
         ▼
Context Assembly
```

---

## Long-Term Memory Update

Executed when a session ends.

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
LLM Judge
      │
 ┌────┴────┐
 │         │
Pass     Fail
 │         │
 ▼         ▼
Return  Query Rewrite
            │
            ▼
      Retrieve Again
```

Maximum iterations:

```
3
```

Failure exits gracefully after the final attempt.

---

# Phase 4 Runtime

Production optimization focuses on latency rather than behavior.

---

## Semantic Cache

```
User Query
      │
      ▼
Embedding
      │
      ▼
Redis Similarity Search
      │
 ┌────┴─────┐
 │          │
Hit       Miss
 │          │
 ▼          ▼
Return   Full Pipeline
```

A cache hit bypasses retrieval and generation entirely.

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

## Cache Invalidation

When a ProfileFact changes:

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

```
log_message()

get_history()
```

Internal storage may evolve.

Public API should not.

---

## Evaluation

```
eval_harness.py
```

Every phase uses the same evaluation entry point.

Only datasets and metrics evolve.

---

# Runtime Evolution Summary

| Phase   | Runtime Change                                                  |
| ------- | --------------------------------------------------------------- |
| Phase 1 | End-to-end baseline pipeline                                    |
| Phase 2 | Better retrieval quality through enrichment, RRF, and reranking |
| Phase 3 | Intent routing, long-term memory, and corrective agent loop     |
| Phase 4 | Semantic caching, concurrency, and production optimization      |

---

# Runtime Invariants

The following principles should remain true regardless of implementation phase.

1. Documents flow only through the ingestion pipeline.

2. Mutable user state is owned exclusively by the memory layer.

3. Retrieval never mutates stored knowledge.

4. Evaluation never modifies application behavior.

5. Operational tooling (Opik, LiteLLM, Redis, etc.) must not contain business logic.

6. Stable interfaces should change far less frequently than their implementations.

Maintaining these invariants keeps experimentation localized and minimizes large-scale refactoring as the system evolves.
