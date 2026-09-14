# Secure RAG Memory Engine

A first-principles implementation of an enterprise-style Retrieval-Augmented Generation (RAG) system built entirely in Python without orchestration frameworks such as LangChain or LlamaIndex.

The project is being developed incrementally over four phases, with  architectural improvements intended to be validated through quantitative evaluation rather than intuition.

**Current Status:** Phase 1 - Persistent MVP & Interactive Runtime - In Progress

---

## Project Goals

* Build a custom RAG system from first principles.
* Separate concerns into ingestion, retrieval, state management, and evaluation.
* Persist retrieval and conversational state across application restarts.
* Isolate retrieval state by experiment so different configurations can be evaluated independently.
* Measure every architectural improvement using reproducible evaluation metrics.
* Produce a portfolio-quality codebase demonstrating engineering trade-offs rather than framework usage.

---

## Current Capabilities

The current Phase 1 implementation provides:

* DOCX document ingestion and sanitization.
* Fixed-size document chunking.
* Dense vector retrieval using ChromaDB.
* Lexical retrieval using BM25.
* Persistent ChromaDB retrieval state.
* Persistent BM25 retrieval state.
* Experiment-isolated retrieval resources.
* Experiment-specific ingestion manifests.
* SQLite-backed conversation persistence.
* Human-readable named sessions backed by immutable session IDs.
* Interactive multi-session CLI.
* Session creation, switching, renaming, history inspection, clearing, and deletion.
* Separate ingestion and query application lifecycles.
* Multi-turn RAG query execution against persistent retrieval state.
* Centralized telemetry abstraction with Opik as the current backend.
* Opik tracing for meaningful ingestion and RAG pipeline stages.
* LiteLLM-to-Opik trace association.
* Experiment and phase metadata attached to telemetry traces.
* Controlled telemetry capture that avoids serializing large ingestion payloads.

Phase 1 evaluation and the 20-question baseline are still in progress.

---

## Architecture

The system is organized around four architectural pillars:

* Data Ingestion Pipeline
* RAG Orchestrator
* State & Session Management
* LLMOps & Evaluation

At a high level:

```
                    Application Runtime
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    Ingestion         RAG Runtime        StateManager
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                       telemetry/
                           │
                           ▼
                         Opik
```

```
                    Documents
                        │
                        ▼
                   ingest.py
                        │
                        ▼
              ┌───────────────────┐
              │ Persistent        │
              │ Retrieval State   │
              │                   │
              │ ChromaDB + BM25   │
              └─────────┬─────────┘
                        │
                        ▼
                   main.py / CLI
                        │
                        ▼
                RAG Orchestrator
                        │
                ┌───────┴───────┐
                ▼               ▼
          Retrieval          SQLite
                │           Session State
                └───────┬───────┘
                        ▼
                       LLM
                        │
                        ▼
                     Response
```

Retrieval state is isolated by `experiment_id`, while conversational state is managed independently through `session_id`.

Detailed architecture and runtime behavior are documented in `project_docs/`.

---

## Development Philosophy

* No LangChain or LlamaIndex business logic.
* Tracer Bullet development (working vertical slice before optimization).
* Data-driven iteration using evaluation metrics to validate architectural changes.
* Persistent state to separate ingestion, query execution, and evaluation lifecycles where appropriate.
* Small, focused Git branches.
* Architecture Decision Records (ADRs) for significant design choices and trade-offs.
* Stable interfaces for keeping architectural boundaries explicit so individual implementations can evolve independently.

---

## How It Works

The project separates document ingestion from interactive query execution.

**Ingestion**

`ingest.py` prepares persistent retrieval state:

Documents
   ↓
Parse
   ↓
Sanitize
   ↓
Chunk
   ↓
ChromaDB
   +
BM25
   ↓
Persistent experiment state

The active `experiment_id` determines the Chroma collection, BM25 index, and ingestion manifest used by the ingestion workflow.

