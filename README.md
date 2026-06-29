# Secure RAG Memory Engine

A first-principles implementation of an enterprise-style Retrieval-Augmented Generation (RAG) system built entirely in Python without orchestration frameworks such as LangChain or LlamaIndex.

The project is being developed incrementally over four phases, with every architectural improvement validated through quantitative evaluation rather than intuition.

**Current Status:** Phase 1 (Baseline MVP) — In Progress

---

## Project Goals

* Build a custom RAG system from first principles.
* Separate concerns into ingestion, retrieval, state management, and operations.
* Measure every architectural improvement using evaluation metrics.
* Produce a portfolio-quality codebase demonstrating engineering trade-offs rather than framework usage.

---

## Architecture

The system is organized around four architectural pillars:

* Secure Data Ingestion Pipeline
* Agentic RAG Orchestrator
* State & Session Management
* LLMOps & Evaluation

Detailed architectural documentation is available under the `project_docs/` directory.

---

## Development Philosophy

* No LangChain or LlamaIndex business logic.
* Tracer Bullet development (working vertical slice before optimization).
* Data-driven iteration using evaluation metrics.
* Small, focused Git branches.
* Architecture Decision Records (ADRs) for significant design choices.

---

## Project Roadmap

### Phase 1 — Baseline MVP (In Progress)

* Basic ingestion pipeline
* Fixed-size chunking
* ChromaDB integration
* BM25 retrieval
* SQLite chat history
* Evaluation harness

### Phase 2 — Retrieval Optimization

* Structural enrichment
* Reciprocal Rank Fusion
* Cross-Encoder reranking
* Session vector memory

### Phase 3 — Governance & Agentic Reasoning

* Intent routing
* Self-corrective retrieval loops
* Long-term memory
* Fact invalidation

### Phase 4 — Production Readiness

* Redis semantic cache
* Parallel retrieval
* Performance benchmarking
* Production optimization

---

## Technology Stack

* Python 3.11+
* ChromaDB
* LiteLLM
* SQLite
* Redis
* BM25
* Opik
* Ragas
* Pydantic
* Tenacity

---

## Configuration System

Centralized runtime configuration (config/ package). All runtime behavior should be controlled through configuration rather than hardcoded constants.

Configuration is intentionally centralized to make architectural experiments reproducible without modifying application logic.

---

## Repository Documentation

| File                  | Purpose                                  |
| --------------------- | ---------------------------------------- |
| `README_AI.md`        | Instructions for AI-assisted development |
| `00_ARCHITECTURE.md`  | System architecture                      |
| `01_ROADMAP.md`       | Development roadmap                      |
| `02_DECISIONS.md`     | Architectural decisions                  |
| `03_CODEBASE.md`      | Auto-generated codebase map              |
| `04_CURRENT_STATE.md` | Implementation status                    |
| `05_TECH_DEBT.md`     | Deferred work                            |
| `06_DEPENDENCIES.md`  | Feature dependencies                     |
| `07_RUNTIME_FLOW.md`  | Runtime execution flow                   |

---

## Current Focus

The project is currently implementing the Phase 1 MVP while establishing the long-term architecture required for later retrieval optimization, agentic reasoning, and production scalability.
