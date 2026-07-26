# Current Phase:
Phase 1

---
# Current Pillar:
Retrieval

---
# Current Branch:
feature/phase1-rag-engine

---
## Current Goal:
Connect retrieval pipeline.

---
## Completed:
Ingestion
* Document Parser 
* Document Sanitization
* Chunk Generation using Fixed Size Chunker

Chromma Vector Engine
* Chunk Embedding 
* Upsert Chunks in chromadb
* Search Similar Chunks using chromadb

BM25 Engine
* Upsert chunks
* Search similar chunks

---
## Data Models used: 
class RawOnenotePage(BaseModel):
    page_id: str 
    notebook_name: str
    section_name: str
    page_title: str
    text_content: str
    page_hash: str
    depth: int = 0  # 0 = main page, 1 = subpage, etc.
    parent_page_id: Optional[str] = None  # Tracks hierarchy for sub-pages

class ProcessedChunk(BaseModel):
    chunk_id: str 
    parent_page_id: str
    text_content: str
    chunk_index: int
    notebook_name: str
    section_name: str
    parent_page_title: str
    content_hash: str  

class IngestionPayload(BaseModel): 
    source_page_id: str
    chunks: List[ProcessedChunk]
    total_chunks: int
    parsing_latency_ms: float

---
## Definition of Done
- simple hybrid retrieval
- Vector and BM25 results are concatenated without ranking
- context assembly
- LLM generation

---
## Explicitly Out of Scope
- routing
- reranking
- query rewriting
- self-correction
- agent loops

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
# Phase 1 Runtime flow

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