**Query Runtime**

`main.py` provides the interactive application runtime:

User
 ↓
Interactive CLI
 ↓
Session resolution
 ↓
RAG Orchestrator
 ↓
Vector + BM25 retrieval
 ↓
Prompt construction
 ↓
LLM
 ↓
Response
 ↓
Persist conversation

The CLI exposes human-readable session names, while `StateManager` owns the mapping to immutable persistent session IDs.

**Observability**

Application components emit telemetry through the centralized `telemetry/` abstraction.

The current backend is Opik, using the shared project:

`secure-rag-memory-engine`

Traces are logically scoped using metadata such as:

* `experiment_id`
* `phase`

Telemetry is intentionally limited to operational metadata and meaningful pipeline stages rather than large document, chunk, or embedding payloads.

---

## Project Roadmap

### Phase 1 - Baseline MVP (In Progress)

**Status: In Progress**

Implemented:

* Basic secure ingestion pipeline
* Fixed-size chunking
* Dense vector retrieval
* BM25 retrieval
* Persistent ChromaDB storage
* Persistent BM25 storage
* Experiment-isolated retrieval state
* Experiment-specific ingestion manifests
* SQLite conversation persistence
* Named multi-session runtime
* Interactive CLI
* Session management
* Separate ingestion and query lifecycles

Remaining:

* Phase 1 evaluation harness
* 20-question baseline evaluation
* Baseline metric recording
* Finalize telemetry decorator initialization/fault-tolerance behavior

### Phase 2 - Retrieval Optimization

**Status: Planned**

* Structural enrichment
* Reciprocal Rank Fusion
* Cross-Encoder reranking
* Semantic conversation retrieval
* Session vector memory

### Phase 3 - Governance & Agentic Reasoning

**Status: Planned**

* Intent routing
* Self-corrective retrieval loops
* Long-term memory
* Fact invalidation
* Agentic reasoning workflows

### Phase 4 - Production Readiness

**Status: Planned**

* Redis semantic cache
* Parallel retrieval
* Concurrency improvements
* Performance benchmarking
* Production optimization

---

## Technology Stack

**Current**

* Python 3.11+
* ChromaDB
* LiteLLM
* SQLite
* BM25
* Pydantic
* Opik

**Planned / Later Phases**

* Tenacity
* Redis
* Ragas
* Cross-Encoder reranking infrastructure
* Additional production-related infrastructure

The technology stack evolves with the implementation phase; planned technologies are not necessarily part of the current runtime.

---

## Configuration System

Runtime configuration is centralized in the `config/` package.

Configuration controls runtime behavior and persistent resource selection rather than relying on hardcoded application constants.

In particular, experiment configuration determines the active `experiment_id` and the associated persistent retrieval resources.

Telemetry configuration is also centralized. The active experiment and phase are propagated into telemetry metadata, while the Opik project remains shared across experiments.

Persistent retrieval resources remain physically isolated by experiment.

Centralized configuration also makes architectural experiments reproducible without modifying application logic.

---

## Running the Project

The project uses separate application entry points for ingestion and interactive querying.

### Ingest Documents

python ingest.py

The ingestion runtime prepares persistent retrieval state for the configured experiment.

### Start the Interactive Runtime

python main.py

The interactive CLI supports commands for inspecting and managing the application state, including:

/help
/info
/experiments
/sessions
/switch <session_name>
/rename <new_session_name>
/history [session_name]
/clear [session_name]
/delete <session_name>
/exit
/quit

Detailed runtime behavior and configuration dependencies are documented under project_docs/.

---

## Repository Documentation

