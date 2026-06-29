# 01_ROADMAP.md

# Secure RAG Memory Engine — Implementation Roadmap

This document is the single source of truth for implementation progress.

It defines:

- project phases
- architectural goals
- implementation milestones
- branch planning
- completion criteria
- phase dependencies

It intentionally does **not** describe implementation details.
Those belong in the architecture documents.

---

# Overall Development Philosophy

This project follows three architectural manifestos.

## 1. Tracer Bullet Development

Every phase produces a complete, working vertical slice.

Optimization never comes before correctness.

---

## 2. Data-Driven Evolution

Every optimization must improve at least one measurable metric.

Metrics include:

- Context Precision
- Context Recall
- Faithfulness
- Latency

No optimization is introduced purely because it appears "better."

---

## 3. Stable Interfaces

Implementations are expected to evolve.

Public interfaces should remain stable.

Whenever possible:

Implementation
↓

Interface remains unchanged

↓

Consumers remain unchanged

---

# Phase Overview

| Phase | Focus | Status |
|---------|--------|---------|
| Phase 1 | Working MVP | In Progress |
| Phase 2 | Retrieval Quality | Planned |
| Phase 3 | Agentic Reasoning & Governance | Planned |
| Phase 4 | Production Optimization | Planned |

---

# Phase 1 — Baseline MVP

## Objective

Build the smallest complete end-to-end RAG system.

The emphasis is establishing architecture rather than maximizing quality.

---

## Pillar 1 — Secure Data Ingestion

### Scope

- DOCX parsing
- document sanitization
- ingestion manifest
- incremental ingestion
- RawOnenotePage generation
- fixed-size chunking
- ProcessedChunk generation
- Chroma insertion
- BM25 indexing

### Explicitly Out of Scope

- structural chunking
- HTML parsing
- OCR
- metadata enrichment
- chunk-level deduplication
- persistent vector optimization

---

## Pillar 2 — Agentic RAG

### Scope

- vector search
- BM25 search
- simple hybrid retrieval
- context assembly
- LLM generation

### Explicitly Out of Scope

- routing
- reranking
- query rewriting
- self-correction
- agent loops

---

## Pillar 3 — State & Session Management

### Scope

- SQLite persistence
- ChatMessage
- session restoration
- get_conversation_context()

### Explicitly Out of Scope

- semantic conversation retrieval
- profile memory
- fact invalidation
- Redis cache

---

## Pillar 4 — LLMOps

### Scope

- Opik tracing
- evaluation harness
- smoke evaluation
- baseline evaluation

---

## Success Criteria

✓ Complete ingestion pipeline

✓ Searchable documents

✓ Hybrid retrieval

✓ SQLite conversation persistence

✓ Session restoration

✓ Evaluation harness operational

✓ Baseline metrics recorded

---

## Planned Branches

### feature/phase1-ingestion

Build baseline ingestion.

---

### feature/phase1-vector-store

Implement Chroma integration.

---

### feature/phase1-bm25

Implement lexical retrieval.

---

### feature/phase1-rag-engine

Connect retrieval pipeline.

---

### feature/phase1-session-memory

SQLite logging.

Conversation restoration.

---

### feature/phase1-evaluation

Smoke tests.

20-question baseline.

---

### Exit Criteria

Phase 1 is complete when every architectural pillar has one working implementation.

Optimization is intentionally postponed.

---

# Phase 2 — Retrieval Quality

## Objective

Improve retrieval quality while preserving the Phase 1 pipeline.

No agentic reasoning should be introduced.

---

## Pillar 1

### Scope

- Structural Ancestry Injection
- enrichment stage
- enriched embedding text
- raw text preservation
- layout-aware parsing
- BeautifulSoup parsing
- OCR extraction
- structural chunking

---

## Pillar 2

### Scope

- BaseRetriever
- modular retrievers
- Reciprocal Rank Fusion
- Cross-Encoder reranking

---

## Pillar 3

### Scope

- SessionVectorChunk
- semantic conversation retrieval
- shared Chroma collection
- session filtering

---

## Pillar 4

### Scope

- Phase comparison
- regression evaluation
- metric tracking

---

## Success Criteria

Retrieval quality measurably improves.

Evaluation demonstrates:

- higher precision
- higher recall

No caller changes required.

---

## Planned Branches

feature/phase2-layout-parser

feature/phase2-structural-chunking

feature/phase2-enrichment

feature/phase2-bm25-refactor

feature/phase2-retriever-interface

feature/phase2-rrf

feature/phase2-cross-encoder

feature/phase2-session-vectors

feature/phase2-regression-evaluation

---

## Exit Criteria

Hybrid retrieval is modular.

Retrieval quality improves measurably.

Conversation context becomes semantic.

---

# Phase 3 — Governance & Agentic State

## Objective

Transform retrieval into an intelligent agent.

Introduce long-term user memory.

---

## Pillar 1

### Scope

Metadata filtering.

Access control.

Allowed-user filtering.

---

## Pillar 2

### Scope

Intent router.

Query routing.

Hybrid retrieval.

LLM-as-a-Judge.

Query rewriting.

Finite-state corrective loop.

---

## Pillar 3

### Scope

ProfileFact extraction.

Read-Verify-Invalidate pipeline.

Fact invalidation.

Long-term memory.

Versioned profile facts.

---

## Pillar 4

### Scope

Evaluation of routing strategies.

Hallucination reduction.

Faithfulness tracking.

---

## Success Criteria

Intent routing operational.

Fact mutation operational.

Hallucination correction operational.

---

## Planned Branches

feature/phase3-security

feature/phase3-router

feature/phase3-profile-memory

feature/phase3-fact-invalidation

feature/phase3-agent-loop

feature/phase3-query-rewriter

feature/phase3-judge

---

## Exit Criteria

The application behaves as a deterministic agent rather than a retrieval script.

---

# Phase 4 — Production Readiness

## Objective

Optimize latency, resilience, scalability, and operational maturity.

---

## Pillar 1

No major ingestion changes.

Only optimization.

---

## Pillar 2

Advanced retrieval experiments.

Hierarchical retrieval.

Graph retrieval.

Parallel retrieval.

---

## Pillar 3

Redis semantic cache.

Synchronization improvements.

Distributed caching.

---

## Pillar 4

Production benchmarking.

Regression dashboards.

Cost analysis.

Latency analysis.

Adaptive retries.

---

## Success Criteria

Cache operational.

Parallel retrieval operational.

Production benchmarking completed.

Portfolio-ready evaluation dashboards.

---

## Planned Branches

feature/phase4-redis

feature/phase4-cache-manager

feature/phase4-parallel-retrieval

feature/phase4-async-orchestration

feature/phase4-production-benchmark

feature/phase4-latency-analysis

---

## Exit Criteria

The system demonstrates:

- production architecture

- measurable optimization

- operational observability

- reproducible benchmarking

---

# Dependency Summary

Phase 2 depends on:

✓ Working Phase 1 pipeline

---

Phase 3 depends on:

✓ Modular retrieval

✓ Semantic memory

---

Phase 4 depends on:

✓ Stable agent pipeline

✓ Evaluation framework

---

# Definition of Done

A feature is complete only when all of the following are true.

- Implementation complete

- Tests pass

- Evaluation completed (if applicable)

- Documentation updated

- Dependency graph updated

- Architectural decisions updated (if required)

- Current state updated

- Branch merged

Only then should work begin on the next feature.