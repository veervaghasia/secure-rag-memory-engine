# 01_ROADMAP.md

# Secure RAG Memory Engine — Implementation Roadmap

This document is the single source of truth for implementation progress.

It defines:

- project phases
- implementation milestones
- branch planning
- completion criteria
- phase dependencies

It intentionally does not define the complete target architecture or explain implementation details.

The architecture document defines long-term system responsibilities and capability ownership.

Architectural decisions and trade-offs belong in the ADR document.

Runtime behavior and implementation details are documented separately.

---

## Relationship to Architecture

The architecture document defines the complete target capability set and ownership boundaries of the system.

This roadmap defines when those capabilities are introduced.

Therefore, a capability appearing in the architecture does not imply that it is already implemented. Its implementation status is determined by the roadmap and current-state documentation.

---

# Overall Development Philosophy

This project follows three architectural principles.

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
| Phase 1 | Working MVP + Persistent Runtime | In Progress |
| Phase 2 | Retrieval Quality | Planned |
| Phase 3 | Agentic Reasoning & Governance | Planned |
| Phase 4 | Production Optimization | Planned |

---

# Phase 1 — Baseline MVP

**Status: In Progress**

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
- persistent ChromaDB storage
- persistent BM25 storage
- experiment-specific retrieval state
- experiment-specific ingestion manifests

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
- persistent retrieval-state consumption
- multi-turn query execution through the interactive runtime

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
- session metadata and message separation
- immutable session IDs
- human-readable session names
- session creation and restoration
- session switching
- session renaming
- session history inspection
- session clearing
- session deletion
- get_conversation_context()
- persistent multi-turn conversation state
- interactive CLI session management

### Explicitly Out of Scope

- semantic conversation retrieval
- profile memory
- fact invalidation
- Redis cache

---

## Pillar 4 — LLMOps

### Scope

- Opik tracing
- centralized application telemetry
- phase-level and experiment-level trace identification
- evaluation harness
- smoke evaluation
- baseline evaluation

---

## Planned Branches

### Completed / Active Branches

#### feature/phase1-ingestion

Build baseline ingestion.

---

#### feature/phase1-vector-store

Implement Chroma integration.

---

#### feature/phase1-bm25

Implement lexical retrieval.

---

#### feature/phase1-rag-engine

Connect retrieval pipeline.

---

#### feature/phase1-session-memory

SQLite logging.

Conversation restoration.

---

#### feature/phase1-persistent-storage

Establish persistent experiment-isolated retrieval storage for ChromaDB and BM25, separate ingestion from query execution, and provide an interactive multi-session runtime with session management.

---

### Remaining Phase 1 Branches

#### feature/phase1-evaluation

Run smoke tests and establish the 20-question Phase 1 baseline against the persistent retrieval state.

---

#### refactor/phase1-cleanup

Final cleanup and modifications before moving to phase 2. 

---

## Success Criteria

✓ Complete ingestion pipeline

✓ Searchable documents

✓ Hybrid retrieval

✓ Persistent ChromaDB retrieval state

✓ Persistent BM25 retrieval state

✓ Experiment-isolated retrieval state

✓ SQLite conversation persistence

✓ Named multi-session runtime

✓ Interactive CLI

✓ Session restoration and management

✓ Ingestion and query execution separated into independent lifecycles

✓ Persistent retrieval state survives application restart

✓ Application telemetry is centralized under one observability project

✓ Traces can be identified by phase and experiment

- Evaluation harness operational
- Baseline metrics recorded

---

### Exit Criteria

Phase 1 is complete when every architectural pillar has one working implementation and the baseline system can be evaluated independently of ingestion.

Phase 1 must provide:

- working ingestion
- persistent retrieval state
- vector and lexical retrieval
- SQLite conversation persistence
- interactive multi-session runtime
- experiment-isolated retrieval state
- stable runtime interfaces
- baseline evaluation

Optimization is intentionally postponed.

---

# Phase 2 — Retrieval Quality

**Status: Planned**

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

Retrieval improvements are evaluated against the Phase 1 baseline.

Changes must demonstrate measurable impact on relevant retrieval metrics without unacceptable regression in other tracked metrics.

Evaluation includes:

- Context Precision
- Context Recall
- Faithfulness
- Latency

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

- Hybrid retrieval is modular.
- Retrieval quality improves measurably.
- Conversation context becomes semantic.

---

# Phase 3 — Governance & Agentic State

**Status: Planned**

## Objective

Introduce governed query routing, corrective retrieval workflows, access control, and long-term user memory.

---

## Pillar 1

### Scope

- Metadata filtering.
- Access control.
- Allowed-user filtering.

---

## Pillar 2

### Scope

- Intent router.
- Query routing.
- Query rewriting.
- Answer validation.
- Finite-state corrective loop.

---

## Pillar 3

### Scope

- ProfileFact extraction.
- Read-Verify-Invalidate pipeline.
- Fact invalidation.
- Long-term memory.
- Versioned profile facts.

---

## Pillar 4

### Scope

- Evaluation of routing strategies.
- LLM-as-a-Judge evaluation.
- Faithfulness tracking.

---

## Success Criteria

- Intent routing is operational and evaluated against a defined routing dataset.
- Long-term profile facts can be created, updated, invalidated, and versioned.
- Corrective retrieval can detect and respond to defined validation failures.
- Access-control filtering is enforced before protected context reaches generation.
- Phase 3 changes are evaluated against the established baseline.

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

The application supports bounded, governed agent execution with:

- intent-based routing
- corrective retrieval
- access-control filtering
- long-term memory
- evaluation of agent behavior

---

# Phase 4 — Production Readiness

**Status: Planned**

## Objective

Optimize latency, resilience, scalability, and operational maturity.

---

## Pillar 1

No major ingestion changes.

Only optimization.

---

## Pillar 2

- Advanced retrieval experiments.
- Hierarchical retrieval.
- Graph retrieval.
- Parallel retrieval.

---

## Pillar 3

- Redis semantic cache.
- Synchronization improvements.
- Distributed caching.

---

## Pillar 4

- Production benchmarking.
- Regression dashboards.
- Cost analysis.
- Latency analysis.
- Adaptive retries.

---

## Success Criteria

- Cache operational.
- Parallel retrieval operational.
- Production benchmarking completed.
- Portfolio-ready evaluation dashboards.

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

### Phase 2 depends on

- Phase 1 ingestion and retrieval pipeline
- persistent retrieval state
- baseline evaluation

### Phase 3 depends on

- modular retrieval
- retrieval fusion and reranking
- semantic conversation retrieval
- established evaluation workflow

### Phase 4 depends on

- stable agentic pipeline
- evaluation framework
- telemetry and benchmarking

---

## Definition of Done

A feature is complete only when all applicable items are true:

- Implementation complete
- Tests pass
- Evaluation completed, if applicable
- Documentation updated
- Dependency graph updated
- Architectural decisions updated, if required
- Current state updated
- No known documentation inconsistencies remain
- Branch merged

Only then should work begin on the next feature.