| File                               | Purpose                                                                                |
| ---------------------------------- | -------------------------------------------------------------------------------------- |
| `project_docs/README_AI.md`        | Instructions for AI-assisted development                                               |
| `project_docs/00_ARCHITECTURE.md`  | Target system architecture, capabilities, and ownership boundaries                     |
| `project_docs/01_ROADMAP.md`       | Development phases, implementation sequencing, scope, and exit criteria                |
| `project_docs/02_DECISIONS.md`     | Architectural decisions, trade-offs, and rationale                                     |
| `project_docs/03_CODEBASE.md`      | Auto-generated codebase structure and implementation map                               |
| `project_docs/04_CURRENT_STATE.md` | Current implementation status, completed work, tests, and known incomplete work        |
| `project_docs/05_TECH_DEBT.md`     | Intentional technical debt, deferred limitations, and open research topics             |
| `project_docs/06_DEPENDENCIES.md`  | Architectural feature dependencies, stable interfaces, and safe refactoring boundaries |
| `project_docs/07_RUNTIME_FLOW.md`  | Runtime execution flow across application phases                                       |

## What It Answers

Use the following guide when deciding which document to read:

| Question                                                     | Read                  |
| ------------------------------------------------------------ | --------------------- |
| **What is this system supposed to become?**                  | `00_ARCHITECTURE.md`  |
| **What capabilities belong to each pillar?**                 | `00_ARCHITECTURE.md`  |
| **When will a capability be implemented?**                   | `01_ROADMAP.md`       |
| **What is planned for the current phase?**                   | `01_ROADMAP.md`       |
| **Why was an architectural decision made?**                  | `02_DECISIONS.md`     |
| **What trade-off or constraint led to a design choice?**     | `02_DECISIONS.md`     |
| **What is actually implemented right now?**                  | `04_CURRENT_STATE.md` |
| **What has been completed or verified?**                     | `04_CURRENT_STATE.md` |
| **What is currently incomplete in this branch?**             | `04_CURRENT_STATE.md` |
| **What technical debt has intentionally been postponed?**    | `05_TECH_DEBT.md`     |
| **What limitations are accepted or still under research?**   | `05_TECH_DEBT.md`     |
| **What depends on what?**                                    | `06_DEPENDENCIES.md`  |
| **What can be changed without causing cascading refactors?** | `06_DEPENDENCIES.md`  |
| **What stable interfaces should implementations depend on?** | `06_DEPENDENCIES.md`  |
| **What happens when the application runs?**                  | `07_RUNTIME_FLOW.md`  |
| **How does ingestion execute?**                              | `07_RUNTIME_FLOW.md`  |
| **How does a user query move through the system?**           | `07_RUNTIME_FLOW.md`  |
| **How does the runtime evolve across phases?**               | `07_RUNTIME_FLOW.md`  |
| **How is the codebase currently structured?**                | `03_CODEBASE.md`      |
| **How should an AI assistant work with this repository?**    | `README_AI.md`        |

### Documentation Relationship

The documents answer different dimensions of the same system:

```text
                 What is the target system?
                          │
                          ▼
                  00_ARCHITECTURE
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
          WHEN?          WHY?       WHAT NOW?
             │            │            │
             ▼            ▼            ▼
       01_ROADMAP   02_DECISIONS  04_CURRENT_STATE
             │                         │
             │                         ▼
             │                    WHAT'S DEFERRED?
             │                         │
             │                         ▼
             │                   05_TECH_DEBT
             │
             └────────────┬───────────────┐
                          │               │
                          ▼               ▼
                    DEPENDS ON?       HOW DOES IT RUN?
                          │               │
                          ▼               ▼
                  06_DEPENDENCIES   07_RUNTIME_FLOW
```

`03_CODEBASE.md` describes the current implementation structure, while `README_AI.md` defines how AI-assisted development should use and maintain the repository documentation.

---

## Current Focus

Phase 1 has established the persistent retrieval architecture, experiment isolation, and interactive multi-session runtime.

The current focus is completing the Phase 1 evaluation harness and establishing the 20-question baseline against the persistent retrieval state.

Optimization of retrieval quality, deeper memory capabilities, agentic reasoning, and production infrastructure are intentionally deferred to later phases.